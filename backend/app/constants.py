"""Constantes compartidas por el dominio de consulta académica."""

MAX_PREGUNTA = 1000
TOP_K = 3
TIEMPO_MAXIMO_CONSULTA_S = 12.0
MAX_REINTENTOS_GENERACION = 1

RESPUESTA_SIN_EVIDENCIA = (
    "No se encontró información suficiente en los documentos de demostración."
)

ADVERTENCIA_SIN_EVIDENCIA = (
    "No se encontró información suficiente en los documentos de demostración "
    "para responder con certeza. Consulta los canales oficiales de tu institución."
)
