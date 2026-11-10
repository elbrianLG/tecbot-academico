"""Modelo de respuesta del endpoint de salud."""

from typing import Literal

from pydantic import BaseModel


class SaludResponse(BaseModel):
    """Estado de la API."""

    status: Literal["ok"]
