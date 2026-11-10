"""Fixtures compartidas por la suite del backend."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def _limpiar_dependency_overrides() -> Iterator[None]:
    """Garantiza que cada prueba arranque sin overrides de dependencias."""

    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
