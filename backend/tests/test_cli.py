"""Pruebas del CLI de indexación (sin corpus real ni dependencias pesadas)."""

from pathlib import Path

import pytest

from app.config import Settings
from app.rag import main


def _corpus_temporal(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "documento.md").write_text(
        "# Documento de prueba\n\nContenido ficticio para la prueba.",
        encoding="utf-8",
    )
    return corpus


def test_indexar_sin_corpus_devuelve_2(tmp_path: Path) -> None:
    settings = Settings(
        corpus_dir=tmp_path / "no-existe",
        chroma_dir=tmp_path / "chroma",
    )

    assert main(["indexar"], settings=settings) == 2
    assert not (tmp_path / "chroma").exists()


def test_indexar_corpus_sin_markdown_devuelve_2(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "notas.txt").write_text("sin markdown", encoding="utf-8")
    settings = Settings(corpus_dir=corpus, chroma_dir=tmp_path / "chroma")

    assert main(["indexar"], settings=settings) == 2


def test_indexar_rechaza_rutas_con_puntos_suspensivos(tmp_path: Path) -> None:
    settings = Settings(
        corpus_dir=Path("..") / "corpus",
        chroma_dir=tmp_path / "chroma",
    )

    assert main(["indexar"], settings=settings) == 2


def test_indexar_sin_dependencias_pesadas_devuelve_3(tmp_path: Path) -> None:
    try:
        import chromadb  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("chromadb está instalado; la prueba cubre el entorno sin la dependencia.")

    corpus = _corpus_temporal(tmp_path)
    settings = Settings(corpus_dir=corpus, chroma_dir=tmp_path / "chroma")

    assert main(["indexar"], settings=settings) == 3
    assert not (tmp_path / "chroma").exists()
