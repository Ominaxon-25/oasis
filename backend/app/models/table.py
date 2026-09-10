from typing import List, TYPE_CHECKING
from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.restaurant import Restaurant
    from app.models.reservation import Reservation


class TableZone(Base):
    __tablename__ = "table_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="zones")
    tables: Mapped[List["Table"]] = relationship(
        "Table",
        back_populates="zone",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<TableZone(id={self.id}, name='{self.name}', restaurant_id={self.restaurant_id})>"


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    zone_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("table_zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_number: Mapped[str] = mapped_column(String(50), nullable=False)
    min_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    zone: Mapped["TableZone"] = relationship("TableZone", back_populates="tables")
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation",
        back_populates="table",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Table(id={self.id}, number='{self.table_number}', cap={self.min_capacity}-{self.max_capacity})>"
