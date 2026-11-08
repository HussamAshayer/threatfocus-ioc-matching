from sqlalchemy.orm import Session

from app.models import WatchlistItem
from app.normalization import normalize
from app.repositories.match_repository import MatchRepository
from app.repositories.watchlist_repository import WatchlistRepository


class WatchlistService:
    def __init__(self, session: Session):
        self.session = session
        self.items = WatchlistRepository(session)
        self.matches = MatchRepository(session)

    def add(self, tenant_id, indicator_type: str, raw_value: str) -> tuple[WatchlistItem, bool]:
        value = normalize(indicator_type, raw_value)
        self.matches.lock_indicator(indicator_type, value)
        item, created = self.items.get_or_create(tenant_id, indicator_type, value)
        self.matches.create_for_item(item)
        self.session.commit()
        return item, created

    def list(self, tenant_id) -> list[WatchlistItem]:
        return self.items.list_for_tenant(tenant_id)
