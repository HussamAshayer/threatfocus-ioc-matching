from sqlalchemy.orm import Session

from app.models import Ioc
from app.normalization import normalize
from app.repositories.ioc_repository import IocRepository
from app.repositories.match_repository import MatchRepository


class IocService:
    def __init__(self, session: Session):
        self.session = session
        self.iocs = IocRepository(session)
        self.matches = MatchRepository(session)

    def ingest(self, indicator_type: str, raw_value: str) -> tuple[Ioc, bool]:
        value = normalize(indicator_type, raw_value)
        self.matches.lock_indicator(indicator_type, value)
        ioc, created = self.iocs.get_or_create(indicator_type, value)
        self.matches.create_for_ioc(ioc)
        self.session.commit()
        return ioc, created
