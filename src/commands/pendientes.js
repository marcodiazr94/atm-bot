import { getPendientes } from '../database/db.js'

export async function cmdPendientes(sock, groupId) {
  const tareas = getPendientes(groupId)

  if (tareas.length === 0) {
    await sock.sendMessage(groupId, {
      text: '✅ No hay nada pendiente en este grupo. ¡Todo controlado!'
    })
    return
  }

  const lista = tareas
    .map((t, i) => `  ${i + 1}. ${t.descripcion}`)
    .join('\n')

  await sock.sendMessage(groupId, {
    text: `📋 *Pendientes (${tareas.length}):*\n\n${lista}\n\n_!hecho [número] — ej: !hecho 2 o !hecho 1 3 5_`
  })
}
