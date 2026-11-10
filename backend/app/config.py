"""Configuración central: único punto donde se leen variables de entorno."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import TIEMPO_MAXIMO_CONSULTA_S

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TecBot API"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    corpus_dir: Path = RAIZ_REPOSITORIO / "documentos-demo"
    chroma_dir: Path = Path("data/chroma")

    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_chat_model: str = "llama3.2"
    consulta_timeout_s: float = TIEMPO_MAXIMO_CONSULTA_S


@lru_cache
def get_settings() -> Settings:
    return Settings()
