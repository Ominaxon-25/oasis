from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TableZoneBase(BaseModel):
    name: str = Field(..., max_length=100, example="Main Hall")


class TableZoneCreate(TableZoneBase):
    restaurant_id: int


class TableBase(BaseModel):
    table_number: str = Field(..., max_length=50, example="T-1")
    min_capacity: int = Field(default=1, ge=1, example=2)
    max_capacity: int = Field(default=4, ge=1, example=4)
    is_active: bool = Field(default=True)


class TableCreate(TableBase):
    zone_id: int


class TableOut(TableBase):
    id: int
    zone_id: int

    model_config = ConfigDict(from_attributes=True)


class TableZoneOut(TableZoneBase):
    id: int
    restaurant_id: int
    tables: List[TableOut] = []

    model_config = ConfigDict(from_attributes=True)


class TableStatusUpdate(BaseModel):
    is_active: Optional[bool] = None
    seat_walk_in: Optional[bool] = None  # If true, seats walk-in directly
    party_size: Optional[int] = Field(default=None, ge=1)
    customer_name: Optional[str] = Field(default="Walk-in Guest")
    customer_phone: Optional[str] = Field(default="+998900000000")
