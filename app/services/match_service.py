from sqlalchemy.orm import Session

from app.models import Ioc, Match, WatchlistItem
from app.repositories.match_repository import MatchRepository


class MatchService:
    def __init__(self, session: Session):
        self.matches = MatchRepository(session)

    def list(self, tenant_id) -> list[tuple[Match, WatchlistItem, Ioc]]:
        return self.matches.list_for_tenant(tenant_id)
