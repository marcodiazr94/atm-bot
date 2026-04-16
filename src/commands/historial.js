import { getHistorial } from '../database/db.js'

export async function cmdHistorial(sock, groupId, args) {
  let dias = parseInt(args?.trim()) || 7
  if (dias < 1) dias = 1
  if (dias > 30) dias = 30

  const tareas = getHistorial(groupId, dias)

  if (tareas.length === 0) {
    await sock.sendMessage(groupId, {
      text: `📭 No hay tareas completadas en los últimos ${dias} días.`
    })
    return
  }

  const lista = tareas.map(t => {
    const fecha = t.done_at ? t.done_at.substring(0, 10) : '??'
    const asignado = t.asignado_a ? ` (${t.asignado_a})` : ''
    return `✓ ${t.descripcion}${asignado} [${fecha}]`
  }).join('\n')

  await sock.sendMessage(groupId, {
    text: `📋 *Historial — últimos ${dias} días (${tareas.length} tarea${tareas.length !== 1 ? 's' : ''}):*\n\n${lista}`
  })
}
