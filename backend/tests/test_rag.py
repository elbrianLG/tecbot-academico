"""Pruebas unitarias de las utilidades RAG (sin chromadb ni Ollama)."""

import json
from pathlib import Path

import pytest

from app.config import Settings
from app.constants import (
    ADVERTENCIA_SIN_EVIDENCIA,
    MAX_REINTENTOS_GENERACION,
    RESPUESTA_SIN_EVIDENCIA,
)
from app.rag import (
    NOMBRE_MANIFIESTO,
    CorpusNoIndexadoError,
    FragmentoRecuperado,
    GeneracionInvalidaError,
    ServicioConsulta,
    ServicioNoDisponibleError,
    TiempoAgotadoError,
    calcular_manifiesto,
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
        servicio,
        "recuperar",
        lambda pregunta, top_k=3, deadline=None, indexado=None: [recuperada],
    )
    monkeypatch.setattr(servicio, "documentos_indexados", lambda: DOCUMENTOS)
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
        lambda pregunta, recuperadas, deadline=None: {
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
        lambda pregunta, recuperadas, deadline=None: {
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
        lambda pregunta, recuperadas, deadline=None: {
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
    monkeypatch.setattr(
        servicio, "_cliente_ollama", lambda timeout=None: _OllamaFalso()
    )

    fragmentos = servicio.recuperar("pregunta", top_k=3)

    assert len(fragmentos) == 3
    assert [fragmento.distancia for fragmento in fragmentos] == [0.91, 0.97, 0.99]


# ---------------------------------------------------------------------------
# Errores de tiempo en la recuperación (F-1)
# ---------------------------------------------------------------------------


class _OllamaQueFalla:
    """Cliente de embeddings que siempre lanza la excepción indicada."""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.llamadas = 0

    def embed(self, model: str, input: list[str]) -> dict[str, object]:
        self.llamadas += 1
        raise self.error


def test_recuperar_timeout_de_embeddings_es_tiempo_agotado(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    servicio = _servicio_rag(tmp_path)
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    monkeypatch.setattr(servicio, "_importar_chromadb", lambda: _ChromaFalso())
    cliente = _OllamaQueFalla(TimeoutError("timed out"))
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    with pytest.raises(TiempoAgotadoError):
        servicio.recuperar("pregunta")

    assert cliente.llamadas == 1


def test_recuperar_timeout_sin_mensaje_es_tiempo_agotado(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    servicio = _servicio_rag(tmp_path)
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    monkeypatch.setattr(servicio, "_importar_chromadb", lambda: _ChromaFalso())
    cliente = _OllamaQueFalla(TimeoutError())
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    with pytest.raises(TiempoAgotadoError):
        servicio.recuperar("pregunta")

    assert cliente.llamadas == 1


def test_recuperar_error_de_conexion_sigue_siendo_servicio_no_disponible(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    servicio = _servicio_rag(tmp_path)
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    monkeypatch.setattr(servicio, "_importar_chromadb", lambda: _ChromaFalso())
    cliente = _OllamaQueFalla(ConnectionError("connection refused"))
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    with pytest.raises(ServicioNoDisponibleError):
        servicio.recuperar("pregunta")

    assert cliente.llamadas == 1


def test_recuperar_con_indexado_explicito_no_recalcula(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    servicio = _servicio_rag(tmp_path)
    llamadas: list[bool] = []

    def esta_indexado() -> bool:
        llamadas.append(True)
        return True

    monkeypatch.setattr(servicio, "esta_indexado", esta_indexado)
    monkeypatch.setattr(servicio, "_importar_chromadb", lambda: _ChromaFalso())
    monkeypatch.setattr(
        servicio, "_cliente_ollama", lambda timeout=None: _OllamaFalso()
    )

    fragmentos = servicio.recuperar("pregunta", top_k=3, indexado=True)

    assert len(fragmentos) == 3
    assert llamadas == []


def test_recuperar_con_indexado_falso_no_consulta_dependencias(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    servicio = _servicio_rag(tmp_path)
    llamadas: list[bool] = []

    def esta_indexado() -> bool:
        llamadas.append(True)
        return True

    monkeypatch.setattr(servicio, "esta_indexado", esta_indexado)

    with pytest.raises(CorpusNoIndexadoError):
        servicio.recuperar("pregunta", indexado=False)

    assert llamadas == []


def test_recuperar_sin_indexado_explicito_lanza_corpus_no_indexado(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Sin ``indexado`` explícito, ``recuperar`` evalúa el estado una sola vez.

    Con el corpus no indexado debe abortar antes de importar Chroma o crear el
    cliente de Ollama; los dobles registran cualquier acceso para demostrarlo.
    """

    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    llamadas: list[bool] = []
    dependencias: list[str] = []

    def esta_indexado() -> bool:
        llamadas.append(True)
        return False

    def importar_chromadb() -> object:
        dependencias.append("chromadb")
        raise AssertionError("no debe importar chromadb")

    def cliente_ollama(timeout: float | None = None) -> object:
        dependencias.append("ollama")
        raise AssertionError("no debe crear el cliente de Ollama")

    monkeypatch.setattr(servicio, "esta_indexado", esta_indexado)
    monkeypatch.setattr(servicio, "_importar_chromadb", importar_chromadb)
    monkeypatch.setattr(servicio, "_cliente_ollama", cliente_ollama)

    with pytest.raises(CorpusNoIndexadoError):
        servicio.recuperar("pregunta")

    assert llamadas == [True]
    assert dependencias == []


class _ChromaQueFalla:
    """Doble de ``chromadb`` cuyo cliente persistente siempre falla."""

    def PersistentClient(self, path: str) -> object:
        raise RuntimeError("chroma caido")


def test_recuperar_error_de_chroma_es_servicio_no_disponible(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Un fallo de Chroma al abrir el índice se traduce en 503, no en 504.

    Se hace fallar ``PersistentClient`` (no ``get_collection``) para cubrir el
    punto donde ``recuperar`` abre el índice. El error no es de tiempo, así que
    debe mapearse a ``ServicioNoDisponibleError`` y no a ``TiempoAgotadoError``.
    """

    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    monkeypatch.setattr(servicio, "_importar_chromadb", lambda: _ChromaQueFalla())
    monkeypatch.setattr(
        servicio, "_cliente_ollama", lambda timeout=None: _OllamaFalso()
    )

    with pytest.raises(ServicioNoDisponibleError) as excinfo:
        servicio.recuperar("pregunta")

    assert not isinstance(excinfo.value, TiempoAgotadoError)



# ---------------------------------------------------------------------------
# Documentos indexados contra el manifiesto (CA-29)
# ---------------------------------------------------------------------------


def _crear_corpus(tmp_path: Path, documentos: dict[str, str]) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for nombre, contenido in documentos.items():
        (corpus / nombre).write_text(contenido, encoding="utf-8")
    return corpus


def _guardar_manifiesto_temporal(
    chroma_dir: Path,
    corpus: Path,
    documentos: dict[str, str] | None = None,
) -> None:
    chroma_dir.mkdir(parents=True, exist_ok=True)
    manifiesto = documentos if documentos is not None else calcular_manifiesto(corpus)
    (chroma_dir / NOMBRE_MANIFIESTO).write_text(
        json.dumps({"version": 1, "documentos": manifiesto}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_documentos_indexados_solo_incluye_hash_coincidente(tmp_path: Path) -> None:
    corpus = _crear_corpus(
        tmp_path,
        {"a.md": "Contenido A.", "b.md": "Contenido B."},
    )
    chroma = tmp_path / "chroma"
    manifiesto = calcular_manifiesto(corpus)
    manifiesto.pop("b.md")
    _guardar_manifiesto_temporal(chroma, corpus, manifiesto)

    servicio = ServicioConsulta(Settings(corpus_dir=corpus, chroma_dir=chroma))

    assert servicio.documentos_indexados() == {"a.md": "Contenido A."}


def test_documentos_indexados_excluye_documento_nuevo(tmp_path: Path) -> None:
    corpus = _crear_corpus(tmp_path, {"a.md": "Contenido A."})
    chroma = tmp_path / "chroma"
    _guardar_manifiesto_temporal(chroma, corpus)
    (corpus / "nuevo.md").write_text("Documento nuevo.", encoding="utf-8")

    servicio = ServicioConsulta(Settings(corpus_dir=corpus, chroma_dir=chroma))

    assert servicio.documentos_indexados() == {"a.md": "Contenido A."}


def test_documentos_indexados_excluye_documento_modificado(tmp_path: Path) -> None:
    corpus = _crear_corpus(tmp_path, {"a.md": "Contenido original."})
    chroma = tmp_path / "chroma"
    _guardar_manifiesto_temporal(chroma, corpus)
    (corpus / "a.md").write_text("Contenido modificado.", encoding="utf-8")

    servicio = ServicioConsulta(Settings(corpus_dir=corpus, chroma_dir=chroma))

    assert servicio.documentos_indexados() == {}


def test_documentos_indexados_sin_manifiesto_es_vacio(tmp_path: Path) -> None:
    corpus = _crear_corpus(tmp_path, {"a.md": "Contenido A."})
    servicio = ServicioConsulta(
        Settings(corpus_dir=corpus, chroma_dir=tmp_path / "chroma")
    )

    assert servicio.documentos_indexados() == {}


def test_consultar_no_cita_documento_fuera_del_manifiesto(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    corpus = _crear_corpus(
        tmp_path,
        {
            "servicio-social.md": DOCUMENTOS["servicio-social.md"],
            "otro.md": "Contenido del documento no indexado.",
        },
    )
    chroma = tmp_path / "chroma"
    manifiesto = calcular_manifiesto(corpus)
    manifiesto.pop("otro.md")
    _guardar_manifiesto_temporal(chroma, corpus, manifiesto)

    servicio = ServicioConsulta(Settings(corpus_dir=corpus, chroma_dir=chroma))
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    recuperada = _fragmento("a", "otro.md", "Contenido del documento no indexado.")
    monkeypatch.setattr(
        servicio,
        "recuperar",
        lambda pregunta, top_k=3, deadline=None, indexado=None: [recuperada],
    )
    monkeypatch.setattr(
        servicio,
        "_generar",
        lambda pregunta, recuperadas, deadline=None: {
            "sin_evidencia": False,
            "respuesta": "Contenido del documento no indexado.",
            "citas": ["a"],
        },
    )

    resultado = servicio.consultar("Pregunta")

    assert resultado.respuesta == RESPUESTA_SIN_EVIDENCIA
    assert resultado.fuentes == []
    assert resultado.advertencia == ADVERTENCIA_SIN_EVIDENCIA


def test_consultar_no_cita_documento_modificado(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    corpus = _crear_corpus(
        tmp_path,
        {"servicio-social.md": DOCUMENTOS["servicio-social.md"]},
    )
    chroma = tmp_path / "chroma"
    _guardar_manifiesto_temporal(chroma, corpus)
    (corpus / "servicio-social.md").write_text(
        "Texto distinto al que se indexó.",
        encoding="utf-8",
    )

    servicio = ServicioConsulta(Settings(corpus_dir=corpus, chroma_dir=chroma))
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    recuperada = _fragmento(
        "a", "servicio-social.md", "haber cubierto el 70% de los créditos"
    )
    monkeypatch.setattr(
        servicio,
        "recuperar",
        lambda pregunta, top_k=3, deadline=None, indexado=None: [recuperada],
    )
    monkeypatch.setattr(
        servicio,
        "_generar",
        lambda pregunta, recuperadas, deadline=None: {
            "sin_evidencia": False,
            "respuesta": "Se requiere haber cubierto el 70% de los créditos.",
            "citas": ["a"],
        },
    )

    resultado = servicio.consultar("Pregunta")

    assert resultado.respuesta == RESPUESTA_SIN_EVIDENCIA
    assert resultado.fuentes == []
    assert resultado.advertencia == ADVERTENCIA_SIN_EVIDENCIA


def test_esta_indexado_false_sin_manifiesto(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    corpus = _crear_corpus(tmp_path, {"a.md": "Contenido A."})
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    servicio = ServicioConsulta(Settings(corpus_dir=corpus, chroma_dir=chroma))
    monkeypatch.setattr(servicio, "_importar_chromadb", lambda: _ChromaFalso())

    assert servicio.esta_indexado() is False


# ---------------------------------------------------------------------------
# Reintento de generación (CA-25)
# ---------------------------------------------------------------------------


class _RelojFalso:
    """Reloj monotónico controlable para pruebas deterministas."""

    def __init__(self, inicio: float = 1000.0) -> None:
        self.ahora = inicio

    def monotonic(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


class _ClienteChatFalso:
    """Cliente de chat que devuelve salidas en orden (o lanza excepciones)."""

    def __init__(self, salidas: list[object]) -> None:
        self.salidas = list(salidas)
        self.llamadas = 0

    def chat(self, **kwargs: object) -> dict[str, object]:
        self.llamadas += 1
        salida = self.salidas.pop(0)
        if isinstance(salida, Exception):
            raise salida
        return {"message": {"content": salida}}


def _servicio_rag(tmp_path: Path) -> ServicioConsulta:
    return ServicioConsulta(
        Settings(corpus_dir=tmp_path, chroma_dir=tmp_path / "chroma")
    )


def test_generar_reintenta_tras_una_salida_invalida(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    cliente = _ClienteChatFalso(
        [
            "esto no es json",
            json.dumps(
                {
                    "sin_evidencia": False,
                    "respuesta": "Respuesta válida.",
                    "citas": ["a"],
                }
            ),
        ]
    )
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    datos = servicio._generar(
        "pregunta",
        [_fragmento("a", "d.md", "fragmento")],
        deadline=reloj.ahora + 12,
    )

    assert datos["respuesta"] == "Respuesta válida."
    assert cliente.llamadas == 1 + MAX_REINTENTOS_GENERACION


def test_generar_falla_tras_agotar_los_reintentos(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    cliente = _ClienteChatFalso(
        [
            "esto no es json",
            json.dumps({"respuesta": "", "citas": []}),
        ]
    )
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    with pytest.raises(GeneracionInvalidaError):
        servicio._generar(
            "pregunta",
            [_fragmento("a", "d.md", "fragmento")],
            deadline=reloj.ahora + 12,
        )

    assert cliente.llamadas == 1 + MAX_REINTENTOS_GENERACION


def test_generar_no_reintenta_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    cliente = _ClienteChatFalso([TimeoutError("timed out")])
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    with pytest.raises(TiempoAgotadoError):
        servicio._generar(
            "pregunta",
            [_fragmento("a", "d.md", "fragmento")],
            deadline=reloj.ahora + 12,
        )

    assert cliente.llamadas == 1


def test_generar_no_reintenta_error_de_conexion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    cliente = _ClienteChatFalso([ConnectionError("connection refused")])
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    with pytest.raises(ServicioNoDisponibleError):
        servicio._generar(
            "pregunta",
            [_fragmento("a", "d.md", "fragmento")],
            deadline=reloj.ahora + 12,
        )

    assert cliente.llamadas == 1


def test_consultar_sin_evidencia_no_reintenta(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    recuperada = _fragmento("a", "d.md", "fragmento")
    monkeypatch.setattr(
        servicio,
        "recuperar",
        lambda pregunta, top_k=3, deadline=None, indexado=None: [recuperada],
    )
    monkeypatch.setattr(servicio, "documentos_indexados", lambda: {"d.md": "fragmento"})
    cliente = _ClienteChatFalso(
        [
            json.dumps(
                {
                    "sin_evidencia": True,
                    "respuesta": "No hay evidencia suficiente.",
                    "citas": [],
                }
            )
        ]
    )
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    resultado = servicio.consultar("Pregunta")

    assert resultado.advertencia == ADVERTENCIA_SIN_EVIDENCIA
    assert cliente.llamadas == 1


def test_consultar_abstiene_con_salida_minima_sin_evidencia(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    monkeypatch.setattr(servicio, "esta_indexado", lambda: True)
    recuperada = _fragmento("a", "d.md", "fragmento")
    monkeypatch.setattr(
        servicio,
        "recuperar",
        lambda pregunta, top_k=3, deadline=None, indexado=None: [recuperada],
    )
    cliente = _ClienteChatFalso([json.dumps({"sin_evidencia": True})])
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    resultado = servicio.consultar("Pregunta")

    assert resultado.respuesta == RESPUESTA_SIN_EVIDENCIA
    assert resultado.fuentes == []
    assert resultado.advertencia == ADVERTENCIA_SIN_EVIDENCIA
    assert cliente.llamadas == 1


def test_generar_no_reintenta_si_el_presupuesto_se_agoto(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)

    class _ClienteAgotaPresupuesto:
        def __init__(self) -> None:
            self.llamadas = 0

        def chat(self, **kwargs: object) -> dict[str, object]:
            self.llamadas += 1
            reloj.avanzar(13)
            return {"message": {"content": "esto no es json"}}

    cliente = _ClienteAgotaPresupuesto()
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    with pytest.raises(TiempoAgotadoError):
        servicio._generar(
            "pregunta",
            [_fragmento("a", "d.md", "fragmento")],
            deadline=reloj.ahora + 12,
        )

    assert cliente.llamadas == 1


# ---------------------------------------------------------------------------
# Deadline global de 12 s (RNF-01)
# ---------------------------------------------------------------------------


def test_recuperar_usa_el_restante_como_timeout_de_embeddings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)

    def esta_indexado() -> bool:
        reloj.avanzar(10)
        return True

    monkeypatch.setattr(servicio, "esta_indexado", esta_indexado)
    monkeypatch.setattr(servicio, "_importar_chromadb", lambda: _ChromaFalso())
    timeouts: list[float | None] = []

    def construir_cliente(timeout: float | None = None) -> _OllamaFalso:
        timeouts.append(timeout)
        return _OllamaFalso()

    monkeypatch.setattr(servicio, "_cliente_ollama", construir_cliente)

    servicio.recuperar("pregunta", top_k=3)

    assert timeouts == pytest.approx([2.0])


def test_generar_usa_el_restante_como_timeout_de_chat(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    timeouts: list[float | None] = []
    cliente = _ClienteChatFalso(
        [
            json.dumps(
                {
                    "sin_evidencia": False,
                    "respuesta": "Respuesta.",
                    "citas": [],
                }
            )
        ]
    )

    def construir_cliente(timeout: float | None = None) -> _ClienteChatFalso:
        timeouts.append(timeout)
        return cliente

    monkeypatch.setattr(servicio, "_cliente_ollama", construir_cliente)
    deadline = reloj.ahora + 12
    reloj.avanzar(10)

    servicio._generar("pregunta", [], deadline=deadline)

    assert timeouts == pytest.approx([2.0])


def test_restante_agotado_no_llama_al_cliente(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    timeouts: list[float | None] = []
    monkeypatch.setattr(
        servicio,
        "_cliente_ollama",
        lambda timeout=None: timeouts.append(timeout),
    )
    deadline = reloj.ahora + 12
    reloj.avanzar(12)

    with pytest.raises(TiempoAgotadoError):
        servicio._generar("pregunta", [], deadline=deadline)

    assert timeouts == []


def test_reintento_no_concede_mas_de_doce_segundos(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    timeouts: list[float | None] = []

    class _ClienteConsumeTodo:
        def __init__(self) -> None:
            self.llamadas = 0

        def chat(self, **kwargs: object) -> dict[str, object]:
            self.llamadas += 1
            reloj.avanzar(12)
            return {"message": {"content": "esto no es json"}}

    cliente = _ClienteConsumeTodo()

    def construir_cliente(timeout: float | None = None) -> _ClienteConsumeTodo:
        timeouts.append(timeout)
        return cliente

    monkeypatch.setattr(servicio, "_cliente_ollama", construir_cliente)

    with pytest.raises(TiempoAgotadoError):
        servicio._generar("pregunta", [], deadline=reloj.ahora + 12)

    assert sum(t for t in timeouts if t is not None) <= 12.0
    assert cliente.llamadas == 1


def test_el_tiempo_de_esta_indexado_consume_presupuesto(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)

    def esta_indexado() -> bool:
        reloj.avanzar(13)
        return True

    monkeypatch.setattr(servicio, "esta_indexado", esta_indexado)
    monkeypatch.setattr(servicio, "recuperar", lambda *args, **kwargs: [])

    with pytest.raises(TiempoAgotadoError):
        servicio.consultar("pregunta")


# ---------------------------------------------------------------------------
# Una sola evaluación de esta_indexado por consulta (F-2)
# ---------------------------------------------------------------------------


def test_consultar_evalua_esta_indexado_una_sola_vez(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    llamadas: list[bool] = []

    def esta_indexado() -> bool:
        llamadas.append(True)
        return True

    monkeypatch.setattr(servicio, "esta_indexado", esta_indexado)
    recuperada = _fragmento(
        "a", "servicio-social.md", "haber cubierto el 70% de los créditos"
    )
    monkeypatch.setattr(
        servicio,
        "recuperar",
        lambda pregunta, top_k=3, deadline=None, indexado=None: [recuperada],
    )
    monkeypatch.setattr(servicio, "documentos_indexados", lambda: DOCUMENTOS)
    cliente = _ClienteChatFalso(
        [
            json.dumps(
                {
                    "sin_evidencia": False,
                    "respuesta": "Se requiere haber cubierto el 70% de los créditos.",
                    "citas": ["a"],
                }
            )
        ]
    )
    monkeypatch.setattr(servicio, "_cliente_ollama", lambda timeout=None: cliente)

    resultado = servicio.consultar("Pregunta")

    assert len(llamadas) == 1
    assert resultado.advertencia is None


def test_consultar_con_recuperar_real_evalua_esta_indexado_una_sola_vez(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """F-2 con la recuperación real: una sola evaluación de ``esta_indexado``.

    A diferencia de ``test_consultar_evalua_esta_indexado_una_sola_vez``, aquí
    NO se reemplaza ``recuperar`` por un doble, por lo que la prueba es sensible
    a la regresión que motivó F-2. Con el código anterior ``consultar`` evaluaba
    ``esta_indexado()`` y luego ``recuperar`` (al no recibir ``indexado``) lo
    volvía a evaluar: el contador habría valido 2 y esta prueba habría fallado.
    """

    reloj = _RelojFalso()
    monkeypatch.setattr("app.rag.time.monotonic", reloj.monotonic)
    servicio = _servicio_rag(tmp_path)
    llamadas: list[bool] = []

    def esta_indexado() -> bool:
        llamadas.append(True)
        return True

    monkeypatch.setattr(servicio, "esta_indexado", esta_indexado)
    monkeypatch.setattr(servicio, "_importar_chromadb", lambda: _ChromaFalso())
    monkeypatch.setattr(
        servicio, "_cliente_ollama", lambda timeout=None: _OllamaFalso()
    )
    # Aísla la generación: la consulta termina en abstención sin llamar al chat.
    monkeypatch.setattr(
        servicio, "_generar", lambda *args, **kwargs: {"sin_evidencia": True}
    )

    resultado = servicio.consultar("pregunta")

    assert len(llamadas) == 1
    assert resultado.advertencia == ADVERTENCIA_SIN_EVIDENCIA

