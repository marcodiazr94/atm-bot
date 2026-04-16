import { añadirRecordatorio } from '../database/db.js'

function getMadridNow() {
  return new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Madrid' }))
}

function formatForDB(date) {
  const pad = n => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function formatEspañol(date) {
  const pad = n => String(n).padStart(2, '0')
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} a las ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export async function cmdRecordar(sock, groupId, sender, args) {
  const input = args.trim()

  if (!input) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Indica cuándo y qué recordar.\n_Ejemplos:_\n!recordar en 2h Sacar la masa del congelador\n!recordar en 30m Llamar al proveedor\n!recordar a las 17:00 Reunión del equipo'
    })
    return
  }

  const ahora = getMadridNow()
  let fireDate = null
  let texto = null

  // Formato relativo: "en Xm", "en Xh", "en Xd"
  const matchRelativo = input.match(/^en\s+(\d+)\s*(m|min|h|hora|horas|d|dia|días|dias)\s+(.+)$/i)
  if (matchRelativo) {
    const cantidad = parseInt(matchRelativo[1])
    const unidad = matchRelativo[2].toLowerCase()
    texto = matchRelativo[3].trim()

    fireDate = new Date(ahora)
    if (unidad === 'm' || unidad === 'min') {
      fireDate.setMinutes(fireDate.getMinutes() + cantidad)
    } else if (unidad === 'h' || unidad === 'hora' || unidad === 'horas') {
      fireDate.setHours(fireDate.getHours() + cantidad)
    } else if (unidad === 'd' || unidad === 'dia' || unidad === 'días' || unidad === 'dias') {
      fireDate.setDate(fireDate.getDate() + cantidad)
    }
  }

  // Formato absoluto: "a las HH:MM"
  if (!fireDate) {
    const matchAbsoluto = input.match(/^a\s+las\s+(\d{1,2})[:\.](\d{2})\s+(.+)$/i)
    if (matchAbsoluto) {
      const horas = parseInt(matchAbsoluto[1])
      const minutos = parseInt(matchAbsoluto[2])
      texto = matchAbsoluto[3].trim()

      fireDate = new Date(ahora)
      fireDate.setHours(horas, minutos, 0, 0)

      // Si la hora ya pasó hoy, programar para mañana
      if (fireDate <= ahora) {
        fireDate.setDate(fireDate.getDate() + 1)
      }
    }
  }

  if (!fireDate || !texto) {
    await sock.sendMessage(groupId, {
      text: '⚠️ No entiendo el formato. Usa:\n_!recordar en 2h Sacar masa_\n_!recordar en 30m Llamar proveedor_\n_!recordar a las 17:00 Reunión_'
    })
    return
  }

  const fireAtStr = formatForDB(fireDate)
  añadirRecordatorio(groupId, texto, fireAtStr, sender)

  await sock.sendMessage(groupId, {
    text: `⏰ Recordatorio programado para el *${formatEspañol(fireDate)}*:\n_"${texto}"_`
  })
}
