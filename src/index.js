import 'dotenv/config'
import {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion
} from '@whiskeysockets/baileys'
import { Boom } from '@hapi/boom'
import pino from 'pino'
import { mkdirSync } from 'fs'
import { handleMessage } from './bot.js'
import { iniciarCronJobs } from './cron/jobs.js'

const AUTH_DIR = './auth/session'
mkdirSync(AUTH_DIR, { recursive: true })

const logger = pino({ level: 'silent' })

let cronIniciado = false
let pairingCodeSolicitado = false

async function conectar() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR)
  const { version } = await fetchLatestBaileysVersion()

  console.log(`[BOT] Iniciando ATM Bot con WhatsApp v${version.join('.')}`)

  const sock = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: false,
    browser: ['ATM Bot', 'Chrome', '1.0.0'],
    syncFullHistory: false,
    markOnlineOnConnect: false
  })

  sock.ev.on('creds.update', saveCreds)

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update

    // Cuando el socket está listo pero no autenticado, solicitar código
    if (qr && !pairingCodeSolicitado) {
      pairingCodeSolicitado = true

      const telefono = process.env.TELEFONO_BOT
      if (!telefono) {
        console.log('\n[BOT] ══════════════════════════════════════════')
        console.log('[BOT] ⚠️  Falta la variable TELEFONO_BOT')
        console.log('[BOT]  Añádela en Railway con tu número de empresa')
        console.log('[BOT]  Ejemplo: 34612345678')
        console.log('[BOT] ══════════════════════════════════════════\n')
        return
      }

      try {
        // Esperar un momento para que el socket esté listo
        await new Promise(r => setTimeout(r, 3000))

        const code = await sock.requestPairingCode(telefono)
        const codigoFormateado = code.match(/.{1,4}/g).join('-')

        console.log('\n[BOT] ══════════════════════════════════════════')
        console.log('[BOT]  CÓDIGO DE VINCULACIÓN WHATSAPP BUSINESS')
        console.log('[BOT] ══════════════════════════════════════════')
        console.log(`[BOT]  👉  ${codigoFormateado}`)
        console.log('[BOT] ══════════════════════════════════════════')
        console.log('[BOT]  En tu móvil:')
        console.log('[BOT]  WhatsApp Business > ··· > Dispositivos vinculados')
        console.log('[BOT]  > Vincular dispositivo > Vincular con número de teléfono')
        console.log('[BOT]  Introduce el código de arriba')
        console.log('[BOT] ══════════════════════════════════════════\n')
      } catch (err) {
        console.error('[BOT] Error al solicitar código de vinculación:', err.message)
      }
    }

    if (connection === 'close') {
      const statusCode = (lastDisconnect?.error instanceof Boom)
        ? lastDisconnect.error.output.statusCode
        : 0

      const debeReconectar = statusCode !== DisconnectReason.loggedOut
      console.log(`[BOT] Conexión cerrada. Código: ${statusCode}. Reconectar: ${debeReconectar}`)

      if (debeReconectar) {
        pairingCodeSolicitado = false
        console.log('[BOT] Reconectando en 5 segundos...')
        setTimeout(conectar, 5000)
      } else {
        console.log('[BOT] Sesión cerrada. Borra auth/session y reinicia.')
        process.exit(1)
      }
    }

    if (connection === 'open') {
      console.log('[BOT] ✅ Conectado a WhatsApp correctamente')
      console.log('[BOT] El bot está activo y escuchando mensajes')

      if (!cronIniciado) {
        iniciarCronJobs(sock)
        cronIniciado = true
      }
    }
  })

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return
    for (const msg of messages) {
      await handleMessage(sock, msg)
    }
  })

  return sock
}

conectar().catch(err => {
  console.error('[BOT] Error fatal al arrancar:', err)
  process.exit(1)
})