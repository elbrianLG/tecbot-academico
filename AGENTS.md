# AGENTS.md

Guidance for OpenCode sessions working on TecBot.

This file was written while the repo was still empty; the conventions below are the agreed plan for the project. Follow them, and update this file as the codebase takes shape.

## Layout

Two independent apps in one repo, no shared code and no root-level manifest:

- `backend/` — Python 3 + FastAPI. AI features call Ollama (local models) and store/retrieve embeddings in ChromaDB (embedded local vector store — no external DB service to start).
- `frontend/` — React + TypeScript + Vite, managed with npm.

All install, run, and test commands belong inside `backend/` or `frontend/` — never assume a root-level build or test entry point.

## Backend

- Dependencies via Python venv + pip. Keep the venv inside `backend/` (e.g. `backend/.venv`). On Windows, invoke tools without activation if the policy blocks scripts: `backend\.venv\Scripts\python -m pytest`.
- Pin dependencies in `backend/requirements.txt`.
- Tests: `pytest`, run from `backend/`.
- Anything that calls AI models requires a local Ollama server to already be running; failing tests that hit LLM features usually mean Ollama isn't up, not a code bug.

## Frontend

- `npm install` inside `frontend/`; dev/build scripts are Vite-based in `frontend/package.json`.

## Secrets & config

- All API keys and credentials live in `.env` files (gitignored). Never hardcode secrets in code or commits.
- Commit a `.env.example` with placeholder keys only, and keep it in sync whenever a new variable is added.
