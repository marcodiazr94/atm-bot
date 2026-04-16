import { getPendientes } from '../database/db.js'

const DIAS_ALERTA = parseInt(process.env.DIAS_ALERTA_OLVIDADA) || 3

export async function cmdPendientes(sock, groupId) {
  const tareas = getPendientes(groupId)

  if (tareas.length === 0) {
    await sock.sendMessage(groupId, {
      text: '✅ No hay nada pendiente en este grupo. ¡Todo controlado!'
    })
    return
  }

  const ahora = new Date()

  const lista = tareas.map((t, i) => {
    const creadoEn = new Date(t.created_at)
    const diasPendiente = Math.floor((ahora - creadoEn) / (1000 * 60 * 60 * 24))
    const olvidada = diasPendiente >= DIAS_ALERTA
    const prefijo = olvidada ? `⚠️` : `  ${i + 1}.`
    const asignado = t.asignado_a ? ` _(${t.asignado_a})_` : ''
    return `${prefijo} ${t.descripcion}${asignado}`
  }).join('\n')

  await sock.sendMessage(groupId, {
    text: `📋 *Pendientes (${tareas.length}):*\n\n${lista}\n\n_!hecho [número] — ej: !hecho 2 o !hecho 1 3 5_\n_⚠️ = más de ${DIAS_ALERTA} días sin completar_`
  })
}
