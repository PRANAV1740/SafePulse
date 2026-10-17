"""Shared pytest fixtures: isolated in-memory DB + TestClient, stub mode forced."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import config
from app.db import get_session
from app.main import app


@pytest.fixture(autouse=True)
def _force_offline(monkeypatch):
    """Force stub extraction and disable external geocoding for deterministic tests."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("ENABLE_NOMINATIM", "false")
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
def engine():
    import app.models  # noqa: F401 - register tables on metadata

    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as sess:
        yield sess


@pytest.fixture
def client(engine):
    def _override():
        with Session(engine) as sess:
            yield sess

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
