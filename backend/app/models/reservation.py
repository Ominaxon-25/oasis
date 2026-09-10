import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.restaurant import Restaurant
    from app.models.table import Table


class ReservationStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SEATED = "SEATED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    reservation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[ReservationStatus] = mapped_column(
        SQLEnum(ReservationStatus), default=ReservationStatus.CONFIRMED, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="reservations")
    table: Mapped["Table"] = relationship("Table", back_populates="reservations")

    def __repr__(self) -> str:
        return f"<Reservation(id={self.id}, table_id={self.table_id}, party={self.party_size}, time={self.reservation_time}, status='{self.status}')>"
