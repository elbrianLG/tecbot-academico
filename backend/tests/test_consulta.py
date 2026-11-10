"""Pruebas de POST /api/consulta con el contrato de respuesta v1.1."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.constants import ADVERTENCIA_SIN_EVIDENCIA, RESPUESTA_SIN_EVIDENCIA
from app.main import app
from app.rag import (
    CorpusNoIndexadoError,
    GeneracionInvalidaError,
    ServicioNoDisponibleError,
    TiempoAgotadoError,
    get_servicio_consulta,
)
from app.schemas.consulta import ConsultaResponse, FuenteDocumental


class ServicioFalso:
    """Servicio de consulta controlable para probar la capa HTTP."""

    def __init__(
        self,
        respuesta: ConsultaResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.respuesta = respuesta
        self.error = error
        self.preguntas: list[str] = []

    def consultar(self, pregunta: str) -> ConsultaResponse:
        self.preguntas.append(pregunta)
        if self.error is not None:
            raise self.error
        assert self.respuesta is not None, "El servicio falso no tiene respuesta configurada."
        return self.respuesta


def _instalar(servicio: ServicioFalso) -> ServicioFalso:
    app.dependency_overrides[get_servicio_consulta] = lambda: servicio
    return servicio


def _respuesta_fundamentada() -> ConsultaResponse:
    return ConsultaResponse(
        respuesta="Para iniciar el servicio social debes entregar la solicitud.",
        fuentes=[
            FuenteDocumental(
                documento="servicio-social.md",
                fragmento="entregar la solicitud en el departamento",
            )
        ],
        advertencia=None,
    )


def test_consulta_valida_contrato(client: TestClient) -> None:
    servicio = _instalar(ServicioFalso(respuesta=_respuesta_fundamentada()))

    response = client.post("/api/consulta", json={"pregunta": "¿Qué necesito para el servicio social?"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"respuesta", "fuentes", "advertencia"}
    assert "pregunta" not in body
    assert body["advertencia"] is None
    assert body["fuentes"] == [
        {
            "documento": "servicio-social.md",
            "fragmento": "entregar la solicitud en el departamento",
        }
    ]
    assert servicio.preguntas == ["¿Qué necesito para el servicio social?"]


def test_advertencia_presente_y_none_con_fundamento(client: TestClient) -> None:
    _instalar(ServicioFalso(respuesta=_respuesta_fundamentada()))

    body = client.post("/api/consulta", json={"pregunta": "servicio social"}).json()

    assert "advertencia" in body
    assert body["advertencia"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"pregunta": ""},
        {"pregunta": "   "},
        {"pregunta": "\t\n"},
        {},
        {"pregunta": 123},
        {"pregunta": "a" * 1001},
        {"pregunta": "pregunta válida", "top_k": 3},
    ],
    ids=[
        "vacia",
        "solo-espacios",
        "solo-blanco",
        "faltante",
        "tipo-incorrecto",
        "1001-caracteres",
        "campo-extra",
    ],
)
def test_consulta_invalida(payload: dict[str, Any], client: TestClient) -> None:
    servicio = _instalar(ServicioFalso(respuesta=_respuesta_fundamentada()))

    response = client.post("/api/consulta", json=payload)

    assert response.status_code == 422
    assert servicio.preguntas == []


def test_consulta_limite_exacto_de_1000(client: TestClient) -> None:
    servicio = _instalar(ServicioFalso(respuesta=_respuesta_fundamentada()))

    response = client.post("/api/consulta", json={"pregunta": "a" * 1000})

    assert response.status_code == 200
    assert servicio.preguntas == ["a" * 1000]


def test_consulta_strip_antes_de_validar_longitud(client: TestClient) -> None:
    servicio = _instalar(ServicioFalso(respuesta=_respuesta_fundamentada()))
    pregunta = "a" * 990 + " " * 20

    response = client.post("/api/consulta", json={"pregunta": pregunta})

    assert response.status_code == 200
    assert servicio.preguntas == ["a" * 990]


def test_consulta_sin_evidencia(client: TestClient) -> None:
    servicio = _instalar(
        ServicioFalso(
            respuesta=ConsultaResponse(
                respuesta=RESPUESTA_SIN_EVIDENCIA,
                fuentes=[],
                advertencia=ADVERTENCIA_SIN_EVIDENCIA,
            )
        )
    )

    response = client.post("/api/consulta", json={"pregunta": "¿Cuál es el horario de la cafetería?"})

    assert response.status_code == 200
    assert response.json() == {
        "respuesta": RESPUESTA_SIN_EVIDENCIA,
        "fuentes": [],
        "advertencia": ADVERTENCIA_SIN_EVIDENCIA,
    }
    assert servicio.preguntas == ["¿Cuál es el horario de la cafetería?"]


@pytest.mark.parametrize(
    ("error", "codigo", "clave"),
    [
        (CorpusNoIndexadoError(), 503, "corpus_no_indexado"),
        (ServicioNoDisponibleError(), 503, "servicio_no_disponible"),
    ],
    ids=["corpus-no-indexado", "servicio-no-disponible"],
)
def test_errores_de_dominio_503(
    error: Exception,
    codigo: int,
    clave: str,
    client: TestClient,
) -> None:
    _instalar(ServicioFalso(error=error))

    response = client.post("/api/consulta", json={"pregunta": "servicio social"})

    assert response.status_code == codigo
    body = response.json()
    assert set(body) == {"error", "mensaje"}
    assert body["error"] == clave
    assert body["mensaje"]


def test_consulta_tiempo_agotado(client: TestClient) -> None:
    _instalar(ServicioFalso(error=TiempoAgotadoError()))

    response = client.post("/api/consulta", json={"pregunta": "servicio social"})

    assert response.status_code == 504
    body = response.json()
    assert body["error"] == "tiempo_agotado"
    assert set(body) == {"error", "mensaje"}


def test_consulta_generacion_invalida() -> None:
    _instalar(ServicioFalso(error=GeneracionInvalidaError()))
    cliente = TestClient(app, raise_server_exceptions=False)

    response = cliente.post("/api/consulta", json={"pregunta": "servicio social"})

    assert response.status_code == 500
    assert response.json()["error"] == "generacion_invalida"


def test_consulta_error_interno() -> None:
    _instalar(ServicioFalso(error=RuntimeError("fallo inesperado")))
    cliente = TestClient(app, raise_server_exceptions=False)

    response = cliente.post("/api/consulta", json={"pregunta": "servicio social"})

    assert response.status_code == 500
    assert response.json() == {
        "error": "error_interno",
        "mensaje": "Error interno del servidor.",
    }


def test_consulta_get_rechazado(client: TestClient) -> None:
    response = client.get("/api/consulta")

    assert response.status_code == 405


# ---------------------------------------------------------------------------
# Textos exactos del contrato de abstención (CA-12, CA-28)
# ---------------------------------------------------------------------------


def test_advertencia_texto_exacto() -> None:
    assert ADVERTENCIA_SIN_EVIDENCIA == (
        "No se encontró información suficiente en los documentos de demostración "
        "para responder con certeza. Consulta los canales oficiales de tu institución."
    )


def test_advertencia_sin_departamentos_no_documentados() -> None:
    assert "departamento" not in ADVERTENCIA_SIN_EVIDENCIA.lower()


def test_respuesta_sin_evidencia_texto_exacto() -> None:
    assert RESPUESTA_SIN_EVIDENCIA == (
        "No se encontró información suficiente en los documentos de demostración."
    )
