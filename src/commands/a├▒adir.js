import { añadirTarea } from '../database/db.js'

export async function cmdAñadir(sock, groupId, sender, args) {
  const descripcion = args.trim()

  if (!descripcion) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Escribe la tarea después del comando.\n_Ejemplo: !añadir Llamar al proveedor de pan_'
    })
    return
  }

  añadirTarea(groupId, descripcion, sender)

  await sock.sendMessage(groupId, {
    text: `✅ Añadido a pendientes:\n"${descripcion}"`
  })
}
