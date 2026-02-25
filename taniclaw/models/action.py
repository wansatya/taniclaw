"""SQLAlchemy models — Action."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taniclaw.models.base import Base


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plants.id"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="rules")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    plant: Mapped["Plant"] = relationship("Plant", back_populates="actions")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Action {self.action_type!r} for plant={self.plant_id} status={self.status!r}>"
