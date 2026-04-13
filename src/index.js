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
import { createServer } from 'http'
import { handleMessage } from './bot.js'
import { iniciarCronJobs } from './cron/jobs.js'

const AUTH_DIR = './auth/session'
mkdirSync(AUTH_DIR, { recursive: true })

const logger = pino({ level: 'silent' })
let cronIniciado = false
let qrActual = null
let estadoConexion = 'esperando'

const PORT = process.env.PORT || 3000

const server = createServer((req, res) => {
  res.setHeader('Content-Type', 'text/html; charset=utf-8')

  if (estadoConexion === 'conectado') {
    res.end(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ATM Bot</title>
    <style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#111;color:#fff;}
    .box{text-align:center;padding:2rem;}h1{color:#4ade80;}</style></head>
    <body><div class="box"><div style="font-size:4rem">✅</div><h1>ATM Bot conectado</h1>
    <p>El bot está activo y escuchando mensajes en WhatsApp.</p></div></body></html>`)
    return
  }

  if (!qrActual) {
    res.end(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ATM Bot — Esperando</title>
    <meta http-equiv="refresh" content="3">
    <style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#111;color:#fff;}</style></head>
    <body><div style="text-align:center"><h2>⏳ Generando QR...</h2><p>Esta página se actualiza automáticamente.</p></div></body></html>`)
    return
  }

  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(qrActual)}`

  res.end(`<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ATM Bot — Escanea el QR</title><meta http-equiv="refresh" content="30">
  <style>
    body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#111;color:#fff;}
    .box{text-align:center;padding:2rem;max-width:420px;}
    img{border:4px solid #fff;border-radius:12px;margin:1rem 0;}
    h1{color:#facc15;}.steps{text-align:left;background:#222;padding:1rem;border-radius:8px;margin-top:1rem;}
    .steps li{margin:.5rem 0;}.warn{color:#f87171;font-size:.85rem;margin-top:1rem;}
  </style></head>
  <body><div class="box">
    <h1>🍔 ATM Bot</h1>
    <p>Escanea este QR con WhatsApp Business</p>
    <img src="${qrUrl}" alt="QR Code" width="300" height="300">
    <div class="steps"><ol>
      <li>Abre <strong>WhatsApp Business</strong></li>
      <li>Toca <strong>⋮ → Dispositivos vinculados</strong></li>
      <li>Toca <strong>Vincular un dispositivo</strong></li>
      <li>Apunta la cámara a este QR</li>
    </ol></div>
    <p class="warn">⚠️ El QR se renueva cada 30s. La página se actualiza sola.</p>
  </div></body></html>`)
})

server.listen(PORT, () => {
  console.log(`[BOT] Servidor web activo en puerto ${PORT}`)
})

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

    if (qr) {
      qrActual = qr
      estadoConexion = 'esperando_escaneo'
      console.log('[BOT] QR generado — abre la URL pública de Railway en el navegador')
    }

    if (connection === 'close') {
      qrActual = null
      estadoConexion = 'desconectado'
      const statusCode = (lastDisconnect?.error instanceof Boom)
        ? lastDisconnect.error.output.statusCode : 0
      const debeReconectar = statusCode !== DisconnectReason.loggedOut
      console.log(`[BOT] Conexión cerrada. Código: ${statusCode}. Reconectar: ${debeReconectar}`)
      if (debeReconectar) {
        console.log('[BOT] Reconectando en 5 segundos...')
        setTimeout(conectar, 5000)
      } else {
        process.exit(1)
      }
    }

    if (connection === 'open') {
      qrActual = null
      estadoConexion = 'conectado'
      console.log('[BOT] ✅ Conectado a WhatsApp correctamente')
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