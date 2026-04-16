export async function cmdAyuda(sock, groupId) {
  await sock.sendMessage(groupId, {
    text: `🤖 *ATM Bot — Comandos*

━━━━━━━━━━━━━━━━━━━━
📋 *TAREAS*
━━━━━━━━━━━━━━━━━━━━
!pendientes
  → Lista todas las tareas (⚠️ = +3 días sin completar)

!añadir [tarea]
!añadir [tarea] @Nombre
!añadir - tarea1 - tarea2 - tarea3
  → Añade una o varias tareas, con asignación opcional

!hecho 2 · !hecho 1 3 5
  → Marca una o varias tareas como completadas

!borrar 2 · !borrar 1 3 5
  → Elimina una o varias tareas de la lista

!mis-tareas Marco
  → Tareas pendientes asignadas a una persona

!historial · !historial 14
  → Tareas completadas (últimos 7 días por defecto, máx 30)

━━━━━━━━━━━━━━━━━━━━
⏰ *RECORDATORIOS*
━━━━━━━━━━━━━━━━━━━━
!recordar en 30m [mensaje]
!recordar en 2h [mensaje]
!recordar en 1d [mensaje]
!recordar [mensaje] en 20 minutos
!recordar [mensaje] dentro de 2 horas
!recordar a las 17:00 [mensaje]
!recordar [mensaje] a las 17:00
  → Programa un aviso al grupo. El tiempo puede ir antes o después del mensaje

━━━━━━━━━━━━━━━━━━━━
📢 *AVISOS*
━━━━━━━━━━━━━━━━━━━━
!avisar [mensaje]
  → Envía el mensaje a todos los grupos activos

━━━━━━━━━━━━━━━━━━━━
🧠 *INTELIGENCIA ARTIFICIAL*
━━━━━━━━━━━━━━━━━━━━
!resumen · !resumen 8
  → Resumen IA de la conversación (24h por defecto)

!buscar [tema]
  → Busca en todo el historial guardado del grupo.
  La IA localiza cuándo se habló del tema, quién lo dijo
  y muestra extractos literales ordenados por fecha.

━━━━━━━━━━━━━━━━━━━━
🌐 *PANEL WEB*
━━━━━━━━━━━━━━━━━━━━
atm-bot-production.up.railway.app
atm-bot-production.up.railway.app/admin
  • Ver, añadir, completar y borrar tareas
  • Ver historial de completadas
  • Activar/desactivar grupos
  • Configurar hora del recordatorio diario por grupo
  • Los grupos se registran solos al primer mensaje

━━━━━━━━━━━━━━━━━━━━
!ayuda — Mostrar este mensaje
_Bot desarrollado para ATM Burgers 🍔_`
  })
}
