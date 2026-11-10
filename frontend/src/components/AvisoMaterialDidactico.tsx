/**
 * Aviso permanente de material didáctico (RF-09).
 *
 * Se monta una sola vez en `App` y permanece visible en todos los estados
 * de la consulta. No debe ocultarse ni condicionarse.
 */

export const AVISO_MATERIAL_DIDACTICO =
  'Material didáctico de demostración. No es normativa oficial.'

function AvisoMaterialDidactico() {
  return (
    <div
      className="aviso-material"
      role="note"
      aria-label="Aviso de material didáctico"
    >
      <span className="aviso-material-icon" aria-hidden="true">
        !
      </span>
      <p>{AVISO_MATERIAL_DIDACTICO}</p>
    </div>
  )
}

export default AvisoMaterialDidactico
