from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Ioc


class IocRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_value(self, indicator_type: str, value: str) -> Ioc | None:
        query = select(Ioc).where(Ioc.type == indicator_type, Ioc.value == value)
        return self.session.scalars(query).one_or_none()

    def get_or_create(self, indicator_type: str, value: str) -> tuple[Ioc, bool]:
        new_id = self.session.execute(
            insert(Ioc)
            .values(type=indicator_type, value=value)
            .on_conflict_do_nothing(index_elements=["type", "value"])
            .returning(Ioc.id)
        ).scalar_one_or_none()
        ioc = self.get_by_value(indicator_type, value)
        return ioc, new_id is not None
