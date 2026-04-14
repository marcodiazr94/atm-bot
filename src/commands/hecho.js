import { getPendientes, marcarHecho } from '../database/db.js'

export async function cmdHecho(sock, groupId, args) {
  const partes = args.trim().split(/\s+/).filter(Boolean)

  if (partes.length === 0) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Indica el número de la tarea a marcar como hecha.\n_Ejemplos:_\n!hecho 2\n!hecho 1 3 5\n\nEscribe !pendientes para ver la lista numerada.'
    })
    return
  }

  const numeros = partes.map(p => parseInt(p)).filter(n => !isNaN(n) && n >= 1)

  if (numeros.length === 0) {
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

  // Validar que todos los números estén dentro del rango
  const fuera = numeros.filter(n => n > tareas.length)
  if (fuera.length > 0) {
    await sock.sendMessage(groupId, {
      text: `⚠️ Los números ${fuera.join(', ')} no existen. Solo hay ${tareas.length} tarea(s) pendiente(s). Escribe !pendientes para ver la lista.`
    })
    return
  }

  // Eliminar duplicados y recoger los IDs antes de marcar (los índices no cambian al marcar por ID)
  const numerosUnicos = [...new Set(numeros)].sort((a, b) => a - b)
  const tareasAMarcar = numerosUnicos.map(n => tareas[n - 1])

  for (const tarea of tareasAMarcar) {
    marcarHecho(groupId, tarea.id)
  }

  if (tareasAMarcar.length === 1) {
    await sock.sendMessage(groupId, {
      text: `✅ Marcado como hecho:\n"${tareasAMarcar[0].descripcion}"`
    })
  } else {
    const lista = tareasAMarcar.map((t, i) => `  ${i + 1}. ${t.descripcion}`).join('\n')
    await sock.sendMessage(groupId, {
      text: `✅ *${tareasAMarcar.length} tareas marcadas como hechas:*\n\n${lista}`
    })
  }
}
