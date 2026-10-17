"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import clusters, reports, tickets
from app.schemas import HealthOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="SafePulse API", version="0.1.0", lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router)
app.include_router(clusters.router)
app.include_router(tickets.router)


@app.get("/api/health", response_model=HealthOut, tags=["health"])
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        gemini_configured=_settings.gemini_configured,
        extractor_mode="live" if _settings.gemini_configured else "stub",
        nominatim_enabled=_settings.enable_nominatim,
    )
