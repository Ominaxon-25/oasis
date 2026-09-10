from datetime import datetime, date, time, timedelta
import pytz
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.restaurant import Restaurant
from app.models.table import Table, TableZone
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.reservation import TimeSlotOut, AvailabilityResponse


class AvailabilityEngine:
    """
    High-performance dynamic availability calculation engine.
    Computes real-time bookable slots against table capacities, operating schedules,
    and active reservation intervals without slot overlap.
    """

    @staticmethod
    async def get_availability(
        db: AsyncSession,
        restaurant_id: int,
        target_date: date,
        party_size: int
    ) -> AvailabilityResponse:
        # 1. Fetch Restaurant & Operating Hours
        restaurant = await db.get(Restaurant, restaurant_id)
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restaurant with ID {restaurant_id} not found."
            )

        tz_str = restaurant.timezone or "Asia/Tashkent"
        try:
            local_tz = pytz.timezone(tz_str)
        except Exception:
            local_tz = pytz.timezone("Asia/Tashkent")

        turn_mins = restaurant.avg_turn_time_mins or 90
        op_hours = restaurant.operating_hours or {"open": "12:00", "close": "23:00"}
        open_time_str = op_hours.get("open", "12:00")
        close_time_str = op_hours.get("close", "23:00")

        open_h, open_m = map(int, open_time_str.split(":"))
        close_h, close_m = map(int, close_time_str.split(":"))

        # Day window in restaurant's timezone
        day_start = local_tz.localize(datetime.combine(target_date, time(open_h, open_m)))
        day_close = local_tz.localize(datetime.combine(target_date, time(close_h, close_m)))

        # 2. Query all active tables for this restaurant matching capacity
        table_stmt = (
            select(Table)
            .join(TableZone, Table.zone_id == TableZone.id)
            .where(
                and_(
                    TableZone.restaurant_id == restaurant_id,
                    Table.is_active.is_(True),
                    Table.min_capacity <= party_size,
                    Table.max_capacity >= party_size
                )
            )
        )
        table_result = await db.execute(table_stmt)
        matching_tables = table_result.scalars().all()

        if not matching_tables:
            return AvailabilityResponse(
                restaurant_id=restaurant_id,
                date=target_date.isoformat(),
                party_size=party_size,
                available_slots=[]
            )

        matching_table_ids = {t.id for t in matching_tables}

        # 3. Query all non-cancelled reservations for the restaurant on that day window
        # Include overlapping reservations that might start or end on this day
        res_stmt = (
            select(Reservation)
            .where(
                and_(
                    Reservation.restaurant_id == restaurant_id,
                    Reservation.table_id.in_(matching_table_ids),
                    Reservation.status.in_([
                        ReservationStatus.PENDING,
                        ReservationStatus.CONFIRMED,
                        ReservationStatus.SEATED
                    ]),
                    Reservation.reservation_time < day_close,
                    Reservation.end_time > day_start
                )
            )
        )
        res_result = await db.execute(res_stmt)
        active_reservations = res_result.scalars().all()

        # 4. Generate candidate time slots every 30 minutes
        # A slot is valid if (slot_start + turn_time) <= day_close
        slot_duration = timedelta(minutes=turn_mins)
        step_interval = timedelta(minutes=30)
        
        available_slots: List[TimeSlotOut] = []
        current_slot_start = day_start

        while current_slot_start + slot_duration <= day_close:
            current_slot_end = current_slot_start + slot_duration

            # Find which matching tables are free during [current_slot_start, current_slot_end)
            free_table_ids: List[int] = []

            for t in matching_tables:
                has_overlap = False
                for r in active_reservations:
                    if r.table_id != t.id:
                        continue

                    # Ensure timezone comparability
                    r_start = r.reservation_time
                    r_end = r.end_time
                    if r_start.tzinfo is None:
                        r_start = local_tz.localize(r_start)
                    else:
                        r_start = r_start.astimezone(local_tz)

                    if r_end.tzinfo is None:
                        r_end = local_tz.localize(r_end)
                    else:
                        r_end = r_end.astimezone(local_tz)

                    # Standard Interval Overlap Test:
                    # Slot [S_start, S_end) overlaps with [R_start, R_end) iff:
                    # S_start < R_end and S_end > R_start
                    if current_slot_start < r_end and current_slot_end > r_start:
                        has_overlap = True
                        break

                if not has_overlap:
                    free_table_ids.append(t.id)

            if free_table_ids:
                available_slots.append(
                    TimeSlotOut(
                        time=current_slot_start.strftime("%H:%M"),
                        slot_start=current_slot_start,
                        slot_end=current_slot_end,
                        available_tables_count=len(free_table_ids),
                        matching_table_ids=free_table_ids
                    )
                )

            current_slot_start += step_interval

        return AvailabilityResponse(
            restaurant_id=restaurant_id,
            date=target_date.isoformat(),
            party_size=party_size,
            available_slots=available_slots
        )


availability_engine = AvailabilityEngine()
