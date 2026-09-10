from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class RestaurantBase(BaseModel):
    name: str = Field(..., max_length=150, example="Veranda Lounge")
    timezone: str = Field(default="Asia/Tashkent", example="Asia/Tashkent")
    operating_hours: Dict[str, Any] = Field(
        default_factory=lambda: {"open": "12:00", "close": "23:00"},
        example={"open": "12:00", "close": "23:00"}
    )
    avg_turn_time_mins: int = Field(default=90, ge=15, le=360, example=90)


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantOut(RestaurantBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
