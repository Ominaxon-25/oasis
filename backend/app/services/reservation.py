import asyncio
import pytz
from datetime import datetime, timedelta
from typing import Dict
from collections import defaultdict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, BackgroundTasks

from app.database import is_sqlite
from app.models.restaurant import Restaurant
from app.models.table import Table, TableZone
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.reservation import ReservationCreate, ReservationOut
from app.services.websocket_manager import ws_manager
from app.services.notification import notification_service

# Fine-grained async mutex per table to guarantee atomic mutual exclusion on local SQLite
_table_locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


class ReservationService:
    """
    Production-grade reservation creation service with strict concurrency control.
    Prevents race conditions using SQL row-level locking (SELECT ... FOR UPDATE)
    and transaction isolation.
    """

    @classmethod
    async def create_reservation(
        cls,
        db: AsyncSession,
        payload: ReservationCreate,
        background_tasks: BackgroundTasks
    ) -> ReservationOut:
        # Acquire table-level mutex (complements SQL row lock for local SQLite dev)
        table_lock = _table_locks[payload.table_id]

        async with table_lock:
            # 1. Fetch Restaurant & Timezone
            restaurant = await db.get(Restaurant, payload.restaurant_id)
            if not restaurant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Restaurant with ID {payload.restaurant_id} not found."
                )

            tz_str = restaurant.timezone or "Asia/Tashkent"
            try:
                local_tz = pytz.timezone(tz_str)
            except Exception:
                local_tz = pytz.timezone("Asia/Tashkent")

            # Standardize reservation times
            res_time = payload.reservation_time
            if res_time.tzinfo is None:
                res_time = local_tz.localize(res_time)
            else:
                res_time = res_time.astimezone(local_tz)

            turn_mins = restaurant.avg_turn_time_mins or 90
            end_time = payload.end_time
            if end_time is None:
                end_time = res_time + timedelta(minutes=turn_mins)
            else:
                if end_time.tzinfo is None:
                    end_time = local_tz.localize(end_time)
                else:
                    end_time = end_time.astimezone(local_tz)

            if end_time <= res_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reservation end_time must be strictly after reservation_time."
                )

            # 2. Begin transaction with SQL Row-Level Locking (SELECT ... FOR UPDATE)
            # In PostgreSQL: executes SELECT ... FOR UPDATE
            # In SQLite: locked via transaction & table mutex
            table_query = select(Table).where(Table.id == payload.table_id)
            if not is_sqlite:
                table_query = table_query.with_for_update()

            table_result = await db.execute(table_query)
            table = table_result.scalar_one_or_none()

            if not table:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Table with ID {payload.table_id} does not exist."
                )

            if not table.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Table {table.table_number} is currently inactive or blocked."
                )

            # Check capacity
            if payload.party_size < table.min_capacity or payload.party_size > table.max_capacity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Party size {payload.party_size} is outside table capacity "
                        f"({table.min_capacity}-{table.max_capacity} guests)."
                    )
                )

            # 3. Check for overlapping active reservations on the locked table
            # Overlap formula: existing_start < new_end AND existing_end > new_start
            overlap_query = select(Reservation).where(
                and_(
                    Reservation.table_id == payload.table_id,
                    Reservation.status.in_([
                        ReservationStatus.PENDING,
                        ReservationStatus.CONFIRMED,
                        ReservationStatus.SEATED
                    ]),
                    Reservation.reservation_time < end_time,
                    Reservation.end_time > res_time
                )
            )
            if not is_sqlite:
                overlap_query = overlap_query.with_for_update()

            overlap_result = await db.execute(overlap_query)
            existing_overlap = overlap_result.scalars().first()

            if existing_overlap:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Selected table is no longer available for this time slot"
                )

            # 4. Insert Confirmed Reservation
            new_reservation = Reservation(
                restaurant_id=payload.restaurant_id,
                table_id=payload.table_id,
                customer_name=payload.customer_name,
                customer_phone=payload.customer_phone,
                party_size=payload.party_size,
                reservation_time=res_time,
                end_time=end_time,
                status=ReservationStatus.CONFIRMED
            )
            db.add(new_reservation)
            await db.commit()
            await db.refresh(new_reservation)

            # 5. Dispatch decoupled async notifications
            background_tasks.add_task(
                notification_service.send_reservation_confirmation,
                customer_name=new_reservation.customer_name,
                customer_phone=new_reservation.customer_phone,
                restaurant_name=restaurant.name,
                table_number=table.table_number,
                reservation_time=res_time.strftime("%Y-%m-%d %H:%M"),
                party_size=new_reservation.party_size,
                ref_id=new_reservation.id
            )

            # 6. Broadcast live real-time event to B2B Vendor Dashboard via WebSockets
            res_out = ReservationOut.model_validate(new_reservation)
            await ws_manager.broadcast(
                restaurant_id=payload.restaurant_id,
                event_type="RESERVATION_CREATED",
                data={
                    "reservation": res_out.model_dump(mode="json"),
                    "table_number": table.table_number,
                    "table_id": table.id
                }
            )

            return res_out


reservation_service = ReservationService()
