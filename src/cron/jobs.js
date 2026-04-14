import cron from 'node-cron'
import { getGruposActivos, getPendientes, limpiarMensajesAntiguos } from '../database/db.js'

// Recibe getSock: función que devuelve el socket activo en cada momento.
// Así si el bot se reconecta y cambia de socket, el cron siempre usa el nuevo.
export function iniciarCronJobs(getSock) {

  // ── RESUMEN DIARIO DE PENDIENTES ─────────────────────────
  // Todos los días a las 9:00 (hora España)
  const horaDiaria = process.env.HORA_RESUMEN_DIARIO || '0 9 * * *'

  cron.schedule(horaDiaria, async () => {
    console.log('[CRON] Ejecutando resumen diario de pendientes...')

    const sock = getSock()
    if (!sock) {
      console.warn('[CRON] Bot desconectado, saltando resumen diario')
      return
    }

    try {
      const grupos = getGruposActivos()

      for (const grupo of grupos) {
        const pendientes = getPendientes(grupo.group_id)

        let mensaje
        if (pendientes.length === 0) {
          mensaje = `☀️ *¡Buenos días equipo ATM!* 🍔\n\nHoy no hay tareas pendientes registradas.\n¡A por el día!`
        } else {
          const lista = pendientes
            .map((t, i) => `  ${i + 1}. ${t.descripcion}`)
            .join('\n')

          mensaje = `☀️ *¡Buenos días equipo ATM!* 🍔\n\n📋 *Pendientes de hoy (${pendientes.length}):*\n${lista}\n\n_Escribe !hecho [número] para marcar como completado_`
        }

        await sock.sendMessage(grupo.group_id, { text: mensaje })
        console.log(`[CRON] Mensaje enviado al grupo: ${grupo.nombre || grupo.group_id}`)
      }
    } catch (error) {
      console.error('[CRON] Error en resumen diario:', error)
    }
  }, {
    timezone: 'Europe/Madrid'
  })

  // ── LIMPIEZA SEMANAL ──────────────────────────────────────
  // Cada domingo a las 3:00 AM — borra mensajes de más de 30 días
  cron.schedule('0 3 * * 0', () => {
    try {
      const resultado = limpiarMensajesAntiguos()
      console.log(`[CRON] Limpieza semanal: ${resultado.changes} mensajes eliminados`)
    } catch (error) {
      console.error('[CRON] Error en limpieza:', error)
    }
  }, {
    timezone: 'Europe/Madrid'
  })

  console.log('[CRON] Jobs programados correctamente')
  console.log(`[CRON] Resumen diario: ${horaDiaria} (Madrid)`)
}
