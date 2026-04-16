import cron from 'node-cron'
import {
  getGruposActivos,
  getPendientes,
  getRecordatoriosPendientes,
  marcarRecordatorioDisparado
} from '../database/db.js'

export function getMadridNow() {
  return new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Madrid' }))
}

function getMadridHHMM() {
  const now = getMadridNow()
  const pad = n => String(n).padStart(2, '0')
  return `${pad(now.getHours())}:${pad(now.getMinutes())}`
}

const DIAS_ALERTA = parseInt(process.env.DIAS_ALERTA_OLVIDADA) || 3

async function enviarResumenDiario(sock, grupo) {
  const pendientes = getPendientes(grupo.group_id)
  const ahora = getMadridNow()

  let mensaje
  if (pendientes.length === 0) {
    mensaje = `☀️ *¡Buenos días equipo ATM!* 🍔\n\nHoy no hay tareas pendientes registradas.\n¡A por el día!`
  } else {
    let olvidadas = 0
    const lista = pendientes.map((t, i) => {
      const creadoEn = new Date(t.created_at)
      const diasPendiente = Math.floor((ahora - creadoEn) / (1000 * 60 * 60 * 24))
      const esOlvidada = diasPendiente >= DIAS_ALERTA
      if (esOlvidada) olvidadas++
      const prefijo = esOlvidada ? `⚠️` : `  ${i + 1}.`
      const asignado = t.asignado_a ? ` (${t.asignado_a})` : ''
      return `${prefijo} ${t.descripcion}${asignado}`
    }).join('\n')

    mensaje = `☀️ *¡Buenos días equipo ATM!* 🍔\n\n📋 *Pendientes de hoy (${pendientes.length}):*\n${lista}\n\n_Escribe !hecho [número] para marcar como completado_`

    if (olvidadas > 0) {
      mensaje += `\n\n_⚠️ ${olvidadas} tarea${olvidadas !== 1 ? 's' : ''} lleva${olvidadas !== 1 ? 'n' : ''} más de ${DIAS_ALERTA} días pendiente${olvidadas !== 1 ? 's' : ''}_`
    }
  }

  await sock.sendMessage(grupo.group_id, { text: mensaje })
  console.log(`[CRON] Resumen enviado al grupo: ${grupo.nombre || grupo.group_id}`)
}

// Recibe getSock: función que devuelve el socket activo en cada momento.
// Así si el bot se reconecta y cambia de socket, el cron siempre usa el nuevo.
export function iniciarCronJobs(getSock) {

  // ── JOB CADA MINUTO: resumen diario + recordatorios ───────
  cron.schedule('* * * * *', async () => {
    const sock = getSock()
    if (!sock) return

    const horaActual = getMadridHHMM()

    try {
      // 1. Comprobar si algún grupo tiene resumen programado a esta hora
      const grupos = getGruposActivos()
      for (const grupo of grupos) {
        const horaResumen = grupo.hora_resumen || '09:00'
        if (horaResumen === horaActual) {
          await enviarResumenDiario(sock, grupo)
        }
      }

      // 2. Lanzar recordatorios pendientes
      const recordatorios = getRecordatoriosPendientes()
      for (const rec of recordatorios) {
        try {
          await sock.sendMessage(rec.group_id, {
            text: `⏰ *Recordatorio:*\n${rec.texto}`
          })
          marcarRecordatorioDisparado(rec.id)
          console.log(`[CRON] Recordatorio #${rec.id} disparado al grupo ${rec.group_id}`)
        } catch (err) {
          console.error(`[CRON] Error disparando recordatorio #${rec.id}:`, err)
        }
      }
    } catch (error) {
      console.error('[CRON] Error en job minuto a minuto:', error)
    }
  }, {
    timezone: 'Europe/Madrid'
  })


  console.log('[CRON] Jobs programados correctamente')
  console.log('[CRON] Job de minuto activo para resúmenes y recordatorios (Madrid)')
}
