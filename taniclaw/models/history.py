"""SQLAlchemy models — History and WeatherCache."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taniclaw.models.base import Base


class History(Base):
    __tablename__ = "history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plants.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    plant: Mapped["Plant"] = relationship("Plant", back_populates="history")  # noqa: F821


class WeatherCache(Base):
    __tablename__ = "weather_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    temp_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    temp_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("latitude", "longitude", "date", name="uq_weather_location_date"),)
