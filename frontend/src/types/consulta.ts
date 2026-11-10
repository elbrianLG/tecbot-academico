/** Contrato de respuesta de `POST /api/consulta` (arquitectura v1.1). */

export interface FuenteDocumental {
  /** Nombre del archivo del corpus de demostración. */
  documento: string
  /** Fragmento textual que respalda la respuesta. */
  fragmento: string
}

export interface ConsultaResponse {
  respuesta: string
  fuentes: FuenteDocumental[]
  advertencia: string | null
}
