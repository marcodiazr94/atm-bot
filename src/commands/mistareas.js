import { getPendientes } from '../database/db.js'

const DIAS_ALERTA = parseInt(process.env.DIAS_ALERTA_OLVIDADA) || 3

export async function cmdMisTareas(sock, groupId, args) {
  const nombre = args.trim()

  if (!nombre) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Indica tu nombre.\n_Ejemplo: !mis-tareas Marco_'
    })
    return
  }

  const todasLasTareas = getPendientes(groupId)
  const ahora = new Date()

  // Filtrar tareas asignadas a esa persona (case-insensitive)
  // y mantener la posición real en la lista completa
  const misTareas = todasLasTareas
    .map((t, i) => ({ ...t, posicion: i + 1 }))
    .filter(t => t.asignado_a && t.asignado_a.toLowerCase() === nombre.toLowerCase())

  if (misTareas.length === 0) {
    await sock.sendMessage(groupId, {
      text: `📭 No hay tareas asignadas a *${nombre}*.`
    })
    return
  }

  const lista = misTareas.map(t => {
    const creadoEn = new Date(t.created_at)
    const diasPendiente = Math.floor((ahora - creadoEn) / (1000 * 60 * 60 * 24))
    const olvidada = diasPendiente >= DIAS_ALERTA
    const prefijo = olvidada ? `⚠️` : `  ${t.posicion}.`
    return `${prefijo} ${t.descripcion}`
  }).join('\n')

  await sock.sendMessage(groupId, {
    text: `📋 *Tareas de ${nombre} (${misTareas.length}):*\n\n${lista}\n\n_Usa el número para marcar con !hecho_\n_⚠️ = más de ${DIAS_ALERTA} días sin completar_`
  })
}
