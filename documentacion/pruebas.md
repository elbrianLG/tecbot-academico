# Pruebas — TecBot Académico

> **Material didáctico.** Los documentos, preguntas y resultados descritos aquí
> pertenecen a un proyecto de demostración del curso *Creación de software con
> Agentes de IA*. No son normativa ni evidencia de un sistema institucional real.

## 1. Entorno de ejecución

- Windows, PowerShell.
- Backend: Python 3.11 en `backend/.venv`.
- Frontend: Node.js con Vitest + Testing Library.
- No hay `documentos-demo/` en el repositorio.
- `chromadb` y `ollama` no están instalados en el entorno actual.

Los comandos se ejecutan desde la carpeta indicada. En Windows se invoca el
Python del venv directamente para evitar bloqueos de activación.

El incremento **v1.1.1** incluye cambios de backend (P0/P1) y documentación; el
frontend no cambia. Los resultados de backend y frontend que aparecen abajo se
volvieron a ejecutar para verificar el estado del repositorio en este incremento.

## 2. Comandos y resultados reales

### 2.1 Suite unitaria del backend (por defecto)

```powershell
cd backend
.venv\Scripts\python -m pytest -q
```

Salida real:

```text
........................................................................ [ 81%]
................                                                         [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  D:\Curso_ChatBotIA\TecBot\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
88 passed, 6 deselected, 1 warning in 1.27s
```

Interpretación: **88 pruebas unitarias/de API aprobadas**; las **6 pruebas de
integración quedan deseleccionadas** por `addopts = -m 'not integracion'` en
`backend/pyproject.toml`. La advertencia es de Starlette/httpx y no es un fallo
del proyecto.

### 2.2 Pruebas de integración (hoy omitidas)

```powershell
cd backend
.venv\Scripts\python -m pytest -q -m integracion -rs
```

Salida real:

```text
ssssss                                                                   [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  D:\Curso_ChatBotIA\TecBot\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
SKIPPED [1] tests\test_integracion.py:58: could not import 'chromadb': No module named 'chromadb'
SKIPPED [1] tests\test_integracion.py:68: could not import 'chromadb': No module named 'chromadb'
SKIPPED [1] tests\test_integracion.py:75: could not import 'chromadb': No module named 'chromadb'
SKIPPED [1] tests\test_integracion.py:106: could not import 'chromadb': No module named 'chromadb'
SKIPPED [1] tests\test_integracion.py:133: could not import 'chromadb': No module named 'chromadb'
SKIPPED [1] tests\test_integracion.py:149: could not import 'chromadb': No module named 'chromadb'
6 skipped, 88 deselected, 1 warning in 0.17s
```

**Las 6 pruebas de integración están omitidas, no aprobadas.** La causa
inmediata es que falta `chromadb`; aun instalándolo, también se requieren
`ollama`, el servidor activo y `documentos-demo/`.

### 2.3 Frontend (sin cambios en v1.1.1)

```powershell
cd frontend
npm test
```

Salida real:

```text
> tecbot-frontend@0.1.0 test
> vitest run

 RUN  v5.1.0 D:/Curso_ChatBotIA/TecBot/frontend

 Test Files  2 passed (2)
      Tests  8 passed (8)
   Start at  16:07:16
   Duration  10.09s (environment 50%, tests 29%, setup 11%, import 8%, transform 1%)
```

Compilación de producción:

```powershell
cd frontend
npm run build
```

Salida real (resumen):

```text
> tecbot-frontend@0.1.0 build
> tsc && vite build

vite v7.3.8 building client environment for production...
✓ 32 modules transformed.
dist/index.html                 0.63 kB │ gzip:  0.37 kB
dist/assets/index-DEx2kdJ6.css 10.97 kB │ gzip:  3.03 kB
dist/assets/index-Dvf3vx8g.js 232.97 kB │ gzip: 73.16 kB
✓ built in 3.22s
```

## 3. Inventario de pruebas del backend

La suite por defecto recoge **88** pruebas en **6** archivos; las 6 de integración
se deseleccionan.

| Archivo | Pruebas | Qué cubre |
|---|---:|---|
| `tests/test_consulta.py` | 21 | Contrato de `POST /api/consulta`, claves exactas, `advertencia`, entradas inválidas (vacía, espacios, faltante, tipo incorrecto, 1001, campo extra), límite exacto de 1000, `strip` previo, abstención, errores `503/504/500`, método `GET` rechazado y textos exactos de abstención. |
| `tests/test_health.py` | 5 | `GET /api/salud`, alias `/api/health`, inexistencia de `/salud`, salud `200` sin corpus indexado y alias permanente sin deprecación. |
| `tests/test_rag.py` | 51 | Normalización, validación de fuentes, guardia de datos sensibles, flujo con dobles, `top_k=3` sin umbral, manifiesto/hash, reintento único, deadline global, consumo de presupuesto, clasificación del timeout de embeddings como tiempo agotado (`504`), una sola evaluación de `esta_indexado()` por consulta y error de Chroma traducido a `ServicioNoDisponibleError` (`503`). |
| `tests/test_cli.py` | 6 | Código `2` sin corpus, sin `.md` y con `..`; código `3` sin dependencias; `CORPUS_DIR` de `.env.example` sin `..`; ruta válida que no falla por el guard. |
| `tests/test_api_version.py` | 2 | `/api/v1/consulta` y `/api/v1/salud` no existen (`404`). |
| `tests/test_config.py` | 3 | `.env.example` parseable, `DEBUG=false` y `CORS_ORIGINS` como arreglo JSON. |
| `tests/test_integracion.py` | 6 (omitidas) | Indexación real idempotente, manifiesto real, consulta cubierta, consulta no cubierta, latencia real y `503` sin índice. |

Total de la suite por defecto: **21 + 5 + 51 + 6 + 2 + 3 = 88** pruebas. Las
**6 pruebas de `tests/test_integracion.py` quedan fuera de ese total** porque se
omiten y no forman parte de las 88.

Detalle de cobertura relevante:

- **Contrato HTTP:** las pruebas de `test_consulta.py` usan un servicio falso
  inyectado con `dependency_overrides`. Verifican la capa HTTP, no ChromaDB ni
  Ollama.
- **RAG:** `test_rag.py` usa dobles, `monkeypatch`, un reloj monotónico falso y
  archivos temporales. Verifica lógica y presupuesto de forma determinista.
- **CLI:** `test_cli.py` no indexa un corpus real; comprueba códigos de salida y
  guards con rutas temporales o con la ausencia real de dependencias.
- **Configuración:** `test_config.py` lee `backend/.env.example`, no un `.env`
  real.

## 4. Pruebas de integración: por qué se omiten y cómo habilitarlas

Requisitos para ejecutarlas:

1. Crear `documentos-demo/` en la raíz con documentos `.md` acordados con el
   responsable del corpus. **No se deben inventar documentos ni preguntas.**
2. Instalar `chromadb` y `ollama` en el venv:
   `pip install -r requirements.txt`.
3. Tener Ollama activo y los modelos descargados:
   `ollama pull nomic-embed-text` y `ollama pull llama3.2`.
4. Definir en `tests/test_integracion.py` las preguntas/documentos de prueba
   (`PREGUNTA_CUBIERTA`, `DOCUMENTO_ESPERADO`, `FRAGMENTO_ESPERADO`,
   `PREGUNTA_NO_CUBIERTA`) con el responsable del corpus. Hoy son `None` y esos
   casos se omiten explícitamente.
5. Ejecutar `python -m pytest -q -m integracion -rs`.

La suite por defecto **no** ejecuta integración. El marcador está declarado en
`backend/pyproject.toml` y `addopts` aplica `-m 'not integracion'`.

## 5. Qué no está verificado

- **CA-07, CA-08, CA-11, CA-23, CA-26 y CA-29 reales** (identificadores del plan
  de pruebas del incremento): requieren corpus real, ChromaDB y Ollama.
- **Latencia real** de una consulta completa: no medida; solo se verificó el
  presupuesto de 12 s con reloj falso.
- **Indexación real**: no ejecutada; no existe `documentos-demo/` ni están
  instaladas las dependencias pesadas.
- **Idempotencia real** de la indexación: solo cubierta por la prueba de
  integración, hoy omitida.
- **Calidad de recuperación/generación** con documentos reales: no evaluada.
- **Uniformidad del cuerpo `422`** con `{error, mensaje}`: el `422` actual usa
  el formato estándar de FastAPI (`detail`).

## 6. Declaración sobre dobles y fakes

**Las pruebas con dobles, fakes, `monkeypatch` o relojes falsos NO son pruebas
de integración.** Verifican la lógica y los contratos de forma determinista,
pero no demuestran que ChromaDB, Ollama, el corpus real y la API funcionen
juntos. Presentar esas pruebas como integración sería incorrecto.

Una prueba de integración solo cuenta como aprobada cuando se ejecuta sin
omitirse y con el entorno real disponible. En este repositorio, las 6 pruebas de
`test_integracion.py` se omiten y por lo tanto **no están aprobadas**.

## 7. Criterio para actualizar este documento

Al habilitar la integración, reemplazar los resultados de la sección 2.2 por la
salida real y actualizar la sección 5. No copiar resultados de otro entorno ni
declarar aprobadas pruebas que se omitieron.
