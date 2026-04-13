import { getPendientes, marcarHecho } from '../database/db.js'

export async function cmdHecho(sock, groupId, args) {
  const numero = parseInt(args.trim())

  if (isNaN(numero) || numero < 1) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Indica el número de la tarea a marcar como hecha.\n_Ejemplo: !hecho 2_\n\nEscribe !pendientes para ver la lista numerada.'
    })
    return
  }

  const tareas = getPendientes(groupId)

  if (tareas.length === 0) {
    await sock.sendMessage(groupId, {
      text: '✅ No hay tareas pendientes.'
    })
    return
  }

  if (numero > tareas.length) {
    await sock.sendMessage(groupId, {
      text: `⚠️ Solo hay ${tareas.length} tarea(s) pendiente(s). Escribe !pendientes para ver la lista.`
    })
    return
  }

  const tarea = tareas[numero - 1]
  marcarHecho(groupId, tarea.id)

  await sock.sendMessage(groupId, {
    text: `✅ Marcado como hecho:\n"${tarea.descripcion}"`
  })
}
