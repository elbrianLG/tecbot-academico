# AGENTS.md — TecBot Académico

## Propósito

Asistente de información académica para estudiantes del ITS Santiago Papasquiaro.
Responde preguntas sobre servicio social, residencias, titulación y acreditación
usando únicamente los documentos de `documentos-demo/`.

## Alcance

Incluye: consultas en lenguaje natural, recuperación de fragmentos documentales,
respuestas con fuentes y derivación a los canales oficiales cuando no hay evidencia.

No incluye: autenticación de usuarios, trámites oficiales ni firmas, datos
personales, normativa institucional real.

## Estructura

Todo el código Python vive en `backend/`; el frontend es una SPA independiente.
No hay comandos ni manifiestos de nivel raíz.

Existente:

- `backend/app/main.py` — entrada de FastAPI: crea la app, CORS, registra routers.
- `backend/app/routers/` — capa HTTP (`health.py`, `consulta.py`), sin lógica de negocio.
- `backend/app/schemas/` — modelos Pydantic de petición/respuesta.
- `backend/app/config.py` — `Settings`: único punto que lee `.env`.
- `backend/app/rag.py` — indexación y consulta documental (ChromaDB + Ollama).
- `backend/tests/` — pytest con `TestClient`; no requieren servicios externos.
- `backend/requirements.txt` — dependencias de la API, incluidos `chromadb` y `ollama`.
- `frontend/` — React + TypeScript + Vite (npm); proxy de `/api` → http://localhost:8000.
  Incluye componentes (`AvisoMaterialDidactico`, `ConsultaPanel`), tipos del
  contrato en `src/types/consulta.ts` y pruebas con Vitest + Testing Library.

Pendiente de crear (aún no existe):

- `documentos-demo/` — corpus ficticio de demostración (raíz del repo).
- `documentacion/` y `prompts/` — raíz del repo.

## Comandos

Desde `backend/` — en Windows, invocar `.venv\Scripts\python` directamente
(la activación del venv puede estar bloqueada por política de ejecución):

```
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload   # http://localhost:8000
.venv\Scripts\python -m pytest                            # suite completa
.venv\Scripts\python -m pytest tests/test_consulta.py -q  # un solo archivo
```

El venv ya existe en `backend/.venv` (Python 3.11). Frontend: `cd frontend`,
`npm install`, `npm run dev` (http://localhost:5173), `npm test` (Vitest) y
`npm run build`.

Las pruebas que ejerciten el modelo de IA local requieren su servidor activo;
un fallo allí suele ser del entorno, no del código.

## Estado actual de la API

- `POST /api/consulta` recibe `{"pregunta": "..."}` (1–1000 caracteres tras
  normalizar espacios extremos) y responde con `respuesta`, `fuentes` y
  `advertencia`.
- `fuentes` es una lista de objetos `{documento, fragmento}`. `advertencia` es
  `null` cuando la respuesta está fundamentada.
- Sin corpus indexado, `POST /api/consulta` responde `503`. Cuando no hay
  evidencia suficiente, responde `200` con `fuentes` vacío y una `advertencia`
  que recomienda consultar los canales oficiales de la institución.
- Rutas existentes: `GET /api/salud` (estado del servicio) y su alias
  `GET /api/health`.

## Reglas

1. No inventar requisitos, fechas, montos ni enlaces.
2. Toda respuesta debe citar al menos un documento de `documentos-demo/`.
3. Si la recuperación no encuentra evidencia suficiente, responder que no se
   cuenta con información y recomendar consultar los canales oficiales de la
   institución.
4. No modificar `documentos-demo/` para "hacer que una respuesta funcione".
5. No agregar dependencias sin justificar el motivo y actualizar
   `backend/requirements.txt`.
6. No incluir credenciales, tokens ni datos personales en el repositorio.
   Los secretos van en `backend/.env` (gitignored); mantener `.env.example`
   sincronizado.
7. Los documentos son material didáctico; nunca presentarlos como normativa oficial.

## Convenciones

- Python con type hints en funciones públicas; archivos en snake_case.
- Rutas de API en español y en plural cuando representan recursos
  (las acciones, como `/consulta`, van en singular).
- Respuestas JSON con las claves `respuesta`, `fuentes` y `advertencia`.
- Commits en Conventional Commits con descripción en español
  (p. ej. `feat: agrega endpoint inicial de consulta académica`).

## Definición de terminado

Una tarea está terminada cuando:

- El código compila y las pruebas pasan.
- Existe al menos una prueba para el caso feliz y una para el caso sin evidencia.
- Se actualizó la documentación afectada.
- El cambio fue revisado con `git diff`.



# Equipo de agentes — TecBot Académico

## Coordinador (agente principal)
- Lee requerimientos y arquitectura.
- Descompone tareas.
- Delega a subagentes.
- Revisa e integra.
- Ejecuta o solicita pruebas.

## Arquitecto
- Analiza requerimientos.
- Define estructura y contratos de API.
- Documenta decisiones.
- Revisa coherencia backend/frontend.

## Diseñador web
- Define sistema de diseño.
- Diseña componentes y pantallas.
- Garantiza accesibilidad y responsive.
- Trabaja con design.md.

## Desarrollador
- Implementa endpoints y componentes.
- Integra frontend/backend.
- Mantiene buenas prácticas.

## Tester
- Diseña y ejecuta pruebas.
- Reporta defectos.
- Verifica correcciones.