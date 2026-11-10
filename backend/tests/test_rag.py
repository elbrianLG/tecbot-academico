"""Pruebas unitarias de las utilidades RAG (sin chromadb ni Ollama)."""

from pathlib import Path

import pytest

from app.config import Settings
from app.constants import ADVERTENCIA_SIN_EVIDENCIA, RESPUESTA_SIN_EVIDENCIA
from app.rag import (
    FragmentoRecuperado,
    ServicioConsulta,
    extraer_datos_sensibles,
    normalizar_texto,
    respuesta_respaldada,
    validar_fuentes,
)
from app.schemas.consulta import FuenteDocumental

DOCUMENTOS = {
    "servicio-social.md": (
        "Para iniciar el servicio social se requiere haber cubierto el 70% de los "
        "créditos y entregar la solicitud en el departamento de vinculación."
    ),
    "titulacion.md": (
        "Las modalidades de titulación son tesis, proyecto integrador y promedio "
        "destacado."
    ),
}


def _fragmento(
    identificador: str,
    documento: str,
    fragmento: str,
) -> FragmentoRecuperado:
    return FragmentoRecuperado(id=identificador, documento=documento, fragmento=fragmento)


# ---------------------------------------------------------------------------
# normalizar_texto
# ---------------------------------------------------------------------------


def test_normalizar_texto_compone_nfc() -> None:
    assert normalizar_texto("cafe\u0301") == "café"


def test_normalizar_texto_colapsa_espacios() -> None:
    assert normalizar_texto("  hola \n\t mundo  ") == "hola mundo"


def test_normalizar_texto_conserva_mayusculas() -> None:
    assert normalizar_texto("Hola Mundo") == "Hola Mundo"


def test_normalizar_texto_vacio() -> None:
    assert normalizar_texto("   \n\t ") == ""


# ---------------------------------------------------------------------------
# validar_fuentes
# ---------------------------------------------------------------------------


def test_validar_fuentes_descarta_id_desconocido() -> None:
    recuperadas = [
        _fragmento("a", "servicio-social.md", "haber cubierto el 70% de los créditos"),
    ]

    assert validar_fuentes(["desconocido"], recuperadas, DOCUMENTOS) == []


def test_validar_fuentes_descarta_documento_fuera_del_manifiesto() -> None:
    recuperadas = [
        _fragmento("a", "otro.md", "haber cubierto el 70% de los créditos"),
    ]

    assert validar_fuentes(["a"], recuperadas, DOCUMENTOS) == []


def test_validar_fuentes_descarta_fragmento_parafraseado() -> None:
    recuperadas = [
        _fragmento(
            "a",
            "servicio-social.md",
            "es necesario haber cubierto 70% de créditos",
        ),
    ]

    assert validar_fuentes(["a"], recuperadas, DOCUMENTOS) == []


def test_validar_fuentes_deduplica_por_documento_y_fragmento() -> None:
    recuperadas = [
        _fragmento("a", "servicio-social.md", "haber cubierto el 70% de los créditos"),
        _fragmento("b", "servicio-social.md", "haber cubierto el 70% de los créditos"),
    ]

    fuentes = validar_fuentes(["a", "b"], recuperadas, DOCUMENTOS)

    assert len(fuentes) == 1
    assert fuentes[0].documento == "servicio-social.md"


def test_validar_fuentes_corta_a_tres() -> None:
    recuperadas = [
        _fragmento("a", "servicio-social.md", "haber cubierto el 70% de los créditos"),
        _fragmento("b", "servicio-social.md", "entregar la solicitud en el departamento"),
        _fragmento("c", "titulacion.md", "Las modalidades de titulación son tesis"),
        _fragmento("d", "titulacion.md", "proyecto integrador y promedio destacado"),
    ]

    fuentes = validar_fuentes(["a", "b", "c", "d"], recuperadas, DOCUMENTOS)

    assert len(fuentes) == 3


def test_validar_fuentes_todas_invalidas() -> None:
    recuperadas = [
        _fragmento("a", "servicio-social.md", "texto que no está en el documento"),
        _fragmento("b", "desconocido.md", "haber cubierto el 70% de los créditos"),
    ]

    assert validar_fuentes(["a", "b"], recuperadas, DOCUMENTOS) == []


def test_validar_fuentes_respeta_orden_de_recuperadas() -> None:
    recuperadas = [
        _fragmento("b", "titulacion.md", "Las modalidades de titulación son tesis"),
        _fragmento("a", "servicio-social.md", "haber cubierto el 70% de los créditos"),
    ]

    fuentes = validar_fuentes(["a", "b"], recuperadas, DOCUMENTOS)

    assert [fuente.documento for fuente in fuentes] == [
        "titulacion.md",
        "servicio-social.md",
    ]


def test_validar_fuentes_normaliza_espacios_del_fragmento() -> None:
    recuperadas = [
        _fragmento(
            "a",
            "servicio-social.md",
            "haber   cubierto el 70% de los créditos",
        ),
    ]

    fuentes = validar_fuentes(["a"], recuperadas, DOCUMENTOS)

    assert len(fuentes) == 1
    assert fuentes[0].fragmento == "haber   cubierto el 70% de los créditos"


def test_validar_fuentes_solo_incluye_las_citadas() -> None:
    recuperadas = [
        _fragmento("a", "servicio-social.md", "haber cubierto el 70% de los créditos"),
        _fragmento("b", "servicio-social.md", "entregar la solicitud en el departamento"),
        _fragmento("c", "titulacion.md", "Las modalidades de titulación son tesis"),
    ]

    fuentes = validar_fuentes(["b"], recuperadas, DOCUMENTOS)

    assert [fuente.fragmento for fuente in fuentes] == [
        "entregar la solicitud en el departamento"
    ]


# ---------------------------------------------------------------------------
# Guardia de datos sensibles (CA-17)
# ---------------------------------------------------------------------------


def test_extraer_datos_sensibles_detecta_numeros_urls_y_correos() -> None:
    texto = "Cuesta 500 pesos, cubre 70%, vigente en 2026, https://ejemplo.mx y a@b.mx"

    assert extraer_datos_sensibles(texto) == [
        "500",
        "70%",
        "2026",
        "https://ejemplo.mx",
        "a@b.mx",
    ]


def test_respuesta_respaldada_acepta_dato_presente_en_la_fuente() -> None:
    fuentes = [
        FuenteDocumental(
            documento="servicio-social.md",
            fragmento="se requiere haber cubierto el 70% de los créditos",
        )
    ]

    assert respuesta_respaldada("Necesitas el 70% de los créditos.", fuentes)


@pytest.mark.parametrize(
    "respuesta",
    [
        "El costo es de 500 pesos.",
        "El trámite vence en 2026.",
        "Consulta https://inventado.mx para más información.",
        "Escribe a correo@inventado.mx.",
    ],
    ids=["monto", "fecha", "url", "correo"],
)
def test_respuesta_respaldada_rechaza_dato_ausente(respuesta: str) -> None:
    fuentes = [
        FuenteDocumental(
            documento="servicio-social.md",
            fragmento="se requiere haber cubierto el 70% de los créditos",
        )
    ]

    assert not respuesta_respaldada(respuesta, fuentes)


# ---------------------------------------------------------------------------
# Flujo de consulta con dobles (sin ChromaDB ni Ollama)
# ---------------------------------------------------------------------------


def _servicio_con_dobles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    recuperada: FragmentoRecuperado,
) -> ServicioConsulta:
    servicio = ServicioConsulta(
        Settings(corpus_dir=tmp_path, chroma_dir=tmp_path / "chroma")
    )
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    monkeypatch.setattr(
        servicio, "recuperar", lambda pregunta, top_k=3: [recuperada]
    )
    monkeypatch.setattr("app.rag.cargar_documentos", lambda _: DOCUMENTOS)
    return servicio


def test_consultar_devuelve_fuentes_validadas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recuperada = _fragmento(
        "a", "servicio-social.md", "haber cubierto el 70% de los créditos"
    )
    servicio = _servicio_con_dobles(monkeypatch, tmp_path, recuperada)
    monkeypatch.setattr(
        servicio,
        "_generar",
        lambda pregunta, recuperadas: {
            "sin_evidencia": False,
            "respuesta": "Se requiere haber cubierto el 70% de los créditos.",
            "citas": ["a"],
        },
    )

    resultado = servicio.consultar("¿Qué necesito para el servicio social?")

    assert resultado.advertencia is None
    assert len(resultado.fuentes) == 1
    assert resultado.fuentes[0].documento == "servicio-social.md"


def test_consultar_abstiene_si_la_respuesta_inventa_datos(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recuperada = _fragmento(
        "a", "servicio-social.md", "haber cubierto el 70% de los créditos"
    )
    servicio = _servicio_con_dobles(monkeypatch, tmp_path, recuperada)
    monkeypatch.setattr(
        servicio,
        "_generar",
        lambda pregunta, recuperadas: {
            "sin_evidencia": False,
            "respuesta": "El costo es de 500 pesos y vence en 2026.",
            "citas": ["a"],
        },
    )

    resultado = servicio.consultar("¿Cuánto cuesta el trámite?")

    assert resultado.respuesta == RESPUESTA_SIN_EVIDENCIA
    assert resultado.fuentes == []
    assert resultado.advertencia == ADVERTENCIA_SIN_EVIDENCIA


def test_consultar_abstiene_si_todas_las_citas_son_invalidas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recuperada = _fragmento(
        "a", "servicio-social.md", "haber cubierto el 70% de los créditos"
    )
    servicio = _servicio_con_dobles(monkeypatch, tmp_path, recuperada)
    monkeypatch.setattr(
        servicio,
        "_generar",
        lambda pregunta, recuperadas: {
            "sin_evidencia": False,
            "respuesta": "Respuesta sin respaldo.",
            "citas": ["desconocida"],
        },
    )

    resultado = servicio.consultar("Pregunta")

    assert resultado.fuentes == []
    assert resultado.advertencia == ADVERTENCIA_SIN_EVIDENCIA


# ---------------------------------------------------------------------------
# Recuperación sin filtro por score (CA-10)
# ---------------------------------------------------------------------------


class _ColeccionFalsa:
    def count(self) -> int:
        return 5

    def query(self, **kwargs: object) -> dict[str, object]:
        assert kwargs["n_results"] == 3
        return {
            "ids": [["a", "b", "c"]],
            "documents": [["uno", "dos", "tres"]],
            "metadatas": [[{"documento": "d.md"} for _ in range(3)]],
            "distances": [[0.91, 0.97, 0.99]],
        }


class _ChromaFalso:
    def PersistentClient(self, path: str) -> object:
        class _Cliente:
            def get_collection(self, nombre: str) -> _ColeccionFalsa:
                return _ColeccionFalsa()

        return _Cliente()


class _OllamaFalso:
    def embed(self, model: str, input: list[str]) -> dict[str, object]:
        return {"embeddings": [[0.1, 0.2]]}


def test_recuperar_no_filtra_por_score(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    servicio = ServicioConsulta(
        Settings(corpus_dir=tmp_path, chroma_dir=tmp_path / "chroma")
    )
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    monkeypatch.setattr(servicio, "_importar_chromadb", lambda: _ChromaFalso())
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda: _OllamaFalso())

    fragmentos = servicio.recuperar("pregunta", top_k=3)

    assert len(fragmentos) == 3
    assert [fragmento.distancia for fragmento in fragmentos] == [0.91, 0.97, 0.99]
