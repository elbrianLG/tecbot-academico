"""Pruebas de la configuración de ejemplo (``backend/.env.example``)."""

from pathlib import Path

import pytest

from app.config import Settings

RUTA_ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"

# Variables que podrían venir del entorno de ejecución y contaminar la lectura
# del archivo de ejemplo (las variables de entorno tienen prioridad).
VARIABLES_A_LIMPIAR = (
    "APP_NAME",
    "DEBUG",
    "CORS_ORIGINS",
    "CORPUS_DIR",
    "CHROMA_DIR",
    "OLLAMA_BASE_URL",
    "OLLAMA_EMBED_MODEL",
    "OLLAMA_CHAT_MODEL",
    "CONSULTA_TIMEOUT_S",
)


def _settings_de_ejemplo(monkeypatch: pytest.MonkeyPatch) -> Settings:
    for variable in VARIABLES_A_LIMPIAR:
        monkeypatch.delenv(variable, raising=False)
    return Settings(_env_file=RUTA_ENV_EXAMPLE)


def test_env_example_es_parseable(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings_de_ejemplo(monkeypatch)

    assert settings.debug is False


def test_env_example_cors_es_lista_json(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings_de_ejemplo(monkeypatch)

    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_env_example_no_tiene_debug_true() -> None:
    lineas_activas = [
        linea.strip()
        for linea in RUTA_ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
        if not linea.strip().startswith("#")
    ]

    assert "DEBUG=true" not in lineas_activas
