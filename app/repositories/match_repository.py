from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Ioc, Match, WatchlistItem


class MatchRepository:
    def __init__(self, session: Session):
        self.session = session

    def lock_indicator(self, indicator_type: str, value: str) -> None:
        # Serializes concurrent IOC ingests and watchlist adds for the same indicator,
        # so neither transaction misses the other's uncommitted row. Released on commit/rollback.
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"{indicator_type}:{value}"},
        )

    def _create(self, item: WatchlistItem, ioc: Ioc) -> bool:
        new_id = self.session.execute(
            insert(Match)
            .values(tenant_id=item.tenant_id, watchlist_item_id=item.id, ioc_id=ioc.id)
            .on_conflict_do_nothing(index_elements=["watchlist_item_id", "ioc_id"])
            .returning(Match.id)
        ).scalar_one_or_none()
        return new_id is not None

    def create_for_ioc(self, ioc: Ioc) -> int:
        query = select(WatchlistItem).where(
            WatchlistItem.type == ioc.type, WatchlistItem.value == ioc.value
        )
        watchers = self.session.scalars(query).all()
        return sum(self._create(item, ioc) for item in watchers)

    def create_for_item(self, item: WatchlistItem) -> int:
        query = select(Ioc).where(Ioc.type == item.type, Ioc.value == item.value)
        ioc = self.session.scalars(query).one_or_none()
        if ioc is None:
            return 0
        return int(self._create(item, ioc))

    def list_for_tenant(self, tenant_id) -> list[tuple[Match, WatchlistItem, Ioc]]:
        query = (
            select(Match, WatchlistItem, Ioc)
            .join(WatchlistItem, WatchlistItem.id == Match.watchlist_item_id)
            .join(Ioc, Ioc.id == Match.ioc_id)
            .where(Match.tenant_id == tenant_id)
            .order_by(Match.matched_at.desc())
        )
        return [tuple(row) for row in self.session.execute(query)]
