from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Dict
import pytz

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.database import get_db
from app.models.restaurant import Restaurant
from app.models.table import TableZone, Table
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.table import TableStatusUpdate
from app.schemas.reservation import ReservationOut
from app.schemas.vendor import (
    FloorPlanTableOut,
    FloorPlanZoneOut,
    FloorPlanResponse,
    PeakHourMetric,
    AnalyticsResponse
)
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/vendor", tags=["B2B Vendor Dashboard"])


@router.get("/floor-plan", response_model=FloorPlanResponse, summary="Live Floor Plan & Real-Time Table Status")
async def get_floor_plan(
    restaurant_id: int = Query(..., description="Target restaurant ID", example=1),
    timestamp: Optional[datetime] = Query(None, description="Point in time (ISO); defaults to current time"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the real-time layout of zones and tables for the B2B Vendor Dashboard,
    including live occupancy status (AVAILABLE, SEATED, RESERVED, or BLOCKED).
    """
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

    check_time = timestamp or datetime.now(timezone.utc)
    if check_time.tzinfo is None:
        check_time = local_tz.localize(check_time)
    else:
        check_time = check_time.astimezone(local_tz)

    # Fetch zones with tables
    zones_stmt = (
        select(TableZone)
        .where(TableZone.restaurant_id == restaurant_id)
        .order_by(TableZone.id)
    )
    zones_result = await db.execute(zones_stmt)
    zones = zones_result.scalars().all()

    # Query active reservations that are currently active at check_time
    res_stmt = (
        select(Reservation)
        .where(
            and_(
                Reservation.restaurant_id == restaurant_id,
                Reservation.status.in_([
                    ReservationStatus.CONFIRMED,
                    ReservationStatus.SEATED
                ]),
                Reservation.reservation_time <= check_time,
                Reservation.end_time > check_time
            )
        )
    )
    res_result = await db.execute(res_stmt)
    current_reservations = {r.table_id: r for r in res_result.scalars().all()}

    floor_plan_zones: List[FloorPlanZoneOut] = []

    for zone in zones:
        tables_out: List[FloorPlanTableOut] = []
        for table in zone.tables:
            active_res = current_reservations.get(table.id)

            if not table.is_active:
                live_status = "BLOCKED"
            elif active_res:
                live_status = active_res.status.value  # "SEATED" or "CONFIRMED" (RESERVED)
            else:
                live_status = "AVAILABLE"

            res_schema = ReservationOut.model_validate(active_res) if active_res else None

            tables_out.append(
                FloorPlanTableOut(
                    id=table.id,
                    table_number=table.table_number,
                    min_capacity=table.min_capacity,
                    max_capacity=table.max_capacity,
                    is_active=table.is_active,
                    live_status=live_status,
                    active_reservation=res_schema
                )
            )

        floor_plan_zones.append(
            FloorPlanZoneOut(
                zone_id=zone.id,
                zone_name=zone.name,
                tables=tables_out
            )
        )

    return FloorPlanResponse(
        restaurant_id=restaurant.id,
        restaurant_name=restaurant.name,
        queried_at=check_time,
        zones=floor_plan_zones
    )


@router.patch("/tables/{id}/status", summary="Manual Table Block/Unblock or Walk-in Seating")
async def update_table_status(
    payload: TableStatusUpdate,
    id: int = Path(..., description="Table ID", example=1),
    db: AsyncSession = Depends(get_db)
):
    """
    Allows vendor staff to:
    1. Toggle table availability (`is_active: false` to block for maintenance, `true` to unblock).
    2. Seat immediate walk-in guests (`seat_walk_in: true`), which creates a SEATED reservation.
    """
    table = await db.get(Table, id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table with ID {id} not found."
        )

    zone = await db.get(TableZone, table.zone_id)
    restaurant = await db.get(Restaurant, zone.restaurant_id)

    # 1. Handle Active/Blocked Toggle
    if payload.is_active is not None:
        table.is_active = payload.is_active
        await db.commit()
        await db.refresh(table)

        await ws_manager.broadcast(
            restaurant_id=zone.restaurant_id,
            event_type="TABLE_STATUS_CHANGED",
            data={
                "table_id": table.id,
                "table_number": table.table_number,
                "is_active": table.is_active,
                "status": "AVAILABLE" if table.is_active else "BLOCKED"
            }
        )

    # 2. Handle Walk-in Seating
    if payload.seat_walk_in:
        if not table.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot seat walk-in: Table {table.table_number} is blocked/inactive."
            )

        now = datetime.now(timezone.utc)
        party_size = payload.party_size or table.min_capacity
        turn_mins = restaurant.avg_turn_time_mins or 90

        # Check for immediate overlap
        overlap_stmt = select(Reservation).where(
            and_(
                Reservation.table_id == table.id,
                Reservation.status.in_([ReservationStatus.CONFIRMED, ReservationStatus.SEATED]),
                Reservation.reservation_time < now + timedelta(minutes=turn_mins),
                Reservation.end_time > now
            )
        )
        overlap = (await db.execute(overlap_stmt)).scalars().first()
        if overlap:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Table {table.table_number} currently has an overlapping reservation."
            )

        walk_in_res = Reservation(
            restaurant_id=zone.restaurant_id,
            table_id=table.id,
            customer_name=payload.customer_name or "Walk-in Guest",
            customer_phone=payload.customer_phone or "+998900000000",
            party_size=party_size,
            reservation_time=now,
            end_time=now + timedelta(minutes=turn_mins),
            status=ReservationStatus.SEATED
        )
        db.add(walk_in_res)
        await db.commit()
        await db.refresh(walk_in_res)

        res_out = ReservationOut.model_validate(walk_in_res)
        await ws_manager.broadcast(
            restaurant_id=zone.restaurant_id,
            event_type="TABLE_STATUS_CHANGED",
            data={
                "table_id": table.id,
                "table_number": table.table_number,
                "is_active": table.is_active,
                "status": "SEATED",
                "reservation": res_out.model_dump(mode="json")
            }
        )
        return {"status": "SUCCESS", "message": f"Walk-in guest seated at Table {table.table_number}", "reservation": res_out}

    return {"status": "SUCCESS", "table_id": table.id, "is_active": table.is_active}


@router.get("/analytics", response_model=AnalyticsResponse, summary="B2B Vendor Performance & Occupancy Analytics")
async def get_analytics(
    restaurant_id: int = Query(..., description="Target restaurant ID", example=1),
    date_query: Optional[date] = Query(None, alias="date", description="Analytics date; defaults to today"),
    db: AsyncSession = Depends(get_db)
):
    """
    Computes vendor performance metrics:
    - Current occupancy rate (%)
    - Active vs blocked tables
    - Total parties and guests served
    - Peak hours distribution
    - Status breakdown
    """
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

    target_date = date_query or datetime.now(local_tz).date()

    # Day bounds
    day_start = local_tz.localize(datetime.combine(target_date, time.min))
    day_end = local_tz.localize(datetime.combine(target_date, time.max))

    # 1. Total and Active Tables
    tables_stmt = (
        select(Table)
        .join(TableZone, Table.zone_id == TableZone.id)
        .where(TableZone.restaurant_id == restaurant_id)
    )
    all_tables = (await db.execute(tables_stmt)).scalars().all()
    total_tables = len(all_tables)
    active_tables = sum(1 for t in all_tables if t.is_active)

    # 2. Reservations for the day
    res_stmt = (
        select(Reservation)
        .where(
            and_(
                Reservation.restaurant_id == restaurant_id,
                Reservation.reservation_time >= day_start,
                Reservation.reservation_time <= day_end
            )
        )
    )
    daily_res = (await db.execute(res_stmt)).scalars().all()

    # 3. Status breakdown
    status_counts: Dict[str, int] = {s.value: 0 for s in ReservationStatus}
    total_guests = 0
    hour_distribution: Dict[int, int] = {h: 0 for h in range(24)}

    for r in daily_res:
        st_val = r.status.value if hasattr(r.status, "value") else str(r.status)
        status_counts[st_val] = status_counts.get(st_val, 0) + 1
        if st_val != ReservationStatus.CANCELLED.value:
            total_guests += r.party_size
            r_local = r.reservation_time.astimezone(local_tz) if r.reservation_time.tzinfo else r.reservation_time
            hour_distribution[r_local.hour] = hour_distribution.get(r_local.hour, 0) + 1

    # 4. Currently Occupied Tables (Right Now)
    now_local = datetime.now(local_tz)
    currently_occupied = sum(
        1 for r in daily_res
        if r.status in [ReservationStatus.CONFIRMED, ReservationStatus.SEATED]
        and (r.reservation_time.astimezone(local_tz) if r.reservation_time.tzinfo else r.reservation_time) <= now_local
        < (r.end_time.astimezone(local_tz) if r.end_time.tzinfo else r.end_time)
    )

    occupancy_pct = round((currently_occupied / active_tables * 100), 1) if active_tables > 0 else 0.0

    # Format Peak Hours (filtering hours with non-zero bookings)
    peak_hours = [
        PeakHourMetric(hour=f"{h:02d}:00", reservations_count=cnt)
        for h, cnt in sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)
        if cnt > 0
    ][:5]

    return AnalyticsResponse(
        restaurant_id=restaurant_id,
        date=target_date.isoformat(),
        total_tables=total_tables,
        active_tables=active_tables,
        currently_occupied_tables=currently_occupied,
        occupancy_rate_pct=occupancy_pct,
        total_parties_today=len([r for r in daily_res if r.status != ReservationStatus.CANCELLED]),
        total_guests_today=total_guests,
        status_breakdown=status_counts,
        peak_hours=peak_hours
    )
