export async function cmdAyuda(sock, groupId) {
  await sock.sendMessage(groupId, {
    text: `🤖 *ATM Bot — Comandos disponibles*

📋 *Gestión de tareas:*
!pendientes — Ver todas las tareas pendientes
!añadir [tarea] — Añadir una tarea pendiente
!hecho [número] — Marcar tarea como completada

🧠 *Inteligencia artificial:*
!resumen — Resumen de las últimas 24 horas
!resumen [horas] — Resumen de las últimas N horas
  _Ejemplo: !resumen 8_

❓ *Otros:*
!ayuda — Mostrar este mensaje

_Bot desarrollado para ATM Burgers 🍔_`
  })
}
