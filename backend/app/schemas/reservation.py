from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationStatus


class ReservationBase(BaseModel):
    restaurant_id: int
    table_id: int
    customer_name: str = Field(..., max_length=120, example="Alisher Usmanov")
    customer_phone: str = Field(..., max_length=40, example="+998901234567")
    party_size: int = Field(..., ge=1, le=50, example=4)
    reservation_time: datetime = Field(..., example="2026-09-10T19:00:00+05:00")


class ReservationCreate(ReservationBase):
    end_time: Optional[datetime] = None  # If omitted, auto-calculated based on restaurant avg_turn_time


class ReservationStatusUpdate(BaseModel):
    status: ReservationStatus


class ReservationOut(ReservationBase):
    id: int
    end_time: datetime
    status: ReservationStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimeSlotOut(BaseModel):
    time: str  # ISO string or "19:00"
    slot_start: datetime
    slot_end: datetime
    available_tables_count: int
    matching_table_ids: list[int]


class AvailabilityResponse(BaseModel):
    restaurant_id: int
    date: str
    party_size: int
    available_slots: list[TimeSlotOut]
