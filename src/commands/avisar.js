import { getGruposActivos } from '../database/db.js'

export async function cmdAvisar(sock, groupId, sender, args) {
  const texto = args.trim()

  // Verificar permisos si ADMIN_NUMERO está definido
  if (process.env.ADMIN_NUMERO) {
    const senderNumero = sender.replace('@s.whatsapp.net', '').replace('@c.us', '')
    if (senderNumero !== process.env.ADMIN_NUMERO) {
      await sock.sendMessage(groupId, {
        text: '⛔ Solo el administrador puede usar este comando.'
      })
      return
    }
  }

  if (!texto) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Indica el mensaje a enviar.\n_Ejemplo: !avisar Mañana cerramos a las 22:00_'
    })
    return
  }

  const grupos = getGruposActivos()

  if (grupos.length === 0) {
    await sock.sendMessage(groupId, {
      text: '⚠️ No hay grupos activos a los que enviar el aviso.'
    })
    return
  }

  const mensaje = `📢 *Aviso general:*\n${texto}`
  let enviados = 0

  for (const grupo of grupos) {
    try {
      await sock.sendMessage(grupo.group_id, { text: mensaje })
      enviados++
    } catch (err) {
      console.error(`[AVISAR] Error enviando al grupo ${grupo.group_id}:`, err)
    }
  }

  await sock.sendMessage(groupId, {
    text: `✅ Aviso enviado a *${enviados}* grupo${enviados !== 1 ? 's' : ''}.`
  })
}
