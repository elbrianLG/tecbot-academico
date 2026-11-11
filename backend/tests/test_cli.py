"""Pruebas del CLI de indexación (sin corpus real ni dependencias pesadas)."""

from pathlib import Path

import pytest

from app.config import Settings
from app.rag import main

RUTA_ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"


def _valor_env_example(clave: str) -> str | None:
    """Devuelve el valor de ``clave`` en ``.env.example`` (activo o comentado)."""

    for linea in RUTA_ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        limpia = linea.strip()
        if limpia.startswith("#"):
            limpia = limpia[1:].strip()
        if limpia.startswith(f"{clave}="):
            valor = limpia.split("=", 1)[1].strip()
            return valor.strip('"').strip("'")
    return None


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


def test_env_example_corpus_dir_no_contiene_puntos_suspensivos() -> None:
    valor = _valor_env_example("CORPUS_DIR")
    if valor is None:
        pytest.skip("CORPUS_DIR no está definido ni comentado en .env.example")

    assert ".." not in Path(valor).parts


def test_indexar_con_ruta_sin_puntos_suspensivos_no_falla_por_guard(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    try:
        import chromadb  # noqa: F401
        import ollama  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip(
            "dependencias pesadas instaladas; la prueba cubre el entorno sin ellas."
        )

    corpus = _corpus_temporal(tmp_path)
    settings = Settings(corpus_dir=corpus, chroma_dir=tmp_path / "chroma")

    codigo = main(["indexar"], settings=settings)

    assert codigo == 3
    assert "no puede contener '..'" not in capsys.readouterr().err
