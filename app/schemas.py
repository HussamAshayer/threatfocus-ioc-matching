import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IndicatorType = Literal["ipv4", "domain"]


class IndicatorIn(BaseModel):
    type: IndicatorType
    value: str = Field(min_length=1, max_length=300)


class Indicator(BaseModel):
    type: IndicatorType
    value: str


class IocOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: IndicatorType
    value: str
    created_at: datetime


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: IndicatorType
    value: str
    created_at: datetime


class WatchlistItemList(BaseModel):
    items: list[WatchlistItemOut]


class MatchedRecord(BaseModel):
    id: uuid.UUID
    created_at: datetime


class MatchOut(BaseModel):
    id: uuid.UUID
    indicator: Indicator
    watchlist_item: MatchedRecord
    ioc: MatchedRecord
    matched_at: datetime


class MatchList(BaseModel):
    items: list[MatchOut]
