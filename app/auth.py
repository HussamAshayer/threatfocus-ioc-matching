import uuid

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import ApiKey
from app.repositories.api_key_repository import ApiKeyRepository
from app.security import hash_api_key

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(
    raw_key: str | None = Security(api_key_header),
    session: Session = Depends(get_session),
) -> ApiKey:
    if not raw_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-API-Key header")
    api_key = ApiKeyRepository(session).get_by_hash(hash_api_key(raw_key))
    if api_key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return api_key


def require_admin(api_key: ApiKey = Depends(get_api_key)) -> None:
    if api_key.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin API key required")


def require_tenant(api_key: ApiKey = Depends(get_api_key)) -> uuid.UUID:
    if api_key.role != "tenant":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tenant API key required")
    return api_key.tenant_id
