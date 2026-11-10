# Requerimientos — TecBot Académico

> **Documento de demostración del curso.** No contiene requisitos oficiales de ninguna institución. Los documentos fuente son ficticios.

## 1. Problema

Los estudiantes necesitan consultar requisitos y procedimientos académicos dispersos en varios documentos. El asistente debe responder con base en un corpus de demostración, citar la fuente y reconocer cuando no tiene información.

## 2. Usuarios

- Estudiantes de nuevo ingreso.
- Estudiantes de semestres avanzados.
- Egresados.
- Personal de apoyo académico.
- Docentes.

## 3. Alcance

Incluye consultas sobre servicio social, residencias, titulación, acreditación y trámites generales. No incluye autenticación, datos personales, trámites oficiales ni integración con sistemas institucionales.

## 4. Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-01 | Recibir una pregunta en lenguaje natural. | Alta |
| RF-02 | Validar pregunta vacía o mayor a 1,000 caracteres. | Alta |
| RF-03 | Recuperar fragmentos del corpus antes de responder. | Alta |
| RF-04 | Responder en español, de forma breve. | Alta |
| RF-05 | Mostrar al menos una fuente por respuesta fundamentada. | Alta |
| RF-06 | Abstenerse cuando no hay evidencia suficiente. | Alta |
| RF-07 | Recomendar consultar los canales oficiales de la institución cuando no haya evidencia suficiente, sin mencionar departamentos no documentados. | Alta |
| RF-08 | Mostrar estados de carga y error. | Media |
| RF-09 | Mostrar aviso de material didáctico. | Alta |
| RF-10 | Exponer `GET /salud`. | Media |

## 5. Requerimientos no funcionales

| ID | Criterio |
|---|---|
| RNF-01 | Respuesta ≤ 12 s en el equipo de demostración. |
| RNF-02 | Sin datos personales ni documentos reales. |
| RNF-03 | Fuentes trazables al documento de origen. |
| RNF-04 | Interfaz usable a 360 px. |
| RNF-05 | MCP restringido a `documentos-demo/` y sin escritura. |
| RNF-06 | Proyecto reproducible con README y scripts. |

## 6. Historias de usuario

### HU-01. Servicio social

**Como** estudiante de semestres avanzados, **quiero** conocer los requisitos para iniciar mi servicio social, **para** planear mi carga académica.

**Criterios de aceptación:**

- Dada una pregunta sobre requisitos, el sistema responde con al menos un requisito y cita `servicio-social.md`.
- La respuesta conserva el sentido del documento y no agrega fechas ni montos.
- Si la pregunta está vacía, devuelve 422.

### HU-02. Sin evidencia

**Como** estudiante, **quiero** recibir una respuesta honesta cuando no hay información, **para** no tomar decisiones con datos inventados.

**Criterios de aceptación:**

- La respuesta indica que no hay información suficiente.
- `fuentes` está vacío.
- `advertencia` recomienda consultar los canales oficiales de la institución.
- No se inventan documentos ni enlaces.

### HU-03. Fuentes

**Como** estudiante, **quiero** ver el documento que respalda la respuesta, **para** verificarla.

**Criterios de aceptación:**

- Cada respuesta fundamentada muestra al menos un documento.
- El nombre corresponde a un archivo del corpus.
- El fragmento mostrado pertenece al documento citado.

## 7. Preguntas de ejemplo

| Pregunta | Documento esperado |
|---|---|
| ¿Qué necesito para el servicio social? | servicio-social.md |
| ¿Cómo registro mi proyecto de residencias? | residencias-profesionales.md |
| ¿Cuáles son las modalidades de titulación? | titulacion.md |
| ¿Puedo acreditar una materia reprobada? | acreditacion-academica.md |
| ¿Cuál es el horario de la cafetería? | Ninguno |

## 8. Fuera de alcance

- Autenticación y expedientes.
- Trámites, firmas o pagos.
- Datos personales.
- Normativa real.
- Notificaciones o correo.
- Panel administrativo.

## 9. Pendientes para uso real

- [ ] Sustituir documentos por fuentes oficiales validadas.
- [ ] Definir responsable de actualización.
- [ ] Revisar privacidad.
- [ ] Implementar autenticación si se usan datos personales.
- [ ] Evaluar con estudiantes reales.
- [ ] Definir canal de reporte de errores.

## 10. Documentos relacionados

- `documentacion/arquitectura.md`
- `documentacion/pruebas.md`
- `documentos-demo/`
