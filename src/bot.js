import { guardarMensaje, registrarGrupo } from './database/db.js'
import { cmdPendientes } from './commands/pendientes.js'
import { cmdAñadir } from './commands/añadir.js'
import { cmdHecho } from './commands/hecho.js'
import { cmdResumen } from './commands/resumen.js'
import { cmdAyuda } from './commands/ayuda.js'

// IDs de los grupos de WhatsApp autorizados
// Formato: XXXXXXXXXXX@g.us
// Los IDs aparecen en los logs cuando el bot recibe el primer mensaje de cada grupo
const GRUPOS_AUTORIZADOS = (process.env.GRUPOS_AUTORIZADOS || '').split(',').filter(Boolean)

// Número del admin (sin + ni espacios, con código de país)
// Ejemplo: 34612345678
const ADMIN_NUMERO = process.env.ADMIN_NUMERO || ''

export async function handleMessage(sock, msg) {
  try {
    // Solo procesar mensajes de grupos
    const groupId = msg.key.remoteJid
    if (!groupId.endsWith('@g.us')) return

    // Ignorar mensajes propios del bot
    if (msg.key.fromMe) return

    // Extraer texto del mensaje (varios formatos posibles)
    const texto =
      msg.message?.conversation ||
      msg.message?.extendedTextMessage?.text ||
      msg.message?.imageMessage?.caption ||
      ''

    if (!texto) return

    const sender = msg.key.participant || ''
    const senderNumero = sender.replace('@s.whatsapp.net', '').replace('@c.us', '')

    // Log para identificar IDs de grupos (útil en el primer arranque)
    console.log(`[MSG] Grupo: ${groupId} | De: ${senderNumero} | Texto: ${texto.substring(0, 50)}`)

    // Registrar el grupo automáticamente si es nuevo
    // (el nombre real se puede actualizar manualmente en la BD)
    registrarGrupo(groupId, groupId)

    // ── WHITELIST ────────────────────────────────────────────
    // Si hay grupos configurados, solo actuar en ellos
    // Si la lista está vacía, actuar en todos (modo desarrollo)
    if (GRUPOS_AUTORIZADOS.length > 0 && !GRUPOS_AUTORIZADOS.includes(groupId)) {
      return
    }

    // Guardar mensaje en historial (para resúmenes)
    guardarMensaje(groupId, senderNumero, senderNumero, texto)

    // ── COMANDOS ─────────────────────────────────────────────
    if (!texto.startsWith('!')) return

    const partes = texto.trim().split(/\s+/)
    const comando = partes[0].toLowerCase().replace('!', '')
    const args = partes.slice(1).join(' ')

    switch (comando) {
      case 'pendientes':
        await cmdPendientes(sock, groupId)
        break

      case 'añadir':
      case 'anadir':
      case 'add':
        await cmdAñadir(sock, groupId, senderNumero, args)
        break

      case 'hecho':
      case 'done':
        await cmdHecho(sock, groupId, args)
        break

      case 'resumen':
      case 'summary':
        await cmdResumen(sock, groupId, args)
        break

      case 'ayuda':
      case 'help':
        await cmdAyuda(sock, groupId)
        break

      default:
        // Comando desconocido — no responder para no saturar el grupo
        break
    }
  } catch (error) {
    console.error('[ERROR] handleMessage:', error)
  }
}
