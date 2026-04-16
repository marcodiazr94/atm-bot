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

function calcularFecha(base, cantidad, unidad) {
  const d = new Date(base)
  const u = unidad.toLowerCase()
  if (u.startsWith('m')) d.setMinutes(d.getMinutes() + cantidad)
  else if (u.startsWith('h')) d.setHours(d.getHours() + cantidad)
  else if (u.startsWith('d')) d.setDate(d.getDate() + cantidad)
  return d
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

  const UNIDAD_RE = `(\\d+)\\s*(minutos?|horas?|días?|dias?|min|m|h|d)`

  // 1. "en X unidad texto"  →  !recordar en 20m sacar la basura
  const m1 = input.match(new RegExp(`^en\\s+${UNIDAD_RE}\\s+(.+)$`, 'i'))
  if (m1) {
    fireDate = calcularFecha(ahora, parseInt(m1[1]), m1[2])
    texto = m1[3].trim()
  }

  // 2. "texto en X unidad"  →  !recordar sacar la basura en 20 minutos
  if (!fireDate) {
    const m2 = input.match(new RegExp(`^(.+?)\\s+en\\s+${UNIDAD_RE}\\s*$`, 'i'))
    if (m2) {
      fireDate = calcularFecha(ahora, parseInt(m2[2]), m2[3])
      texto = m2[1].trim()
    }
  }

  // 3. "texto dentro de X unidad"  →  !recordar sacar la basura dentro de 20 minutos
  if (!fireDate) {
    const m3 = input.match(new RegExp(`^(.+?)\\s+dentro\\s+de\\s+${UNIDAD_RE}\\s*$`, 'i'))
    if (m3) {
      fireDate = calcularFecha(ahora, parseInt(m3[2]), m3[3])
      texto = m3[1].trim()
    }
  }

  // 4. "a las HH:MM texto"  →  !recordar a las 17:00 reunión
  if (!fireDate) {
    const m4 = input.match(/^a\s+las\s+(\d{1,2})[:\.](\d{2})\s+(.+)$/i)
    if (m4) {
      fireDate = new Date(ahora)
      fireDate.setHours(parseInt(m4[1]), parseInt(m4[2]), 0, 0)
      if (fireDate <= ahora) fireDate.setDate(fireDate.getDate() + 1)
      texto = m4[3].trim()
    }
  }

  // 5. "texto a las HH:MM"  →  !recordar reunión a las 17:00
  if (!fireDate) {
    const m5 = input.match(/^(.+?)\s+a\s+las\s+(\d{1,2})[:\.](\d{2})\s*$/i)
    if (m5) {
      fireDate = new Date(ahora)
      fireDate.setHours(parseInt(m5[2]), parseInt(m5[3]), 0, 0)
      if (fireDate <= ahora) fireDate.setDate(fireDate.getDate() + 1)
      texto = m5[1].trim()
    }
  }

  if (!fireDate || !texto) {
    await sock.sendMessage(groupId, {
      text: '⚠️ No entiendo el formato. Ejemplos:\n_!recordar en 20m sacar la basura_\n_!recordar sacar la basura en 20 minutos_\n_!recordar sacar la basura dentro de 20 minutos_\n_!recordar a las 17:00 reunión_\n_!recordar reunión a las 17:00_'
    })
    return
  }

  const fireAtStr = formatForDB(fireDate)
  añadirRecordatorio(groupId, texto, fireAtStr, sender)

  await sock.sendMessage(groupId, {
    text: `⏰ Recordatorio programado para el *${formatEspañol(fireDate)}*:\n_"${texto}"_`
  })
}
