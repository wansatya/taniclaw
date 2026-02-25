"""SQLAlchemy models — Plant."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taniclaw.models.base import Base


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    plant_type: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    plant_date: Mapped[date] = mapped_column(Date, nullable=False)
    growing_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    soil_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_state: Mapped[str] = mapped_column(String(30), nullable=False, default="seed")
    state_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    actions: Mapped[list["Action"]] = relationship(  # noqa: F821
        "Action", back_populates="plant", cascade="all, delete-orphan"
    )
    history: Mapped[list["History"]] = relationship(  # noqa: F821
        "History", back_populates="plant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Plant {self.name!r} ({self.plant_type}) state={self.current_state!r}>"
