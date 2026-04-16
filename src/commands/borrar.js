import { getPendientes, borrarTarea } from '../database/db.js'

export async function cmdBorrar(sock, groupId, args) {
  const partes = args.trim().split(/\s+/).filter(Boolean)

  if (partes.length === 0) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Indica el número de la tarea a borrar.\n_Ejemplos:_\n!borrar 3\n!borrar 1 3 5\n\nEscribe !pendientes para ver la lista numerada.'
    })
    return
  }

  const numeros = partes.map(p => parseInt(p)).filter(n => !isNaN(n) && n >= 1)

  if (numeros.length === 0) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Indica el número de la tarea a borrar.\n_Ejemplo: !borrar 3_\n\nEscribe !pendientes para ver la lista numerada.'
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

  // Eliminar duplicados y recoger los IDs antes de borrar
  const numerosUnicos = [...new Set(numeros)].sort((a, b) => a - b)
  const tareasABorrar = numerosUnicos.map(n => tareas[n - 1])

  for (const tarea of tareasABorrar) {
    borrarTarea(groupId, tarea.id)
  }

  if (tareasABorrar.length === 1) {
    await sock.sendMessage(groupId, {
      text: `🗑️ Tarea borrada: "${tareasABorrar[0].descripcion}"`
    })
  } else {
    const lista = tareasABorrar.map((t, i) => `  ${i + 1}. ${t.descripcion}`).join('\n')
    await sock.sendMessage(groupId, {
      text: `🗑️ *${tareasABorrar.length} tareas borradas:*\n\n${lista}`
    })
  }
}
