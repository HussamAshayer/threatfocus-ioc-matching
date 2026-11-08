import threading

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Ioc, Match, Tenant, WatchlistItem
from app.services.ioc_service import IocService
from app.services.watchlist_service import WatchlistService


def run_together(*functions):
    barrier = threading.Barrier(len(functions))

    def wrap(fn):
        def run():
            with SessionLocal() as session:
                barrier.wait()
                fn(session)

        return run

    threads = [threading.Thread(target=wrap(fn)) for fn in functions]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def tenant_a_id():
    with SessionLocal() as session:
        return session.scalars(select(Tenant.id).where(Tenant.name == "Tenant A")).one()


def count(model) -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(model))


def test_identical_concurrent_ingests_create_one_record():
    ingest = lambda session: IocService(session).ingest("domain", "suspicious.example")  # noqa: E731
    run_together(ingest, ingest, ingest, ingest, ingest)
    assert count(Ioc) == 1


def test_identical_concurrent_watchlist_adds_create_one_item():
    tenant_id = tenant_a_id()
    add = lambda session: WatchlistService(session).add(tenant_id, "ipv4", "192.0.2.10")  # noqa: E731
    run_together(add, add, add, add, add)
    assert count(WatchlistItem) == 1


def test_concurrent_ioc_and_watchlist_add_still_match():
    tenant_id = tenant_a_id()
    for i in range(10):
        value = f"race{i}.example"
        run_together(
            lambda session: IocService(session).ingest("domain", value),
            lambda session: WatchlistService(session).add(tenant_id, "domain", value),
        )
    assert count(Match) == 10
