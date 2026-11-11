"""Pruebas de integración con el corpus real, ChromaDB y Ollama.

Se excluyen por defecto (``addopts = -m 'not integracion'``). Requieren:

- ``documentos-demo/`` en la raíz del repositorio (nunca se crea ni modifica).
- ``chromadb`` y ``ollama`` instalados y el servidor de Ollama activo.
- Una pregunta/documento de prueba acordados con el responsable del corpus.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from app.config import RAIZ_REPOSITORIO, Settings
from app.constants import ADVERTENCIA_SIN_EVIDENCIA, RESPUESTA_SIN_EVIDENCIA
from app.main import app
from app.rag import (
    CorpusNoIndexadoError,
    ServicioConsulta,
    calcular_manifiesto,
    get_servicio_consulta,
)

pytestmark = pytest.mark.integracion

CORPUS_DIR = RAIZ_REPOSITORIO / "documentos-demo"


@pytest.fixture(autouse=True)
def _requiere_entorno_de_integracion() -> None:
    """Omite cada prueba si faltan dependencias pesadas o el corpus real."""

    pytest.importorskip("chromadb")
    pytest.importorskip("ollama")
    if not CORPUS_DIR.is_dir():
        pytest.skip("documentos-demo/ no existe")


# PENDIENTE: definir con el responsable del corpus. No se inventan preguntas ni
# documentos institucionales.
PREGUNTA_CUBIERTA: str | None = None
DOCUMENTO_ESPERADO: str | None = None
FRAGMENTO_ESPERADO: str | None = None
PREGUNTA_NO_CUBIERTA: str | None = None


def _servicio_con_chroma_temporal(tmp_path: Path) -> ServicioConsulta:
    return ServicioConsulta(
        Settings(corpus_dir=CORPUS_DIR, chroma_dir=tmp_path / "chroma")
    )


def test_indexacion_real_es_idempotente(tmp_path: Path) -> None:
    servicio = _servicio_con_chroma_temporal(tmp_path)

    primera = servicio.indexar()
    segunda = servicio.indexar()

    assert primera > 0
    assert segunda == 0


def test_manifiesto_coincide_con_el_corpus_tras_indexar(tmp_path: Path) -> None:
    servicio = _servicio_con_chroma_temporal(tmp_path)
    servicio.indexar()

    assert servicio.manifiesto_guardado() == calcular_manifiesto(CORPUS_DIR)


def test_consulta_cubierta_devuelve_fuente_real(tmp_path: Path) -> None:
    if (
        PREGUNTA_CUBIERTA is None
        or DOCUMENTO_ESPERADO is None
        or FRAGMENTO_ESPERADO is None
    ):
        pytest.skip(
            "Pregunta y documento de prueba pendientes de definir con el "
            "responsable del corpus."
        )

    servicio = _servicio_con_chroma_temporal(tmp_path)
    servicio.indexar()

    resultado = servicio.consultar(PREGUNTA_CUBIERTA)

    assert resultado.advertencia is None
    assert resultado.fuentes
    assert any(
        fuente.documento == DOCUMENTO_ESPERADO
        and FRAGMENTO_ESPERADO in fuente.fragmento
        for fuente in resultado.fuentes
    )
    assert DOCUMENTO_ESPERADO in (servicio.manifiesto_guardado() or {})

    documentos = servicio.documentos_indexados()
    for fuente in resultado.fuentes:
        assert fuente.documento in documentos
        assert fuente.fragmento.strip() in documentos[fuente.documento]


def test_consulta_no_cubierta_abstiene(tmp_path: Path) -> None:
    if PREGUNTA_NO_CUBIERTA is None:
        pytest.skip(
            "Pregunta no cubierta pendiente de definir con el responsable del corpus."
        )

    servicio = _servicio_con_chroma_temporal(tmp_path)
    servicio.indexar()

    app.dependency_overrides[get_servicio_consulta] = lambda: servicio
    try:
        cliente = TestClient(app, raise_server_exceptions=False)
        response = cliente.post(
            "/api/consulta",
            json={"pregunta": PREGUNTA_NO_CUBIERTA},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "respuesta": RESPUESTA_SIN_EVIDENCIA,
        "fuentes": [],
        "advertencia": ADVERTENCIA_SIN_EVIDENCIA,
    }


def test_latencia_de_consulta_no_supera_doce_segundos(tmp_path: Path) -> None:
    if PREGUNTA_CUBIERTA is None:
        pytest.skip(
            "Pregunta cubierta pendiente de definir con el responsable del corpus."
        )

    servicio = _servicio_con_chroma_temporal(tmp_path)
    servicio.indexar()

    inicio = time.monotonic()
    servicio.consultar(PREGUNTA_CUBIERTA)
    transcurrido = time.monotonic() - inicio

    assert transcurrido <= 12.0


def test_corpus_sin_indice_devuelve_503(tmp_path: Path) -> None:
    servicio = ServicioConsulta(
        Settings(corpus_dir=CORPUS_DIR, chroma_dir=tmp_path / "sin-indice")
    )

    with pytest.raises(CorpusNoIndexadoError):
        servicio.consultar("consulta de integración")

    app.dependency_overrides[get_servicio_consulta] = lambda: servicio
    try:
        cliente = TestClient(app, raise_server_exceptions=False)
        response = cliente.post(
            "/api/consulta",
            json={"pregunta": "consulta de integración"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"] == "corpus_no_indexado"
