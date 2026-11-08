import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("watchlist_item_id", "ioc_id"),
        # A match's tenant_id must be the owner of its watchlist item.
        ForeignKeyConstraint(
            ["watchlist_item_id", "tenant_id"],
            ["watchlist_items.id", "watchlist_items.tenant_id"],
        ),
        Index("ix_matches_tenant_id_matched_at", "tenant_id", "matched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column()
    watchlist_item_id: Mapped[uuid.UUID] = mapped_column()
    ioc_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iocs.id"))
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
