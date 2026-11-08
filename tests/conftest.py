import os

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# Point the app at a separate test database BEFORE any app module reads settings.
_main_url = os.environ.get("DATABASE_URL") or dotenv_values(".env").get("DATABASE_URL")
_test_url = os.environ.get("TEST_DATABASE_URL") or make_url(_main_url).set(database="ioc_test").render_as_string(
    hide_password=False
)
os.environ["DATABASE_URL"] = _test_url

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _create_test_database() -> None:
    url = make_url(_test_url)
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def database():
    _create_test_database()
    command.upgrade(Config("alembic.ini"), "head")
    from app.seed import seed

    seed()


@pytest.fixture(autouse=True)
def clean_tables():
    from app.db import engine

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE matches, watchlist_items, iocs"))


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture
def admin():
    from app.config import settings

    return {"X-API-Key": settings.admin_api_key}


@pytest.fixture
def tenant_a():
    from app.config import settings

    return {"X-API-Key": settings.tenant_a_api_key}


@pytest.fixture
def tenant_b():
    from app.config import settings

    return {"X-API-Key": settings.tenant_b_api_key}
