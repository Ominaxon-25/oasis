from typing import List, TYPE_CHECKING
from sqlalchemy import Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.table import TableZone
    from app.models.reservation import Reservation


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Tashkent", nullable=False)
    operating_hours: Mapped[dict] = mapped_column(JSON, nullable=False)
    avg_turn_time_mins: Mapped[int] = mapped_column(Integer, default=90, nullable=False)

    # Relationships
    zones: Mapped[List["TableZone"]] = relationship(
        "TableZone",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Restaurant(id={self.id}, name='{self.name}', timezone='{self.timezone}')>"
