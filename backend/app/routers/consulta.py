"""Ruta POST /api/consulta: recibe una pregunta y delega en el servicio RAG."""

from fastapi import APIRouter, Depends

from app.rag import ServicioConsulta, get_servicio_consulta
from app.schemas.consulta import ConsultaRequest, ConsultaResponse
from app.schemas.error import ErrorOperacion

router = APIRouter(tags=["consulta"])


@router.post(
    "/consulta",
    response_model=ConsultaResponse,
    summary="Responde una pregunta académica con fuentes del corpus",
    responses={
        422: {"description": "Pregunta inválida (vacía, demasiado larga o con campos extra)."},
        500: {
            "model": ErrorOperacion,
            "description": "Error interno o salida inválida del modelo.",
        },
        503: {
            "model": ErrorOperacion,
            "description": "Corpus no indexado o servicio de IA no disponible.",
        },
        504: {
            "model": ErrorOperacion,
            "description": "La consulta excedió el tiempo máximo.",
        },
    },
)
def crear_consulta(
    request: ConsultaRequest,
    servicio: ServicioConsulta = Depends(get_servicio_consulta),
) -> ConsultaResponse:
    return servicio.consultar(request.pregunta)
