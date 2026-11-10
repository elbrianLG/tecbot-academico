"""Modelo de error uniforme de la API."""

from pydantic import BaseModel


class ErrorOperacion(BaseModel):
    """Cuerpo de error de la API: código estable y mensaje legible."""

    error: str
    mensaje: str
