from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Ioc, Match, WatchlistItem

DOMAIN = {"type": "domain", "value": "suspicious.example"}
IP = {"type": "ipv4", "value": "192.0.2.10"}


def count(model) -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(model))


# --- Authentication and authorization ---


def test_missing_api_key_returns_401(client):
    response = client.get("/api/v1/matches")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_invalid_api_key_returns_401(client):
    response = client.get("/api/v1/matches", headers={"X-API-Key": "not-a-real-key"})
    assert response.status_code == 401


def test_tenant_key_cannot_ingest_iocs(client, tenant_a):
    response = client.post("/api/v1/iocs", json=DOMAIN, headers=tenant_a)
    assert response.status_code == 403
    assert count(Ioc) == 0


def test_admin_key_cannot_use_tenant_endpoints(client, admin):
    assert client.get("/api/v1/watchlist-items", headers=admin).status_code == 403
    assert client.get("/api/v1/matches", headers=admin).status_code == 403
    assert client.post("/api/v1/watchlist-items", json=DOMAIN, headers=admin).status_code == 403


def test_client_supplied_tenant_id_is_ignored(client, tenant_a, tenant_b):
    client.post("/api/v1/watchlist-items", json=DOMAIN, headers=tenant_a)
    tenant_a_id = client.get("/api/v1/watchlist-items", headers=tenant_a).json()["items"][0]["id"]

    body = {**IP, "tenant_id": tenant_a_id}
    client.post("/api/v1/watchlist-items", json=body, headers=tenant_b)

    a_values = [i["value"] for i in client.get("/api/v1/watchlist-items", headers=tenant_a).json()["items"]]
    b_values = [i["value"] for i in client.get("/api/v1/watchlist-items", headers=tenant_b).json()["items"]]
    assert a_values == ["suspicious.example"]
    assert b_values == ["192.0.2.10"]


# --- IOC ingestion ---


def test_repeated_ingestion_produces_one_catalog_record(client, admin):
    first = client.post("/api/v1/iocs", json=DOMAIN, headers=admin)
    second = client.post("/api/v1/iocs", json=DOMAIN, headers=admin)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert count(Ioc) == 1


def test_equivalent_domain_spellings_are_stored_once(client, admin):
    spellings = ["Suspicious.Example.", "SUSPICIOUS.EXAMPLE", "suspicious.example"]
    responses = [client.post("/api/v1/iocs", json={"type": "domain", "value": v}, headers=admin) for v in spellings]

    assert {r.json()["value"] for r in responses} == {"suspicious.example"}
    assert count(Ioc) == 1


def test_ipv4_is_stored_in_canonical_form(client, admin):
    response = client.post("/api/v1/iocs", json={"type": "ipv4", "value": " 192.0.2.10 "}, headers=admin)
    assert response.status_code == 201
    assert response.json()["value"] == "192.0.2.10"


def test_invalid_domain_is_rejected_with_clear_error(client, admin):
    response = client.post("/api/v1/iocs", json={"type": "domain", "value": "http://evil.com"}, headers=admin)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_indicator"
    assert "not a valid domain" in response.json()["error"]["message"]
    assert count(Ioc) == 0


def test_invalid_ipv4_is_rejected_with_clear_error(client, admin):
    response = client.post("/api/v1/iocs", json={"type": "ipv4", "value": "256.1.1.1"}, headers=admin)
    assert response.status_code == 422
    assert "not a valid IPv4 address" in response.json()["error"]["message"]
    assert count(Ioc) == 0


def test_unsupported_type_and_missing_value_are_rejected(client, admin):
    response = client.post("/api/v1/iocs", json={"type": "email"}, headers=admin)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert {d["field"] for d in error["details"]} == {"type", "value"}


def test_malformed_json_is_rejected(client, admin):
    response = client.post(
        "/api/v1/iocs", content="not json", headers={**admin, "Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body"


# --- Watchlists ---


def test_duplicate_watchlist_item_is_not_created(client, tenant_a):
    first = client.post("/api/v1/watchlist-items", json=DOMAIN, headers=tenant_a)
    second = client.post("/api/v1/watchlist-items", json={"type": "domain", "value": "Suspicious.Example."}, headers=tenant_a)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert count(WatchlistItem) == 1


def test_tenant_b_cannot_see_tenant_a_watchlist(client, tenant_a, tenant_b):
    client.post("/api/v1/watchlist-items", json=DOMAIN, headers=tenant_a)

    response = client.get("/api/v1/watchlist-items", headers=tenant_b)
    assert response.status_code == 200
    assert response.json() == {"items": []}


# --- Matching ---


def test_match_created_when_ioc_arrives_after_watchlist_item(client, admin, tenant_a):
    client.post("/api/v1/watchlist-items", json=DOMAIN, headers=tenant_a)
    client.post("/api/v1/iocs", json={"type": "domain", "value": "Suspicious.Example."}, headers=admin)

    matches = client.get("/api/v1/matches", headers=tenant_a).json()["items"]
    assert len(matches) == 1
    assert matches[0]["indicator"] == {"type": "domain", "value": "suspicious.example"}
    assert {"id", "watchlist_item", "ioc", "matched_at"} <= matches[0].keys()


def test_match_created_when_watchlist_item_added_after_ioc(client, admin, tenant_b):
    ioc = client.post("/api/v1/iocs", json=IP, headers=admin).json()
    item = client.post("/api/v1/watchlist-items", json=IP, headers=tenant_b).json()

    matches = client.get("/api/v1/matches", headers=tenant_b).json()["items"]
    assert len(matches) == 1
    assert matches[0]["ioc"]["id"] == ioc["id"]
    assert matches[0]["watchlist_item"]["id"] == item["id"]


def test_tenant_b_cannot_see_tenant_a_matches(client, admin, tenant_a, tenant_b):
    client.post("/api/v1/watchlist-items", json=DOMAIN, headers=tenant_a)
    client.post("/api/v1/iocs", json=DOMAIN, headers=admin)

    assert len(client.get("/api/v1/matches", headers=tenant_a).json()["items"]) == 1
    assert client.get("/api/v1/matches", headers=tenant_b).json() == {"items": []}


def test_two_tenants_watching_same_ioc_get_separate_matches(client, admin, tenant_a, tenant_b):
    client.post("/api/v1/watchlist-items", json=DOMAIN, headers=tenant_a)
    client.post("/api/v1/watchlist-items", json=DOMAIN, headers=tenant_b)
    client.post("/api/v1/iocs", json=DOMAIN, headers=admin)

    a_matches = client.get("/api/v1/matches", headers=tenant_a).json()["items"]
    b_matches = client.get("/api/v1/matches", headers=tenant_b).json()["items"]
    assert len(a_matches) == 1
    assert len(b_matches) == 1
    assert a_matches[0]["id"] != b_matches[0]["id"]
    assert a_matches[0]["watchlist_item"]["id"] != b_matches[0]["watchlist_item"]["id"]
    assert a_matches[0]["ioc"]["id"] == b_matches[0]["ioc"]["id"]
    assert count(Ioc) == 1


def test_retrying_requests_does_not_duplicate_matches(client, admin, tenant_a):
    for _ in range(3):
        client.post("/api/v1/watchlist-items", json=DOMAIN, headers=tenant_a)
        client.post("/api/v1/iocs", json=DOMAIN, headers=admin)

    assert count(WatchlistItem) == 1
    assert count(Ioc) == 1
    assert count(Match) == 1
    assert len(client.get("/api/v1/matches", headers=tenant_a).json()["items"]) == 1


def test_non_matching_values_create_no_match(client, admin, tenant_a):
    client.post("/api/v1/watchlist-items", json={"type": "domain", "value": "example.com"}, headers=tenant_a)
    client.post("/api/v1/iocs", json={"type": "domain", "value": "sub.example.com"}, headers=admin)
    client.post("/api/v1/iocs", json={"type": "domain", "value": "example.co"}, headers=admin)

    assert client.get("/api/v1/matches", headers=tenant_a).json() == {"items": []}
