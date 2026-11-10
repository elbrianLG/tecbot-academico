"""Recuperación documental y generación de respuestas (RAG).

Las dependencias pesadas (``chromadb`` y ``ollama``) se importan de forma
perezosa dentro de los métodos para que la API pueda arrancar y las pruebas
unitarias correr sin ellas instaladas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.constants import (
    ADVERTENCIA_SIN_EVIDENCIA,
    RESPUESTA_SIN_EVIDENCIA,
    TOP_K,
)
from app.schemas.consulta import ConsultaResponse, FuenteDocumental

COLECCION = "documentos_demo"
NOMBRE_MANIFIESTO = "manifiesto.json"
TAMANO_FRAGMENTO = 1000
SOLAPE_FRAGMENTO = 100

PROMPT_SISTEMA = (
    "Eres un asistente académico de demostración. Responde únicamente con la "
    "información contenida en los fragmentos proporcionados. Si los fragmentos "
    "no alcanzan para responder, marca sin_evidencia como true. Devuelve "
    "exclusivamente un objeto JSON con las claves: sin_evidencia (booleano), "
    "respuesta (texto breve en español) y citas (lista de identificadores de "
    "fragmento utilizados). No inventes fechas, montos, enlaces ni normativa."
)


# ---------------------------------------------------------------------------
# Excepciones de dominio
# ---------------------------------------------------------------------------


class ErrorConsulta(Exception):
    """Base de los errores de dominio de la consulta académica."""


class CorpusNoIndexadoError(ErrorConsulta):
    """El corpus no existe o todavía no se indexó."""

    def __init__(
        self,
        mensaje: str = (
            "El corpus de demostración no está disponible o no ha sido indexado."
        ),
    ) -> None:
        super().__init__(mensaje)


class ServicioNoDisponibleError(ErrorConsulta):
    """Ollama o ChromaDB no están disponibles."""

    def __init__(
        self,
        mensaje: str = "El servicio de consulta no está disponible en este momento.",
    ) -> None:
        super().__init__(mensaje)


class TiempoAgotadoError(ErrorConsulta):
    """La consulta excedió el tiempo máximo configurado."""

    def __init__(
        self,
        mensaje: str = "La consulta excedió el tiempo máximo de espera.",
    ) -> None:
        super().__init__(mensaje)


class GeneracionInvalidaError(ErrorConsulta):
    """El modelo devolvió una salida que no cumple el contrato."""

    def __init__(
        self,
        mensaje: str = "El modelo generó una respuesta con un formato inválido.",
    ) -> None:
        super().__init__(mensaje)


# ---------------------------------------------------------------------------
# Utilidades de texto y corpus
# ---------------------------------------------------------------------------


def normalizar_texto(texto: str) -> str:
    """Normaliza a NFC, colapsa espacios y recorta extremos (sensible a mayúsculas)."""

    return " ".join(unicodedata.normalize("NFC", texto).split())


_PATRON_DATOS_SENSIBLES = re.compile(
    r"https?://\S+"
    r"|www\.\S+"
    r"|[\w.+-]+@[\w-]+\.[\w.]+"
    r"|\d+(?:[.,]\d+)*%?"
)


def extraer_datos_sensibles(texto: str) -> list[str]:
    """Extrae números, montos, fechas, URLs y correos de un texto."""

    return [
        coincidencia.group(0)
        for coincidencia in _PATRON_DATOS_SENSIBLES.finditer(texto)
    ]


def respuesta_respaldada(
    respuesta: str,
    fuentes: list[FuenteDocumental],
) -> bool:
    """Comprueba que todo dato sensible de la respuesta esté en las fuentes.

    Evita que el modelo invente fechas, montos, porcentajes, enlaces o correos
    que no aparezcan en los fragmentos validados.
    """

    contexto = normalizar_texto(" ".join(fuente.fragmento for fuente in fuentes))
    return all(dato in contexto for dato in extraer_datos_sensibles(respuesta))


@dataclass(frozen=True)
class FragmentoRecuperado:
    """Fragmento devuelto por la recuperación documental."""

    id: str
    documento: str
    fragmento: str
    distancia: float | None = None


def listar_archivos(corpus_dir: Path) -> list[Path]:
    """Devuelve los ``.md`` del corpus ordenados por nombre (lista vacía si no hay)."""

    if not corpus_dir.is_dir():
        return []
    return sorted(p for p in corpus_dir.glob("*.md") if p.is_file())


def cargar_documentos(corpus_dir: Path) -> dict[str, str]:
    """Lee el corpus como ``{nombre_archivo: contenido}``.

    Lanza ``CorpusNoIndexadoError`` si el directorio no existe o no tiene ``.md``.
    """

    archivos = listar_archivos(corpus_dir)
    if not archivos:
        raise CorpusNoIndexadoError()
    return {archivo.name: archivo.read_text(encoding="utf-8") for archivo in archivos}


def calcular_manifiesto(corpus_dir: Path) -> dict[str, str]:
    """Calcula ``{nombre_archivo: sha256}`` del corpus actual."""

    return {
        archivo.name: hashlib.sha256(archivo.read_bytes()).hexdigest()
        for archivo in listar_archivos(corpus_dir)
    }


def chunkear(
    texto: str,
    tamano: int = TAMANO_FRAGMENTO,
    solape: int = SOLAPE_FRAGMENTO,
) -> list[str]:
    """Divide un texto en fragmentos de tamaño fijo con solape."""

    if tamano <= 0:
        raise ValueError("El tamaño de fragmento debe ser positivo.")
    if solape < 0 or solape >= tamano:
        raise ValueError("El solape debe ser no negativo y menor que el tamaño.")

    limpio = texto.strip()
    if not limpio:
        return []

    paso = tamano - solape
    fragmentos: list[str] = []
    for inicio in range(0, len(limpio), paso):
        fragmento = limpio[inicio : inicio + tamano].strip()
        if fragmento:
            fragmentos.append(fragmento)
        if inicio + tamano >= len(limpio):
            break
    return fragmentos


def validar_fuentes(
    citas: list[str],
    recuperadas: list[FragmentoRecuperado],
    documentos: dict[str, str],
) -> list[FuenteDocumental]:
    """Filtra las citas del modelo contra los fragmentos realmente recuperados.

    Descarta identificadores desconocidos, documentos fuera del manifiesto y
    fragmentos que no sean subcadena normalizada del documento. Deduplica por
    ``(documento, fragmento)``, conserva el orden de ``recuperadas`` y corta a
    ``TOP_K`` resultados.
    """

    citadas = set(citas)
    documentos_normalizados = {
        nombre: normalizar_texto(contenido) for nombre, contenido in documentos.items()
    }

    resultado: list[FuenteDocumental] = []
    vistos: set[tuple[str, str]] = set()

    for fragmento in recuperadas:
        if fragmento.id not in citadas:
            continue
        if fragmento.documento not in documentos_normalizados:
            continue

        texto_normalizado = normalizar_texto(fragmento.fragmento)
        if not texto_normalizado:
            continue
        if texto_normalizado not in documentos_normalizados[fragmento.documento]:
            continue

        clave = (fragmento.documento, texto_normalizado)
        if clave in vistos:
            continue
        vistos.add(clave)

        resultado.append(
            FuenteDocumental(
                documento=fragmento.documento,
                fragmento=fragmento.fragmento,
            )
        )
        if len(resultado) >= TOP_K:
            break

    return resultado


def _respuesta_sin_evidencia() -> ConsultaResponse:
    return ConsultaResponse(
        respuesta=RESPUESTA_SIN_EVIDENCIA,
        fuentes=[],
        advertencia=ADVERTENCIA_SIN_EVIDENCIA,
    )


# ---------------------------------------------------------------------------
# Servicio de consulta
# ---------------------------------------------------------------------------


class ServicioConsulta:
    """Orquesta indexación, recuperación y generación con Ollama."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    # -- dependencias perezosas -------------------------------------------------

    @staticmethod
    def _importar_chromadb() -> Any:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise ServicioNoDisponibleError(
                "La dependencia 'chromadb' no está instalada."
            ) from exc
        return chromadb

    @staticmethod
    def _importar_ollama() -> Any:
        try:
            import ollama
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise ServicioNoDisponibleError(
                "La dependencia 'ollama' no está instalada."
            ) from exc
        return ollama

    def _cliente_ollama(self) -> Any:
        ollama = self._importar_ollama()
        return ollama.Client(
            host=self.settings.ollama_base_url,
            timeout=self.settings.consulta_timeout_s,
        )

    # -- manifiesto -------------------------------------------------------------

    @property
    def ruta_manifiesto(self) -> Path:
        return self.settings.chroma_dir / NOMBRE_MANIFIESTO

    def manifiesto_guardado(self) -> dict[str, str] | None:
        """Devuelve el manifiesto persistido o ``None`` si no existe o es inválido."""

        try:
            datos = json.loads(self.ruta_manifiesto.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        documentos = datos.get("documentos") if isinstance(datos, dict) else None
        if not isinstance(documentos, dict):
            return None
        return {str(k): str(v) for k, v in documentos.items()}

    def _guardar_manifiesto(self, manifiesto: dict[str, str]) -> None:
        self.settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.ruta_manifiesto.write_text(
            json.dumps({"version": 1, "documentos": manifiesto}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # -- estado -----------------------------------------------------------------

    def esta_indexado(self) -> bool:
        """``True`` solo si hay corpus, ``chromadb`` y una colección con datos."""

        if not listar_archivos(self.settings.corpus_dir):
            return False
        if not self.settings.chroma_dir.exists():
            return False
        try:
            chromadb = self._importar_chromadb()
        except ServicioNoDisponibleError:
            return False
        try:
            cliente = chromadb.PersistentClient(path=str(self.settings.chroma_dir))
            coleccion = cliente.get_collection(COLECCION)
            return coleccion.count() > 0
        except Exception:
            return False

    # -- Ollama -----------------------------------------------------------------

    def verificar_ollama(self) -> None:
        """Comprueba que Ollama responde y tiene el modelo de embeddings."""

        cliente = self._cliente_ollama()
        try:
            cliente.show(self.settings.ollama_embed_model)
        except Exception as exc:
            raise ServicioNoDisponibleError(
                "Ollama no responde en "
                f"{self.settings.ollama_base_url} o falta el modelo de embeddings "
                f"'{self.settings.ollama_embed_model}'."
            ) from exc

    def _embeber(self, cliente: Any, textos: list[str]) -> list[list[float]]:
        try:
            respuesta = cliente.embed(
                model=self.settings.ollama_embed_model,
                input=textos,
            )
            embeddings = respuesta["embeddings"]
        except Exception as exc:
            raise ServicioNoDisponibleError(
                "No fue posible generar los embeddings del corpus."
            ) from exc
        if len(embeddings) != len(textos):
            raise ServicioNoDisponibleError(
                "Ollama devolvió una cantidad inesperada de embeddings."
            )
        return embeddings

    # -- indexación -------------------------------------------------------------

    def indexar(self, reindexar: bool = False) -> int:
        """Indexa el corpus y devuelve la cantidad de fragmentos procesados.

        Devuelve ``0`` si el manifiesto no cambió y ``reindexar`` es ``False``.
        """

        documentos = cargar_documentos(self.settings.corpus_dir)
        manifiesto = calcular_manifiesto(self.settings.corpus_dir)
        if not reindexar and self.manifiesto_guardado() == manifiesto:
            return 0

        chromadb = self._importar_chromadb()
        cliente_ollama = self._cliente_ollama()
        self.verificar_ollama()

        ids: list[str] = []
        textos: list[str] = []
        metadatos: list[dict[str, str]] = []
        for nombre, contenido in documentos.items():
            for indice, fragmento in enumerate(chunkear(contenido)):
                ids.append(f"{nombre}::{indice}")
                textos.append(fragmento)
                metadatos.append({"documento": nombre})

        if not textos:
            raise CorpusNoIndexadoError("El corpus no contiene texto indexable.")

        embeddings = self._embeber(cliente_ollama, textos)

        self.settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        cliente = chromadb.PersistentClient(path=str(self.settings.chroma_dir))
        try:
            cliente.delete_collection(COLECCION)
        except Exception:
            pass
        coleccion = cliente.create_collection(COLECCION)

        lote = 100
        for inicio in range(0, len(ids), lote):
            fin = inicio + lote
            coleccion.add(
                ids=ids[inicio:fin],
                documents=textos[inicio:fin],
                metadatas=metadatos[inicio:fin],
                embeddings=embeddings[inicio:fin],
            )

        self._guardar_manifiesto(manifiesto)
        return len(textos)

    # -- recuperación -----------------------------------------------------------

    def recuperar(self, pregunta: str, top_k: int = TOP_K) -> list[FragmentoRecuperado]:
        """Recupera los fragmentos más cercanos a la pregunta."""

        if not self.esta_indexado():
            raise CorpusNoIndexadoError()

        chromadb = self._importar_chromadb()
        cliente_ollama = self._cliente_ollama()

        try:
            respuesta = cliente_ollama.embed(
                model=self.settings.ollama_embed_model,
                input=[pregunta],
            )
            embedding = respuesta["embeddings"][0]

            cliente = chromadb.PersistentClient(path=str(self.settings.chroma_dir))
            coleccion = cliente.get_collection(COLECCION)
            n_resultados = max(1, min(top_k, coleccion.count()))
            resultado = coleccion.query(
                query_embeddings=[embedding],
                n_results=n_resultados,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise ServicioNoDisponibleError(
                "No fue posible recuperar fragmentos del corpus."
            ) from exc

        ids = (resultado.get("ids") or [[]])[0]
        documentos = (resultado.get("documents") or [[]])[0]
        metadatos = (resultado.get("metadatas") or [[]])[0]
        distancias = (resultado.get("distances") or [[]])[0]

        fragmentos: list[FragmentoRecuperado] = []
        for posicion, identificador in enumerate(ids):
            metadato = metadatos[posicion] if posicion < len(metadatos) else None
            metadato = metadato or {}
            distancia = distancias[posicion] if posicion < len(distancias) else None
            fragmentos.append(
                FragmentoRecuperado(
                    id=str(identificador),
                    documento=str(metadato.get("documento", "")),
                    fragmento=(
                        documentos[posicion] if posicion < len(documentos) else ""
                    ),
                    distancia=float(distancia) if distancia is not None else None,
                )
            )
        return fragmentos

    # -- generación -------------------------------------------------------------

    def _generar(
        self,
        pregunta: str,
        recuperadas: list[FragmentoRecuperado],
    ) -> dict[str, Any]:
        cliente = self._cliente_ollama()
        contexto = "\n\n".join(
            f"[{fragmento.id}] Documento: {fragmento.documento}\n{fragmento.fragmento}"
            for fragmento in recuperadas
        )
        mensajes = [
            {"role": "system", "content": PROMPT_SISTEMA},
            {
                "role": "user",
                "content": f"Fragmentos:\n{contexto}\n\nPregunta: {pregunta}",
            },
        ]

        try:
            resultado = cliente.chat(
                model=self.settings.ollama_chat_model,
                messages=mensajes,
                format="json",
                options={"temperature": 0},
            )
        except Exception as exc:
            if "timeout" in str(exc).lower() or "timed out" in str(exc).lower():
                raise TiempoAgotadoError() from exc
            raise ServicioNoDisponibleError(
                "Ollama no pudo generar la respuesta."
            ) from exc

        try:
            contenido = resultado["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise GeneracionInvalidaError() from exc

        try:
            datos = json.loads(contenido)
        except (json.JSONDecodeError, TypeError) as exc:
            raise GeneracionInvalidaError() from exc
        if not isinstance(datos, dict):
            raise GeneracionInvalidaError()
        return datos

    def _verificar_tiempo(self, inicio: float) -> None:
        if time.monotonic() - inicio > self.settings.consulta_timeout_s:
            raise TiempoAgotadoError()

    def consultar(self, pregunta: str) -> ConsultaResponse:
        """Responde la pregunta con base en el corpus indexado."""

        if not self.esta_indexado():
            raise CorpusNoIndexadoError()

        inicio = time.monotonic()
        recuperadas = self.recuperar(pregunta, top_k=TOP_K)
        self._verificar_tiempo(inicio)

        if not recuperadas:
            return _respuesta_sin_evidencia()

        datos = self._generar(pregunta, recuperadas)
        self._verificar_tiempo(inicio)

        if datos.get("sin_evidencia") is True:
            return _respuesta_sin_evidencia()

        respuesta = datos.get("respuesta")
        citas = datos.get("citas")
        if not isinstance(respuesta, str) or not respuesta.strip():
            raise GeneracionInvalidaError()
        if not isinstance(citas, list):
            raise GeneracionInvalidaError()

        documentos = cargar_documentos(self.settings.corpus_dir)
        fuentes = validar_fuentes(
            [str(cita) for cita in citas],
            recuperadas,
            documentos,
        )
        if not fuentes:
            return _respuesta_sin_evidencia()

        respuesta_limpia = respuesta.strip()
        if not respuesta_respaldada(respuesta_limpia, fuentes):
            return _respuesta_sin_evidencia()

        return ConsultaResponse(
            respuesta=respuesta_limpia,
            fuentes=fuentes,
            advertencia=None,
        )


@lru_cache
def get_servicio_consulta() -> ServicioConsulta:
    """Instancia única del servicio, inyectable con ``Depends``."""

    return ServicioConsulta()


# ---------------------------------------------------------------------------
# CLI: python -m app.rag indexar [--reindex]
# ---------------------------------------------------------------------------


def _crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.rag",
        description="Herramientas del corpus de TecBot Académico.",
    )
    subcomandos = parser.add_subparsers(dest="comando", required=True)

    indexar = subcomandos.add_parser(
        "indexar",
        help="Indexa el corpus de demostración en ChromaDB.",
    )
    indexar.add_argument(
        "--reindex",
        action="store_true",
        help="Fuerza la reindexación aunque el corpus no haya cambiado.",
    )
    return parser


def _comando_indexar(settings: Settings, reindexar: bool) -> int:
    corpus_dir = settings.corpus_dir

    if ".." in corpus_dir.parts:
        print(
            "Error: la ruta del corpus no puede contener '..'.",
            file=sys.stderr,
        )
        return 2

    if not corpus_dir.is_dir():
        print(
            f"Error: no se encontró el corpus de demostración en {corpus_dir}.",
            file=sys.stderr,
        )
        return 2

    archivos = listar_archivos(corpus_dir)
    if not archivos:
        print(
            f"Error: el corpus en {corpus_dir} no contiene archivos .md.",
            file=sys.stderr,
        )
        return 2

    try:
        import chromadb  # noqa: F401
        import ollama  # noqa: F401
    except ImportError as exc:
        print(
            "Error: faltan dependencias de indexación "
            f"({exc.name or exc}). Instálalas con: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 3

    servicio = ServicioConsulta(settings)
    try:
        servicio.verificar_ollama()
    except ServicioNoDisponibleError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3

    manifiesto = calcular_manifiesto(corpus_dir)
    if not reindexar and servicio.manifiesto_guardado() == manifiesto:
        print(
            "El corpus no cambió desde la última indexación; no se hizo nada. "
            "Usa --reindex para forzar."
        )
        return 0

    try:
        total = servicio.indexar(reindexar=True)
    except (CorpusNoIndexadoError, ServicioNoDisponibleError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3

    print(
        f"Indexación completada: {total} fragmentos de {len(archivos)} documentos "
        f"en {settings.chroma_dir}."
    )
    return 0


def main(argv: list[str] | None = None, settings: Settings | None = None) -> int:
    """Punto de entrada del CLI. Devuelve el código de salida."""

    parser = _crear_parser()
    argumentos = parser.parse_args(argv)
    configuracion = settings or get_settings()

    if argumentos.comando == "indexar":
        return _comando_indexar(configuracion, reindexar=argumentos.reindex)

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
