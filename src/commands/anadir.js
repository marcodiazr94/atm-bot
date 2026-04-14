import { añadirTarea } from '../database/db.js'

export async function cmdAñadir(sock, groupId, sender, args) {
  const input = args.trim()

  if (!input) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Escribe la tarea después del comando.\n_Ejemplos:_\n!añadir Llamar al proveedor de pan\n!añadir - Limpiar freidoras - Reponer salsas - Llamar proveedor'
    })
    return
  }

  // Separar por guión precedido de inicio de cadena o espacios: "- tarea", " -tarea", " - tarea"
  const tareas = input
    .split(/(?:^|\s+)-\s*/)
    .map(t => t.trim())
    .filter(t => t.length > 0)

  if (tareas.length === 1) {
    añadirTarea(groupId, tareas[0], sender)
    await sock.sendMessage(groupId, {
      text: `✅ Añadido a pendientes:\n"${tareas[0]}"`
    })
    return
  }

  // Múltiples tareas
  for (const tarea of tareas) {
    añadirTarea(groupId, tarea, sender)
  }

  const lista = tareas.map((t, i) => `  ${i + 1}. ${t}`).join('\n')
  await sock.sendMessage(groupId, {
    text: `✅ *${tareas.length} tareas añadidas a pendientes:*\n\n${lista}`
  })
}
