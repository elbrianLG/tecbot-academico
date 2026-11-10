"""Rutas de salud. ``/api/salud`` es la ruta oficial; ``/api/health`` se
mantiene como alias por compatibilidad con el frontend existente."""

from fastapi import APIRouter

from app.schemas.salud import SaludResponse

router = APIRouter(tags=["salud"])


@router.get("/salud", response_model=SaludResponse, summary="Estado de la API")
@router.get("/health", response_model=SaludResponse, summary="Alias de /salud")
def salud() -> SaludResponse:
    return SaludResponse(status="ok")
