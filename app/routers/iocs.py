from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_session
from app.schemas import IndicatorIn, IocOut
from app.services.ioc_service import IocService

router = APIRouter(prefix="/api/v1/iocs", tags=["IOCs (admin)"])


@router.post(
    "",
    response_model=IocOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    responses={200: {"description": "IOC already existed; the existing record is returned"}},
)
def ingest_ioc(body: IndicatorIn, response: Response, session: Session = Depends(get_session)):
    ioc, created = IocService(session).ingest(body.type, body.value)
    if not created:
        response.status_code = status.HTTP_200_OK
    return ioc
