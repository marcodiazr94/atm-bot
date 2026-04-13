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

// Directorio donde se guardan las credenciales de la sesión de WhatsApp
const AUTH_DIR = './auth/session'
mkdirSync(AUTH_DIR, { recursive: true })

// Logger silencioso (Baileys es muy verboso por defecto)
const logger = pino({ level: 'silent' })

let cronIniciado = false

async function conectar() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR)
  const { version } = await fetchLatestBaileysVersion()

  console.log(`[BOT] Iniciando ATM Bot con WhatsApp v${version.join('.')}`)

  const sock = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: true,       // Muestra el QR en la terminal
    browser: ['ATM Bot', 'Chrome', '1.0.0'],
    syncFullHistory: false,        // No descargar historial antiguo
    markOnlineOnConnect: false     // No aparecer como "en línea" constantemente
  })

  // ── GUARDAR CREDENCIALES ────────────────────────────────
  sock.ev.on('creds.update', saveCreds)

  // ── GESTIÓN DE CONEXIÓN ─────────────────────────────────
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update

    if (qr) {
      console.log('\n[BOT] ⚠️  Escanea el QR de arriba con el teléfono de la SIM del bot')
      console.log('[BOT] Ve a WhatsApp > ... > Dispositivos vinculados > Vincular dispositivo\n')
    }

    if (connection === 'close') {
      const statusCode = (lastDisconnect?.error instanceof Boom)
        ? lastDisconnect.error.output.statusCode
        : 0

      const debeReconectar = statusCode !== DisconnectReason.loggedOut

      console.log(`[BOT] Conexión cerrada. Código: ${statusCode}. Reconectar: ${debeReconectar}`)

      if (debeReconectar) {
        console.log('[BOT] Reconectando en 5 segundos...')
        setTimeout(conectar, 5000)
      } else {
        console.log('[BOT] Sesión cerrada (logout). Borra la carpeta auth/session y reinicia.')
        process.exit(1)
      }
    }

    if (connection === 'open') {
      console.log('[BOT] ✅ Conectado a WhatsApp correctamente')
      console.log('[BOT] El bot está activo y escuchando mensajes')

      // Iniciar cron jobs solo una vez
      if (!cronIniciado) {
        iniciarCronJobs(sock)
        cronIniciado = true
      }
    }
  })

  // ── ESCUCHAR MENSAJES ───────────────────────────────────
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    // Solo procesar mensajes nuevos (no notificaciones ni historial)
    if (type !== 'notify') return

    for (const msg of messages) {
      await handleMessage(sock, msg)
    }
  })

  return sock
}

// Arrancar el bot
conectar().catch(err => {
  console.error('[BOT] Error fatal al arrancar:', err)
  process.exit(1)
})
