"""Pruebas de POST /api/consulta: normalización, validación y contrato de respuesta."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_consulta_valida() -> None:
    response = client.post("/api/consulta", json={"pregunta": "¿Qué es una derivada?"})
    assert response.status_code == 200
    body = response.json()
    assert body["pregunta"] == "¿Qué es una derivada?"
    assert isinstance(body["respuesta"], str)
    assert body["respuesta"] != ""
    assert body["fuentes"] == []


def test_consulta_normaliza_espacios_extremos() -> None:
    response = client.post("/api/consulta", json={"pregunta": "  ¿Qué es una derivada?  "})
    assert response.status_code == 200
    assert response.json()["pregunta"] == "¿Qué es una derivada?"


def test_consulta_vacia() -> None:
    response = client.post("/api/consulta", json={"pregunta": ""})
    assert response.status_code == 422


@pytest.mark.parametrize("pregunta", ["   ", "\t\n", " \r "])
def test_consulta_solo_espacios(pregunta: str) -> None:
    response = client.post("/api/consulta", json={"pregunta": pregunta})
    assert response.status_code == 422


def test_consulta_campo_faltante() -> None:
    response = client.post("/api/consulta", json={})
    assert response.status_code == 422


def test_consulta_tipo_incorrecto() -> None:
    response = client.post("/api/consulta", json={"pregunta": 123})
    assert response.status_code == 422


def test_consulta_pregunta_muy_larga() -> None:
    response = client.post("/api/consulta", json={"pregunta": "a" * 2001})
    assert response.status_code == 422


def test_consulta_limite_sobre_texto_normalizado() -> None:
    # 2010 caracteres con 20 espacios finales: 1990 tras el strip -> válido.
    response = client.post("/api/consulta", json={"pregunta": "a" * 1990 + " " * 20})
    assert response.status_code == 200
    assert response.json()["pregunta"] == "a" * 1990


def test_consulta_get_rechazado() -> None:
    response = client.get("/api/consulta")
    assert response.status_code == 405
