# Mini IOC Matching Service

A small REST API that stores Indicators of Compromise (IOCs) in a shared catalog, lets each tenant keep a private
watchlist, and records exact matches between the two. Each match is visible only to the tenant that owns the
watchlist item.

**Stack:** Python 3.12 · FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Alembic · pytest · Docker Compose
(Option A from the assignment: local deployment).

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design note.

---

## Quick start

Requirements: Docker with Docker Compose.

```bash
docker compose up --build
```

This single command starts PostgreSQL, applies the database migrations, seeds two sample tenants with API keys,
and starts the API on **http://localhost:8000**. Interactive API docs (Swagger) are at **http://localhost:8000/docs**.

Stop it with `Ctrl+C`. To remove the containers **and** the database volume:

```bash
docker compose down -v
```

Ports used on the host: `8000` (API) and `5434` (PostgreSQL). If either is taken, change the left side of the
mapping in `docker-compose.yml`.

## Sample tenants and API keys

The seed creates these **development-only** keys (override them with environment variables; see Configuration):

| Role     | Tenant   | `X-API-Key`         |
|----------|----------|---------------------|
| admin    | (none)   | `dev-admin-key`     |
| tenant   | Tenant A | `dev-tenant-a-key`  |
| tenant   | Tenant B | `dev-tenant-b-key`  |

Only SHA-256 hashes of the keys are stored in the database. No real credentials are in this repository.

## Running the tests

With Docker (no local Python needed; the database container must be running, e.g. after `docker compose up -d`):

```bash
docker compose run --rm api pytest -v
```

Tests run against a separate database, `ioc_test`, which is created and migrated automatically, so they never
touch the demo data.

| File | Covers |
|------|--------|
| `tests/test_normalization.py` | Domain and IPv4 normalization and validation rules (unit tests, no database) |
| `tests/test_api.py` | Every acceptance scenario through the HTTP API: auth (401/403), ingestion, duplicates, invalid input (422), watchlists, matching in both orders, tenant isolation |
| `tests/test_concurrency.py` | Simultaneous identical requests, and an IOC and a watchlist item for the same value arriving at the same moment |

## Configuration

Settings are read from environment variables (or a `.env` file for local development without Docker):

| Variable | Purpose | Default in Docker Compose |
|----------|---------|---------------------------|
| `DATABASE_URL` | SQLAlchemy connection URL | `postgresql+psycopg://ioc:ioc@db:5432/ioc` |
| `ADMIN_API_KEY` | Seeded admin key | `dev-admin-key` |
| `TENANT_A_API_KEY` | Seeded key for Tenant A | `dev-tenant-a-key` |
| `TENANT_B_API_KEY` | Seeded key for Tenant B | `dev-tenant-b-key` |
| `TEST_DATABASE_URL` | Optional; test database URL | `DATABASE_URL` with the database name `ioc_test` |

## API

All requests require the `X-API-Key` header. Request bodies for both `POST` endpoints:

```json
{ "type": "domain", "value": "Suspicious.Example." }
```

`type` is `"ipv4"` or `"domain"` (lowercase). Any other fields, including a `tenant_id`, are ignored: the tenant is
always taken from the API key.

| Method | Endpoint | Key | Success |
|--------|----------|-----|---------|
| `POST` | `/api/v1/iocs` | admin | `201` created, `200` already existed (existing record returned) |
| `POST` | `/api/v1/watchlist-items` | tenant | `201` created, `200` already existed for this tenant |
| `GET`  | `/api/v1/watchlist-items` | tenant | `200` the caller's items only |
| `GET`  | `/api/v1/matches` | tenant | `200` the caller's matches only, newest first |

### Responses

IOC and watchlist item:
```json
{ "id": "uuid", "type": "domain", "value": "suspicious.example", "created_at": "2026-11-08T10:00:00Z" }
```

Lists are wrapped in an object so they can gain pagination later without breaking clients:
```json
{ "items": [ ... ] }
```

Match:
```json
{
  "id": "uuid",
  "indicator": { "type": "domain", "value": "suspicious.example" },
  "watchlist_item": { "id": "uuid", "created_at": "..." },
  "ioc": { "id": "uuid", "created_at": "..." },
  "matched_at": "2026-11-08T10:00:00Z"
}
```

### Errors

Every error uses the same shape:
```json
{ "error": { "code": "invalid_indicator", "message": "'256.1.1.1' is not a valid IPv4 address" } }
```

| Status | `code` | When |
|--------|--------|------|
| `401` | `unauthorized` | `X-API-Key` missing or unknown |
| `403` | `forbidden` | Valid key with the wrong role (tenant on the admin endpoint, or admin on tenant endpoints) |
| `422` | `validation_error` | Body malformed: missing field, unsupported `type`, value too long. Includes `details` per field. |
| `422` | `invalid_indicator` | `type` is valid but `value` is not a valid IPv4 address or domain |

Authentication is checked before the body, so a bad key always gives `401`, even with an invalid body.

## Demo: the assignment scenario with curl

```bash
API=http://localhost:8000/api/v1

# 1. Tenant A adds suspicious.example to its watchlist           -> 201
curl -s -X POST $API/watchlist-items -H "X-API-Key: dev-tenant-a-key" \
  -H "Content-Type: application/json" -d '{"type":"domain","value":"suspicious.example"}'

# 2. Admin ingests Suspicious.Example. (normalized, stored once)  -> 201
curl -s -X POST $API/iocs -H "X-API-Key: dev-admin-key" \
  -H "Content-Type: application/json" -d '{"type":"domain","value":"Suspicious.Example."}'

#    Sending it again returns the same record                     -> 200
curl -s -X POST $API/iocs -H "X-API-Key: dev-admin-key" \
  -H "Content-Type: application/json" -d '{"type":"domain","value":"SUSPICIOUS.EXAMPLE"}'

#    Tenant A sees the match
curl -s $API/matches -H "X-API-Key: dev-tenant-a-key"

# 3. Tenant B cannot see Tenant A's finding                       -> {"items":[]}
curl -s $API/matches -H "X-API-Key: dev-tenant-b-key"

# 4. Admin ingests 192.0.2.10; later Tenant B watches it          -> match created
curl -s -X POST $API/iocs -H "X-API-Key: dev-admin-key" \
  -H "Content-Type: application/json" -d '{"type":"ipv4","value":"192.0.2.10"}'
curl -s -X POST $API/watchlist-items -H "X-API-Key: dev-tenant-b-key" \
  -H "Content-Type: application/json" -d '{"type":"ipv4","value":"192.0.2.10"}'
curl -s $API/matches -H "X-API-Key: dev-tenant-b-key"

# Errors
curl -s $API/matches                                              # 401
curl -s -X POST $API/iocs -H "X-API-Key: dev-tenant-a-key" \
  -H "Content-Type: application/json" -d '{"type":"ipv4","value":"1.1.1.1"}'   # 403
curl -s -X POST $API/iocs -H "X-API-Key: dev-admin-key" \
  -H "Content-Type: application/json" -d '{"type":"ipv4","value":"256.1.1.1"}' # 422
```

## Normalization rules and assumptions

**Domains**
- Surrounding whitespace is trimmed, letters are lowercased, and one trailing dot is removed
  (`Suspicious.Example.` → `suspicious.example`).
- Total length 1–253 characters, at least two labels (`localhost` is rejected).
- Each label is 1–63 characters of `a-z`, `0-9` and `-`, and does not start or end with `-`.
  This rejects URLs, paths, spaces, underscores and empty labels (`http://evil.com`, `evil.com/x`, `evil..com`).
- A value whose last label is all digits (for example `192.0.2.10`) is rejected as a domain; send it as `ipv4`.
- Internationalized names must be sent in their ASCII (punycode) form, e.g. `xn--caf-dma.com`; `café.com` is rejected.

**IPv4**
- Surrounding whitespace is trimmed and the value is parsed with Python's `ipaddress` module, then stored in
  canonical dotted-decimal form.
- Octets with leading zeros (`192.0.2.010`) are rejected, because some systems read them as octal.
- All IPv4 ranges are accepted, including private and reserved ones. IPv6 is out of scope and rejected.

**Matching** is exact equality on `(type, normalized value)`. `example.com` does not match `sub.example.com`.

**Other assumptions**
- A duplicate request is treated as a successful retry: it returns `200` with the existing record (idempotent),
  rather than `409 Conflict`.
- Tenants and API keys are created by the seed; managing them through the API is out of scope.
- There are no delete or update endpoints, and list endpoints are not paginated (both are listed as improvements).

## Local development without Docker (optional)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d db          # only the database
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload    # http://localhost:8000
pytest -v
```

## Project structure

```
app/
├── main.py            FastAPI app: routers + error handlers
├── config.py          Settings from environment / .env
├── db.py              Engine, session factory, per-request session
├── models/            SQLAlchemy tables (one file per table)
├── schemas.py         Request/response models (Pydantic)
├── normalization.py   Domain/IPv4 validation and normalization (pure functions)
├── security.py        API key hashing
├── auth.py            X-API-Key -> admin or tenant (401/403)
├── errors.py          Consistent error response format
├── repositories/      Database access only
├── services/          Use cases: normalize -> save -> match -> commit
├── routers/           HTTP endpoints
└── seed.py            Sample tenants and API keys (idempotent)
alembic/               Migrations
tests/                 Unit, API and concurrency tests
```

## AI assistance

I used an AI assistant as a pair-programming and learning aid for this exercise: to explain
concepts, discuss design options, and help draft code, tests and documentation. I built the project step by step,
reviewed and ran all of it, and can explain every part of the submitted code and design.
