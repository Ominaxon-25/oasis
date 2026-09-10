from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.models.reservation import ReservationStatus
from app.schemas.reservation import ReservationOut


class FloorPlanTableOut(BaseModel):
    id: int
    table_number: str
    min_capacity: int
    max_capacity: int
    is_active: bool
    live_status: str  # "AVAILABLE", "SEATED", "RESERVED", "BLOCKED"
    active_reservation: Optional[ReservationOut] = None

    model_config = ConfigDict(from_attributes=True)


class FloorPlanZoneOut(BaseModel):
    zone_id: int
    zone_name: str
    tables: List[FloorPlanTableOut]


class FloorPlanResponse(BaseModel):
    restaurant_id: int
    restaurant_name: str
    queried_at: datetime
    zones: List[FloorPlanZoneOut]


class PeakHourMetric(BaseModel):
    hour: str
    reservations_count: int


class AnalyticsResponse(BaseModel):
    restaurant_id: int
    date: str
    total_tables: int
    active_tables: int
    currently_occupied_tables: int
    occupancy_rate_pct: float
    total_parties_today: int
    total_guests_today: int
    status_breakdown: Dict[str, int]
    peak_hours: List[PeakHourMetric]
