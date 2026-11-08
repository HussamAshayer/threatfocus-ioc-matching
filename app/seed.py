from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import SessionLocal
from app.models import ApiKey, Tenant
from app.security import hash_api_key


def get_or_create_tenant(session, name):
    session.execute(insert(Tenant).values(name=name).on_conflict_do_nothing())
    return session.scalars(select(Tenant).where(Tenant.name == name)).one()


def create_key_if_missing(session, raw_key, role, tenant_id):
    session.execute(
        insert(ApiKey)
        .values(key_hash=hash_api_key(raw_key), role=role, tenant_id=tenant_id)
        .on_conflict_do_nothing()
    )


def seed():
    with SessionLocal.begin() as session:
        tenant_a = get_or_create_tenant(session, "Tenant A")
        tenant_b = get_or_create_tenant(session, "Tenant B")
        create_key_if_missing(session, settings.admin_api_key, "admin", None)
        create_key_if_missing(session, settings.tenant_a_api_key, "tenant", tenant_a.id)
        create_key_if_missing(session, settings.tenant_b_api_key, "tenant", tenant_b.id)


if __name__ == "__main__":
    seed()
    print("Seed complete")
