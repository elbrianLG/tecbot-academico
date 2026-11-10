# TecBot Académico

Asistente académico local compuesto por dos apps independientes:

- `backend/` — API en Python 3 + FastAPI.
- `frontend/` — SPA en React + TypeScript + Vite.

Los componentes de IA (Ollama) y la base de datos vectorial (ChromaDB) se integrarán posteriormente.

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload   # http://localhost:8000
.venv\Scripts\python -m pytest                            # pruebas
```

## Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 — el proxy de /api apunta a :8000
```

## Variables de entorno

Copia `backend/.env.example` a `backend/.env` y ajusta los valores. Nunca subas `.env` al repositorio.

## Control de versiones

El proyecto utiliza Git y GitHub para registrar
los cambios y mantener un historial de desarrollo.

La rama principal es `main`.
Las mejoras se trabajan en ramas independientes.
