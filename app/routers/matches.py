import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_tenant
from app.db import get_session
from app.schemas import MatchList
from app.services.match_service import MatchService

router = APIRouter(prefix="/api/v1/matches", tags=["Matches (tenant)"])


@router.get("", response_model=MatchList)
def list_matches(
    tenant_id: uuid.UUID = Depends(require_tenant),
    session: Session = Depends(get_session),
):
    rows = MatchService(session).list(tenant_id)
    return {
        "items": [
            {
                "id": match.id,
                "indicator": {"type": ioc.type, "value": ioc.value},
                "watchlist_item": {"id": item.id, "created_at": item.created_at},
                "ioc": {"id": ioc.id, "created_at": ioc.created_at},
                "matched_at": match.matched_at,
            }
            for match, item, ioc in rows
        ]
    }
