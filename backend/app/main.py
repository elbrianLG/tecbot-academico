"""Punto de entrada del backend. Arrancar con: uvicorn app.main:app --reload"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.rag import (
    CorpusNoIndexadoError,
    GeneracionInvalidaError,
    ServicioNoDisponibleError,
    TiempoAgotadoError,
)
from app.routers import consulta, health

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(consulta.router, prefix="/api")


def _respuesta_error(status_code: int, error: str, mensaje: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "mensaje": mensaje},
    )


@app.exception_handler(CorpusNoIndexadoError)
async def _manejar_corpus_no_indexado(
    request: Request, exc: CorpusNoIndexadoError
) -> JSONResponse:
    return _respuesta_error(503, "corpus_no_indexado", str(exc))


@app.exception_handler(ServicioNoDisponibleError)
async def _manejar_servicio_no_disponible(
    request: Request, exc: ServicioNoDisponibleError
) -> JSONResponse:
    return _respuesta_error(503, "servicio_no_disponible", str(exc))


@app.exception_handler(TiempoAgotadoError)
async def _manejar_tiempo_agotado(
    request: Request, exc: TiempoAgotadoError
) -> JSONResponse:
    return _respuesta_error(504, "tiempo_agotado", str(exc))


@app.exception_handler(GeneracionInvalidaError)
async def _manejar_generacion_invalida(
    request: Request, exc: GeneracionInvalidaError
) -> JSONResponse:
    return _respuesta_error(500, "generacion_invalida", str(exc))


@app.exception_handler(Exception)
async def _manejar_error_interno(request: Request, exc: Exception) -> JSONResponse:
    return _respuesta_error(500, "error_interno", "Error interno del servidor.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
