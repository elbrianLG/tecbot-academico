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
.venv\Scripts\python -m uvicorn app.main:app --reload     # http://localhost:8000
.venv\Scripts\python -m pytest                            # pruebas
```

El comando `python -m app.rag indexar` requiere que exista `documentos-demo/`
y que Ollama esté activo.

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

## Control de versiones

El proyecto utiliza Git y GitHub para registrar
los cambios y mantener un historial de desarrollo.

La rama principal es `main`.
Las mejoras se trabajan en ramas independientes.
