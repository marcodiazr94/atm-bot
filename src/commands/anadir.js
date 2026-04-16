import { añadirTarea } from '../database/db.js'

function parsearAsignacion(texto) {
  const match = texto.match(/^(.*?)\s+@(\S+)$/)
  if (match) return { descripcion: match[1].trim(), asignadoA: match[2] }
  return { descripcion: texto, asignadoA: null }
}

export async function cmdAñadir(sock, groupId, sender, args) {
  const input = args.trim()

  if (!input) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Escribe la tarea después del comando.\n_Ejemplos:_\n!añadir Llamar al proveedor de pan\n!añadir Llamar al proveedor @Marco\n!añadir - Limpiar freidoras - Reponer salsas - Llamar proveedor'
    })
    return
  }

  // Separar por guión precedido de inicio de cadena o espacios: "- tarea", " -tarea", " - tarea"
  const tareas = input
    .split(/(?:^|\s+)-\s*/)
    .map(t => t.trim())
    .filter(t => t.length > 0)

  if (tareas.length === 1) {
    const { descripcion, asignadoA } = parsearAsignacion(tareas[0])
    añadirTarea(groupId, descripcion, sender, asignadoA)
    let texto = `✅ Añadido a pendientes:\n"${descripcion}"`
    if (asignadoA) texto += `\n→ asignado a *${asignadoA}*`
    await sock.sendMessage(groupId, { text: texto })
    return
  }

  // Múltiples tareas
  const tareasParseadas = tareas.map(t => parsearAsignacion(t))
  for (const { descripcion, asignadoA } of tareasParseadas) {
    añadirTarea(groupId, descripcion, sender, asignadoA)
  }

  const lista = tareasParseadas.map(({ descripcion, asignadoA }, i) => {
    let linea = `  ${i + 1}. ${descripcion}`
    if (asignadoA) linea += ` _(${asignadoA})_`
    return linea
  }).join('\n')

  await sock.sendMessage(groupId, {
    text: `✅ *${tareasParseadas.length} tareas añadidas a pendientes:*\n\n${lista}`
  })
}
