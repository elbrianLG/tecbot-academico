# TecBot Académico

Asistente académico local compuesto por dos apps independientes:

- `backend/` — API en Python 3 + FastAPI.
- `frontend/` — SPA en React + TypeScript + Vite.

La recuperación documental usa ChromaDB y la generación de respuestas, Ollama local.

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m app.rag indexar                   # requiere documentos-demo/ y Ollama
.venv\Scripts\python -m app.rag indexar --reindex         # fuerza la reindexación
.venv\Scripts\python -m uvicorn app.main:app --reload     # http://localhost:8000
.venv\Scripts\python -m pytest                            # pruebas unitarias (integración excluida)
.venv\Scripts\python -m pytest -m integracion -rs         # integración (ver más abajo)
```

El comando `python -m app.rag indexar` requiere que exista `documentos-demo/`
y que Ollama esté activo. Si el corpus no cambió desde la última indexación no
hace nada; `--reindex` fuerza el proceso aunque los hashes coincidan.

Modelos locales por defecto (definidos en `backend/app/config.py`):

```bash
ollama pull nomic-embed-text   # embeddings
ollama pull llama3.2           # generación de respuestas
```

Códigos de salida de `python -m app.rag indexar`:

| Código | Significado |
|---|---|
| `0` | Éxito: corpus indexado, o sin cambios desde la última indexación. |
| `2` | Error de corpus: no existe `documentos-demo/`, no contiene archivos `.md` o la ruta incluye `..`. |
| `3` | Faltan dependencias (`chromadb`/`ollama`) o Ollama no responde o no tiene el modelo de embeddings. |

Las pruebas de integración requieren `documentos-demo/` con documentos `.md`,
`chromadb` y `ollama` instalados, el servidor de Ollama activo y, para los casos
de consulta cubierta, preguntas acordadas con el responsable del corpus. La
suite por defecto **no** ejecuta integración: `backend/pyproject.toml` aplica
`-m 'not integracion'`.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/consulta` | Recibe `{"pregunta": "..."}` (1–1000 caracteres) y devuelve `respuesta`, `fuentes` y `advertencia`. |
| `GET` | `/api/salud` | Estado del servicio. |
| `GET` | `/api/health` | Alias de `/api/salud`. |

`POST /api/consulta` responde `503` si no hay corpus indexado. Cuando no hay
evidencia suficiente responde `200` con `fuentes` vacío y una `advertencia` que
recomienda consultar los canales oficiales de la institución.

## Frontend

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173 — el proxy de /api apunta a :8000
npm test        # pruebas con Vitest + Testing Library
npm run build   # compilación de producción
```

## Variables de entorno

Copia `backend/.env.example` a `backend/.env` y ajusta los valores. Nunca subas `.env` al repositorio.

- `DEBUG=false`: con `DEBUG=true`, Starlette usa su `debug_response` y omite el
  manejador de excepciones; eso rompe el contrato de error `{error, mensaje}` y
  puede exponer la traza al cliente.
- `CORS_ORIGINS` debe ser un arreglo JSON, no una lista separada por comas:
  `CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]`.
- `CORPUS_DIR` es opcional; por defecto apunta a `documentos-demo/` en la raíz
  del repositorio. Si se define, no puede contener `..`.

## Control de versiones

El proyecto utiliza Git y GitHub para registrar
los cambios y mantener un historial de desarrollo.

La rama principal es `main`.
Las mejoras se trabajan en ramas independientes.
