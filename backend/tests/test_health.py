"""Pruebas de los endpoints de salud."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag import get_servicio_consulta


def test_salud_ok(client: TestClient) -> None:
    response = client.get("/api/salud")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_alias_mismo_cuerpo(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_salud_sin_prefijo_no_existe(client: TestClient) -> None:
    response = client.get("/salud")

    assert response.status_code == 404


def test_salud_200_aunque_el_corpus_no_este_indexado(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = get_servicio_consulta()
    monkeypatch.setattr(servicio, "esta_indexado", lambda: False)

    assert client.get("/api/salud").status_code == 200
    assert client.get("/api/health").status_code == 200

    consulta = client.post("/api/consulta", json={"pregunta": "servicio social"})
    assert consulta.status_code == 503
    assert consulta.json()["error"] == "corpus_no_indexado"


def test_health_es_alias_permanente_sin_deprecacion() -> None:
    rutas = app.openapi()["paths"]

    assert "/api/salud" in rutas
    assert "/api/health" in rutas
    assert not rutas["/api/health"]["get"].get("deprecated", False)
