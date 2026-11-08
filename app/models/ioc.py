import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Ioc(Base):
    __tablename__ = "iocs"
    __table_args__ = (
        UniqueConstraint("type", "value"),
        CheckConstraint("type IN ('ipv4', 'domain')", name="type_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(10))
    value: Mapped[str] = mapped_column(String(253))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
