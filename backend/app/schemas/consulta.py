"""Modelos de petición y respuesta para POST /api/consulta."""

from pydantic import BaseModel, Field, field_validator


class ConsultaRequest(BaseModel):
    """Pregunta en lenguaje natural.

    La pregunta se normaliza (strip) antes de validar la longitud,
    por lo que el límite de 2000 caracteres se aplica al texto
    ya normalizado, y la respuesta hace echo de la versión normalizada.
    """

    pregunta: str = Field(
        min_length=1,
        max_length=2000,
        description="Pregunta en lenguaje natural (1-2000 caracteres, tras normalizar espacios extremos).",
    )

    @field_validator("pregunta", mode="before")
    @classmethod
    def _normalizar(cls, valor: object) -> object:
        """Elimina espacios al inicio y al final antes de las restricciones.

        Las entradas que no son str pasan intactas para que Pydantic
        las rechace con 422 (y no con un AttributeError -> 500).
        """
        return valor.strip() if isinstance(valor, str) else valor


class ConsultaResponse(BaseModel):
    """Respuesta a una consulta académica.

    `respuesta` es un placeholder en este incremento; la generación con IA
    (Ollama) se integrará posteriormente.

    `fuentes` es una estructura provisional: siempre una lista vacía en este
    incremento. Cuando se implemente la recuperación documental (RAG) su
    estructura podrá cambiar (p. ej. de list[str] a una lista estructurada
    con documento, página y score). No consumir aún desde el frontend.
    """

    pregunta: str = Field(description="Pregunta normalizada que originó la respuesta.")
    respuesta: str = Field(description="Respuesta generada (placeholder en este incremento).")
    fuentes: list[str] = Field(
        default_factory=list,
        description="Fuentes documentales (RAG). Vacío en este incremento; estructura provisional.",
    )
