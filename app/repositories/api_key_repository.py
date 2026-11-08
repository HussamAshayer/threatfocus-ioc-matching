from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiKey


class ApiKeyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_hash(self, key_hash: str) -> ApiKey | None:
        query = select(ApiKey).where(ApiKey.key_hash == key_hash)
        return self.session.scalars(query).one_or_none()
