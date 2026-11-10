"""Modelos de petición y respuesta para POST /api/consulta."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import MAX_PREGUNTA, TOP_K


class ConsultaRequest(BaseModel):
    """Pregunta en lenguaje natural.

    La pregunta se normaliza (strip) antes de validar la longitud, por lo que
    el límite de ``MAX_PREGUNTA`` caracteres se aplica al texto ya normalizado.
    Se rechazan campos adicionales (``extra="forbid"``).
    """

    model_config = ConfigDict(extra="forbid")

    pregunta: str = Field(
        min_length=1,
        max_length=MAX_PREGUNTA,
        description=(
            f"Pregunta en lenguaje natural (1-{MAX_PREGUNTA} caracteres, "
            "tras eliminar espacios extremos)."
        ),
    )

    @field_validator("pregunta", mode="before")
    @classmethod
    def _normalizar(cls, valor: object) -> object:
        """Elimina espacios al inicio y al final antes de las restricciones.

        Las entradas que no son ``str`` pasan intactas para que Pydantic las
        rechace con 422 (y no con un ``AttributeError`` -> 500).
        """
        return valor.strip() if isinstance(valor, str) else valor


class FuenteDocumental(BaseModel):
    """Fragmento documental que respalda una respuesta."""

    documento: str = Field(
        min_length=1,
        description="Nombre del archivo del corpus de demostración.",
    )
    fragmento: str = Field(
        min_length=1,
        description="Texto del documento citado como respaldo.",
    )


class ConsultaResponse(BaseModel):
    """Respuesta a una consulta académica.

    ``fuentes`` contiene como máximo ``TOP_K`` fragmentos validados contra el
    corpus. ``advertencia`` es obligatoria en el contrato: vale ``None`` cuando
    la respuesta está fundamentada y un texto de derivación cuando no hay
    evidencia suficiente.
    """

    respuesta: str = Field(min_length=1)
    fuentes: list[FuenteDocumental] = Field(max_length=TOP_K)
    advertencia: str | None
