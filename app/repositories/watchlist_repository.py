from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import WatchlistItem


class WatchlistRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create(self, tenant_id, indicator_type: str, value: str) -> tuple[WatchlistItem, bool]:
        new_id = self.session.execute(
            insert(WatchlistItem)
            .values(tenant_id=tenant_id, type=indicator_type, value=value)
            .on_conflict_do_nothing(index_elements=["tenant_id", "type", "value"])
            .returning(WatchlistItem.id)
        ).scalar_one_or_none()
        query = select(WatchlistItem).where(
            WatchlistItem.tenant_id == tenant_id,
            WatchlistItem.type == indicator_type,
            WatchlistItem.value == value,
        )
        item = self.session.scalars(query).one()
        return item, new_id is not None

    def list_for_tenant(self, tenant_id) -> list[WatchlistItem]:
        query = (
            select(WatchlistItem)
            .where(WatchlistItem.tenant_id == tenant_id)
            .order_by(WatchlistItem.created_at)
        )
        return list(self.session.scalars(query))
