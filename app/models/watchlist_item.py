import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "type", "value"),
        # Target for the composite foreign key on matches.
        UniqueConstraint("id", "tenant_id"),
        CheckConstraint("type IN ('ipv4', 'domain')", name="type_valid"),
        Index("ix_watchlist_items_type_value", "type", "value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    type: Mapped[str] = mapped_column(String(10))
    value: Mapped[str] = mapped_column(String(253))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
