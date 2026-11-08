from fastapi import FastAPI

from app.errors import register_error_handlers
from app.routers import iocs, matches, watchlist

app = FastAPI(title="Mini IOC Matching Service", version="1.0.0")

register_error_handlers(app)
app.include_router(iocs.router)
app.include_router(watchlist.router)
app.include_router(matches.router)
