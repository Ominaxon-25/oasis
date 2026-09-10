from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.reservation import AvailabilityResponse
from app.services.availability import availability_engine

router = APIRouter(prefix="/availability", tags=["Availability Engine"])


@router.get("", response_model=AvailabilityResponse, summary="Query Real-Time Slot Availability")
async def check_availability(
    restaurant_id: int = Query(..., description="Target restaurant ID", example=1),
    date: date = Query(..., description="Target booking date (YYYY-MM-DD)", example="2026-09-10"),
    party_size: int = Query(..., ge=1, le=50, description="Party size", example=4),
    db: AsyncSession = Depends(get_db)
):
    """
    Computes all dynamically available booking time slots for a given restaurant, date, and party size.
    Filters active tables by capacity, bounds by operating hours, and ensures zero overlap with active bookings.
    """
    return await availability_engine.get_availability(
        db=db,
        restaurant_id=restaurant_id,
        target_date=date,
        party_size=party_size
    )
