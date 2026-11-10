"""Ruta POST /api/consulta: recibe una pregunta en lenguaje natural."""

from fastapi import APIRouter

from app.schemas.consulta import ConsultaRequest, ConsultaResponse

router = APIRouter(tags=["consulta"])

RESPUESTA_PLACEHOLDER = (
    "Funcionalidad en construcción: la generación de respuestas con IA "
    "se integrará en un próximo incremento."
)


@router.post("/consulta", response_model=ConsultaResponse)
def crear_consulta(request: ConsultaRequest) -> ConsultaResponse:
    return ConsultaResponse(
        pregunta=request.pregunta,
        respuesta=RESPUESTA_PLACEHOLDER,
    )
