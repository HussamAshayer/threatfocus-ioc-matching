import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth import require_tenant
from app.db import get_session
from app.schemas import IndicatorIn, WatchlistItemList, WatchlistItemOut
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/api/v1/watchlist-items", tags=["Watchlist (tenant)"])


@router.post(
    "",
    response_model=WatchlistItemOut,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "Item already existed for this tenant; the existing record is returned"}},
)
def add_watchlist_item(
    body: IndicatorIn,
    response: Response,
    tenant_id: uuid.UUID = Depends(require_tenant),
    session: Session = Depends(get_session),
):
    item, created = WatchlistService(session).add(tenant_id, body.type, body.value)
    if not created:
        response.status_code = status.HTTP_200_OK
    return item


@router.get("", response_model=WatchlistItemList)
def list_watchlist_items(
    tenant_id: uuid.UUID = Depends(require_tenant),
    session: Session = Depends(get_session),
):
    return {"items": WatchlistService(session).list(tenant_id)}
