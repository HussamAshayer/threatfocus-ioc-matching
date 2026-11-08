# Architecture note

## Components

A single FastAPI service backed by PostgreSQL, in layers that each have one job:

- **Routers** (`app/routers`) handle HTTP only: parse the body, call a service, choose the status code.
- **Auth** (`app/auth.py`) turns `X-API-Key` into an identity. The key is hashed (SHA-256) and looked up in
  `api_keys`, which gives the role and, for tenants, the `tenant_id`. The tenant always comes from the key and never
  from the request.
- **Services** (`app/services`) implement the use cases: normalize, save, match, then commit once, so an IOC and
  its matches are saved together or not at all.
- **Repositories** (`app/repositories`) hold all database queries. Every tenant read takes a `tenant_id`; there is
  no method that lists another tenant's data.
- **Normalization** (`app/normalization.py`) holds pure functions shared by IOCs and watchlist items, so both sides
  are normalized identically, which is what makes exact matching work.

## Data model

| Table | Key columns | Uniqueness |
|-------|-------------|------------|
| `tenants` | `id`, `name` | `name` |
| `api_keys` | `key_hash`, `role`, `tenant_id` (NULL for admin) | `key_hash`; a CHECK ties role to tenant presence |
| `iocs` (shared) | `type`, `value` (normalized) | `(type, value)` |
| `watchlist_items` | `tenant_id`, `type`, `value` | `(tenant_id, type, value)` |
| `matches` | `tenant_id`, `watchlist_item_id`, `ioc_id`, `matched_at` | `(watchlist_item_id, ioc_id)` |

An IOC relates to many watchlist items (one per tenant watching it) through `matches`. A match stores its own
`tenant_id` so that listing is a simple `WHERE tenant_id = ?`. A composite foreign key
`(watchlist_item_id, tenant_id) → watchlist_items(id, tenant_id)` makes it impossible, at the database level, for a
match to be labelled with a tenant other than the owner of its watchlist item.

## Key decisions

- **The database enforces uniqueness, not application checks.** Inserts use `INSERT … ON CONFLICT DO NOTHING`, so
  two identical requests arriving together still produce one row and neither fails. The second request gets `200`
  with the existing record.
- **Matching runs in both directions, synchronously.** Ingesting an IOC matches existing watchlist items; adding a
  watchlist item matches an existing IOC. Re-running either step is harmless and can repair a missed match.
- **A per-indicator advisory lock** (`pg_advisory_xact_lock` on `type:value`) serializes an IOC ingest and a
  watchlist add for the same value. Without it, two concurrent transactions could each miss the other's uncommitted
  row and no match would be created. Different values never block each other.
- **API keys are stored hashed.** They are long random secrets, so a fast hash is enough (no bcrypt needed).

## Improvements at larger scale

1. **Asynchronous, set-based matching.** Accept IOCs in bulk (batch upserts), put them on a queue, and let workers
   run matching as one `INSERT … SELECT … ON CONFLICT DO NOTHING` per batch instead of per watcher. This decouples
   ingestion latency from the number of watchers.
2. **Operational hardening.** Add pagination to the list endpoints, API key rotation/expiry and per-key rate
   limits, and a managed key or tenant store. At very high volume, consider partitioning `matches` by tenant or time.
