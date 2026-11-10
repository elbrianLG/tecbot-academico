"""Pruebas de compatibilidad: la API no expone rutas /api/v1."""

from fastapi.testclient import TestClient


def test_api_v1_consulta_no_existe(client: TestClient) -> None:
    response = client.post("/api/v1/consulta", json={"pregunta": "servicio social"})

    assert response.status_code == 404


def test_api_v1_salud_no_existe(client: TestClient) -> None:
    response = client.get("/api/v1/salud")

    assert response.status_code == 404
