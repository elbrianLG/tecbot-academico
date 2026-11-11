# Arquitectura — TecBot Académico

> **Material didáctico.** Este documento describe un sistema de demostración del
> curso *Creación de software con Agentes de IA*. No es normativa oficial ni
> contiene requisitos, fechas, montos o enlaces institucionales reales.

## 1. Propósito y alcance

TecBot Académico responde preguntas en lenguaje natural sobre servicio social,
residencias, titulación, acreditación y trámites generales usando únicamente un
corpus ficticio de demostración. Toda respuesta fundamentada cita al menos un
documento del corpus; cuando no hay evidencia suficiente, el sistema se abstiene
y recomienda consultar los canales oficiales de la institución.

Incluye:

- Consulta académica con recuperación documental y generación local.
- Respuestas con `respuesta`, `fuentes` y `advertencia`.
- Indexación del corpus mediante un CLI.
- Aviso visible de material didáctico en el frontend.

No incluye autenticación, expedientes, trámites oficiales, firmas, pagos, datos
personales ni integración con sistemas institucionales.

El incremento **v1.1.1** corrige los defectos P0/P1 del backend (configuración
de ejemplo, reintento del generador, validación contra manifiesto y deadline
global) y actualiza la documentación. El frontend no cambia en este incremento.

## 2. Componentes

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| Frontend | React 19 + TypeScript + Vite | SPA de consulta; proxy de `/api` hacia `http://localhost:8000`. |
| API | FastAPI + Pydantic | Rutas HTTP, validación del contrato y traducción de errores de dominio. |
| RAG | `backend/app/rag.py` | Indexación, recuperación, generación, validación de fuentes y abstención. |
| ChromaDB | Persistencia local en `data/chroma` | Almacena fragmentos y embeddings del corpus. |
| Ollama | Servidor local | Embeddings (`nomic-embed-text`) y generación (`llama3.2`) por defecto. |

Los modelos y rutas por defecto se definen en `backend/app/config.py`. Las
dependencias pesadas (`chromadb` y `ollama`) se importan de forma perezosa para
que la API arranque y las pruebas unitarias corran sin ellas instaladas.

## 3. Contrato HTTP

### 3.1 `POST /api/consulta`

Petición:

```json
{"pregunta": "¿Qué necesito para el servicio social?"}
```

- Solo se acepta la clave `pregunta`; `extra="forbid"` rechaza campos extra.
- El texto se recorta con `strip` **antes** de validar la longitud.
- Longitud válida: 1–1000 caracteres tras el recorte.
- Una entrada vacía, solo espacios, de tipo incorrecto, mayor a 1000 o con
  campos extra responde `422`.

Respuesta `200` fundamentada:

```json
{
  "respuesta": "Texto breve en español.",
  "fuentes": [
    {"documento": "servicio-social.md", "fragmento": "Fragmento textual del documento."}
  ],
  "advertencia": null
}
```

- El cuerpo contiene exactamente las claves `respuesta`, `fuentes` y
  `advertencia`.
- `fuentes` es una lista de objetos `{documento, fragmento}` con un máximo de 3
  elementos (`TOP_K = 3`).
- `advertencia` es `null` cuando la respuesta está fundamentada y un texto de
  derivación cuando no hay evidencia suficiente.

Respuesta `200` sin evidencia:

```json
{
  "respuesta": "No se encontró información suficiente en los documentos de demostración.",
  "fuentes": [],
  "advertencia": "No se encontró información suficiente en los documentos de demostración para responder con certeza. Consulta los canales oficiales de tu institución."
}
```

Los textos exactos viven en `backend/app/constants.py`.

### 3.2 Rutas de salud

- `GET /api/salud` — ruta oficial; responde `{"status": "ok"}`.
- `GET /api/health` — alias permanente de `/api/salud`, sin deprecación.
- La API no expone `/api/v1`; las rutas sin prefijo `/api` no existen.

### 3.3 Modelo de errores

Los errores de dominio y los fallos internos usan el cuerpo
`{"error": "<código>", "mensaje": "<texto>"}`:

| Código | `error` | Causa |
|---|---|---|
| `500` | `generacion_invalida` | El generador agotó el reintento con salida inválida. |
| `500` | `error_interno` | Excepción no controlada; el mensaje es genérico. |
| `503` | `corpus_no_indexado` | No hay corpus, manifiesto o colección indexada. |
| `503` | `servicio_no_disponible` | Falta `chromadb`/`ollama` o el servicio no responde. |
| `504` | `tiempo_agotado` | Se agotó el presupuesto global de la consulta. |

**Observación verificada:** el `422` de validación de Pydantic/FastAPI conserva
el cuerpo estándar `{"detail": [...]}`; no se transforma a `{error, mensaje}`.
El contrato uniforme cubre `500`, `503` y `504`. Si se requiere uniformar el
`422`, es un cambio pendiente y fuera de este incremento documental.

## 4. Flujo RAG

1. **Validación** — `ConsultaRequest` recorta la pregunta y valida longitud y
   campos extra.
2. **Presupuesto** — `consultar()` fija un `deadline` absoluto con
   `time.monotonic() + 12 s`.
3. **`esta_indexado()`** — exige, en orden:
   - archivos `.md` en el corpus;
   - `manifiesto.json` válido en el directorio de ChromaDB;
   - directorio de ChromaDB existente;
   - `chromadb` importable;
   - colección `documentos_demo` con `count() > 0`.

   Un índice sin manifiesto se considera no indexado y produce `503`.
4. **Recuperación** — se genera el embedding de la pregunta con Ollama usando el
   tiempo restante como timeout. Se consulta la colección con
   `n_results = max(1, min(top_k, count))`, con `top_k = 3` y **sin umbral de
   score**. Las distancias se conservan solo como metadato de diagnóstico.
5. **Sin fragmentos** — si la recuperación devuelve una lista vacía, se responde
   con abstención.
6. **Generación** — se envía un prompt de sistema que exige un JSON con
   `sin_evidencia`, `respuesta` y `citas`. Hay como máximo **un reintento**
   (`1 + MAX_REINTENTOS_GENERACION`), y solo cuando la salida tiene forma
   inválida. No se reintenta ante timeout, error de conexión o corpus no
   indexado.
7. **Abstención del modelo** — si `sin_evidencia` es `true`, se devuelve la
   abstención estándar sin reintentar.
8. **Validación de fuentes** — `documentos_indexados()` devuelve únicamente los
   archivos cuyo `sha256` actual coincide con el manifiesto. `validar_fuentes()`
   exige que cada cita:
   - corresponda a un fragmento realmente recuperado;
   - pertenezca a un documento del manifiesto;
   - sea subcadena normalizada del documento actual;
   - no esté duplicada por `(documento, fragmento)`.

   Se conserva el orden de recuperación y se corta a 3 fuentes.
9. **Guardia de datos** — `respuesta_respaldada()` comprueba que todo número,
   porcentaje, URL o correo de la respuesta aparezca en los fragmentos
   validados. Si falta alguno, se abstiene.
10. **Respuesta** — con fuentes válidas devuelve `advertencia: null`; en
    cualquier otro caso devuelve la abstención con `fuentes: []`.

## 5. Presupuesto global de 12 s

El límite de `RNF-01` se implementa con un único `deadline` por consulta. El
tiempo consumido por `esta_indexado()`, la recuperación, la generación y un
eventual reintento descuenta del mismo presupuesto. Antes de cada llamada a
Ollama se calcula el tiempo restante y se usa como timeout; si ya se agotó, no
se llama al servicio y se responde `504`.

Las pruebas unitarias usan un reloj monotónico falso para verificar que el
reintento no concede más de 12 s y que el tiempo de `esta_indexado()` consume
presupuesto. La latencia real con el corpus y Ollama **no** está medida porque
hoy faltan esas dependencias.

## 6. Decisiones

Estado: **Respetada** = implementada y cubierta por pruebas unitarias o de API
con dobles; **Respetada (unitaria), e2e pendiente** = implementada y probada con
dobles o archivos temporales, pero falta validación de extremo a extremo;
**Pendiente por dependencia** = su validación requiere `documentos-demo/`,
`chromadb` y/u Ollama, ausentes en este entorno.

### 6.1 Decisiones v1.1 (aprobadas)

| ID | Decisión | Estado real |
|---|---|---|
| D-01 | Pregunta de máximo 1,000 caracteres tras `strip()`; vacía tras normalizar → 422. | Respetada |
| D-02 | `/api/salud` es la ruta principal; no existe `/salud` raíz; `/api/health` es alias compatible. | Respetada |
| D-03 | La respuesta elimina `pregunta`; solo `respuesta`, `fuentes` y `advertencia`. | Respetada |
| D-04 | `advertencia` siempre presente; `null` cuando la respuesta está fundamentada. | Respetada |
| D-05 | Recuperación `top_k=3` sin umbral; no se incluyen fuentes que no respalden la respuesta. | Respetada (unitaria), e2e pendiente |
| D-06 | RF-09 lo muestra el frontend con aviso fijo; la API no agrega campo. | Respetada |
| D-07 | Texto literal de advertencia sin departamentos no documentados. | Respetada |
| D-08 | Corpus sin indexar → 503; pregunta sin evidencia → 200 con `fuentes: []` y advertencia. | Respetada (unitaria), e2e pendiente |
| D-09 | Campos adicionales en la petición → 422 (`extra="forbid"`). | Respetada |
| D-10 | Solo `/api`; no existe `/api/v1`. | Respetada |
| D-11 | RF-07 alineado al texto genérico de canales oficiales. | Respetada |
| D-12 | Copy de abstención: `RESPUESTA_SIN_EVIDENCIA` más la recomendación en `advertencia`. | Respetada |
| D-13 | Citas inválidas se descartan; si no queda ninguna válida → abstención. | Respetada (unitaria), e2e pendiente |
| D-14 | CLI `python -m app.rag indexar` compatible con la estructura y modelos de Ollama; requisitos documentados. | Respetada (unitaria), e2e pendiente |
| D-15 | Vitest + Testing Library verifican el aviso RF-09 en todos los estados. | Respetada |
| D-16 | `/api/health` se conserva indefinidamente como alias durante esta etapa. | Respetada |

### 6.2 Decisiones v1.1.1 (estabilización)

| ID | Decisión | Estado real |
|---|---|---|
| E-01 | `.env.example` con `DEBUG=false` y `CORS_ORIGINS` como arreglo JSON; la API arranca con esa configuración. | Respetada |
| E-02 | Reintento único y controlado del generador solo ante salida inválida; no ante timeout, conexión o corpus no indexado. | Respetada |
| E-03 | Validación de fuentes contra el manifiesto indexado (`sha256` de bytes); documentos nuevos o modificados no se citan. | Respetada (unitaria), e2e pendiente |
| E-04 | Deadline global de 12 s compartido por comprobación de índice, recuperación y generación; el reintento consume el mismo presupuesto. | Respetada (unitaria), e2e pendiente |
| E-05 | `CORPUS_DIR` del ejemplo sin `..`, compatible con el guard del CLI. | Respetada |
| E-06 | Documentación alineada (RF-10, reglas de agentes, README, arquitectura y pruebas). | Respetada |

## 7. Implementado y verificado

- Contrato de `POST /api/consulta` y validación de la petición.
- Rutas `/api/salud` y `/api/health`; ausencia de `/api/v1`.
- Errores de dominio `500/503/504` con `{error, mensaje}`.
- Recuperación con `top_k=3` sin umbral, usando dobles.
- Validación de citas, manifiesto y guardia de datos con dobles y archivos
  temporales.
- Reintento único y deadline de 12 s con reloj falso.
- CLI: códigos `0/2/3`, rechazo de `..` y corpus ausente/sin `.md`, usando
  dependencias simuladas o su ausencia real.
- Frontend: 8 pruebas Vitest en 2 archivos y compilación de producción correcta.

## 8. Pendiente de validación con corpus real

- `documentos-demo/` no existe en el repositorio.
- `chromadb` y `ollama` no están instalados en el entorno de pruebas actual.
- Las 6 pruebas de integración se omiten; **no están aprobadas**.
- Sin corpus real no se validan de extremo a extremo: CA-07, CA-08, CA-11,
  CA-23, CA-26 y CA-29, la latencia real ni la indexación real.
- La uniformidad del cuerpo `422` con `{error, mensaje}` no está implementada.
- La indexación real debe ejecutarse con un corpus acordado con el responsable
  del corpus; no se deben inventar documentos ni preguntas institucionales.

## 9. Límites y riesgos

- El corpus es material didáctico; nunca debe presentarse como normativa
  oficial.
- La calidad de la recuperación depende del corpus y del modelo local.
- La abstención protege contra datos inventados, pero puede descartar respuestas
  útiles si el modelo parafrasea un dato sensible.
- El frontend no cambió en v1.1.1; su verificación corresponde al incremento
  v1.1.
