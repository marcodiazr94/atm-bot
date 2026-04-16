export async function cmdAyuda(sock, groupId) {
  await sock.sendMessage(groupId, {
    text: `🤖 *ATM Bot — Comandos disponibles*

📋 *Gestión de tareas:*
!pendientes — Ver tareas pendientes (⚠️ = más de 3 días sin completar)

!añadir [tarea] — Añadir una tarea
  Ejemplo: !añadir Llamar al proveedor

!añadir [tarea] @Nombre — Asignar tarea a una persona
  Ejemplo: !añadir Revisar pedido @Marco

!añadir - tarea1 - tarea2 - tarea3 — Añadir varias a la vez
  Ejemplo: !añadir - Limpiar freidoras - Reponer salsas

!hecho [n] o !hecho [n1] [n2]... — Marcar como hecha(s)
  Ejemplo: !hecho 2 o !hecho 1 3 5

!borrar [n] o !borrar [n1] [n2]... — Borrar tarea(s) de la lista
  Ejemplo: !borrar 3

!mis-tareas [Nombre] — Ver tareas asignadas a una persona
  Ejemplo: !mis-tareas Marco

!historial — Tareas completadas en los últimos 7 días
!historial [días] — Ejemplo: !historial 14

⏰ *Recordatorios:*
!recordar en [tiempo] [mensaje] — Recordatorio en X tiempo
  Ejemplo: !recordar en 2h Sacar la masa del congelador
  Ejemplo: !recordar en 30m Llamar al proveedor

!recordar a las [HH:MM] [mensaje] — Recordatorio a una hora
  Ejemplo: !recordar a las 17:00 Reunión del equipo

📢 *Avisos:*
!avisar [mensaje] — Enviar aviso a todos los grupos activos
  Ejemplo: !avisar Mañana cerramos a las 22:00

🧠 *Inteligencia artificial:*
!resumen — Resumen IA de las últimas 24h
!resumen [horas] — Ejemplo: !resumen 8

!buscar [tema] — Busca en toda la conversación guardada del grupo
  La IA encuentra todos los momentos en que se habló sobre ese tema,
  con fecha, quién lo dijo y extractos literales de lo dicho.
  Ejemplo: !buscar cuándo se habló del cambio de carta
  Ejemplo: !buscar decisiones sobre el proveedor de pan

🌐 *Panel de administración web:*
atm-bot-production.up.railway.app
atm-bot-production.up.railway.app/admin

Gestiona el bot desde el navegador:
  • Ver y completar tareas de todos los grupos
  • Añadir tareas directamente desde la web
  • Ver historial de tareas completadas
  • Activar/desactivar grupos con un toggle
  • Configurar la hora del recordatorio diario por grupo
  • Los grupos se detectan solos al recibir el primer mensaje

❓ !ayuda — Mostrar este mensaje

_Bot desarrollado para ATM Burgers 🍔_`
  })
}
