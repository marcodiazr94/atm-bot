export async function cmdAyuda(sock, groupId) {
  await sock.sendMessage(groupId, {
    text: `🤖 *ATM Bot — Comandos disponibles*

📋 *Gestión de tareas:*
!pendientes — Ver todas las tareas pendientes

!añadir [tarea] — Añadir una tarea
  _Ejemplo: !añadir Llamar al proveedor_

!añadir - tarea1 - tarea2 - tarea3 — Añadir varias tareas a la vez
  _Ejemplo: !añadir - Limpiar freidoras - Reponer salsas - Llamar proveedor_

!hecho [número] — Marcar una tarea como completada
  _Ejemplo: !hecho 2_

!hecho [n1] [n2] ... — Marcar varias tareas a la vez
  _Ejemplo: !hecho 1 3 5_

🧠 *Inteligencia artificial:*
!resumen — Resumen de las últimas 24 horas
!resumen [horas] — Resumen de las últimas N horas
  _Ejemplo: !resumen 8_

🌐 *Panel de administración web:*
Accede desde el navegador para gestionar el bot visualmente:
  • Ver y completar tareas pendientes de todos los grupos
  • Activar o desactivar grupos con un toggle — si desactivas un grupo el bot deja de responder en él
  • Los grupos aparecen automáticamente en el panel en cuanto el bot recibe su primer mensaje

❓ *Otros:*
!ayuda — Mostrar este mensaje

_Bot desarrollado para ATM Burgers 🍔_`
  })
}
