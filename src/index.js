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
import { getGruposActivos, getPendientes, marcarHecho, getAllGrupos, setGrupoActivo } from './database/db.js'

const AUTH_DIR = './auth/session'
mkdirSync(AUTH_DIR, { recursive: true })

const logger = pino({ level: 'silent' })
let cronIniciado = false
let qrActual = null
let estadoConexion = 'esperando'
// Referencia mutable al socket activo — se actualiza en cada reconexión
let currentSock = null

const PORT = process.env.PORT || 3000
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || ''

function renderAdminPanel(res) {
  const todosGrupos = getAllGrupos()
  const gruposActivos = todosGrupos.filter(g => g.activo)
  const ahora = new Date().toLocaleString('es-ES', { timeZone: 'Europe/Madrid' })
  const adminPath = `/admin${ADMIN_TOKEN ? '?token=' + ADMIN_TOKEN : ''}`

  // ── Sección tareas pendientes (solo grupos activos) ───────
  let contenidoGrupos = ''
  let totalPendientes = 0

  for (const grupo of gruposActivos) {
    const tareas = getPendientes(grupo.group_id)
    totalPendientes += tareas.length

    let filasTabla = ''
    if (tareas.length === 0) {
      filasTabla = `<tr><td colspan="4" style="text-align:center;color:#6b7280;font-style:italic;">Sin tareas pendientes ✅</td></tr>`
    } else {
      filasTabla = tareas.map((t, i) => `
        <tr>
          <td style="width:2rem;color:#9ca3af">${i + 1}</td>
          <td>${escapeHtml(t.descripcion)}</td>
          <td style="width:9rem;color:#9ca3af;font-size:.8rem">${t.created_at}</td>
          <td style="width:5rem">
            <form method="POST" action="/admin/hecho">
              <input type="hidden" name="groupId" value="${escapeHtml(grupo.group_id)}">
              <input type="hidden" name="tareaId" value="${t.id}">
              <input type="hidden" name="_redirect" value="${adminPath}">
              <button type="submit" class="btn-hecho">✓ Hecho</button>
            </form>
          </td>
        </tr>`).join('')
    }

    contenidoGrupos += `
      <div class="grupo">
        <h2>${escapeHtml(grupo.nombre || grupo.group_id)}
          <span class="badge">${tareas.length} pendiente${tareas.length !== 1 ? 's' : ''}</span>
        </h2>
        <table>
          <thead><tr><th>#</th><th>Tarea</th><th>Creada</th><th></th></tr></thead>
          <tbody>${filasTabla}</tbody>
        </table>
      </div>`
  }

  if (gruposActivos.length === 0) {
    contenidoGrupos = `<p style="text-align:center;color:#6b7280;padding:2rem 0">No hay grupos activos. Actívalos en la sección de gestión de grupos.</p>`
  }

  // ── Sección gestión de grupos (todos) ────────────────────
  let tarjetasGrupos = ''
  for (const grupo of todosGrupos) {
    const pendientes = grupo.activo ? getPendientes(grupo.group_id).length : 0
    const cls = grupo.activo ? 'activo' : 'inactivo'
    const checked = grupo.activo ? 'checked' : ''
    const idCorto = grupo.group_id.length > 24
      ? grupo.group_id.substring(0, 12) + '…' + grupo.group_id.slice(-8)
      : grupo.group_id

    tarjetasGrupos += `
      <div class="grupo-card ${cls}">
        <div class="grupo-info">
          <div class="grupo-nombre">${escapeHtml(grupo.nombre || grupo.group_id)}</div>
          <div class="grupo-id">${escapeHtml(idCorto)}</div>
          ${grupo.activo ? `<div class="grupo-pendientes">${pendientes} tarea${pendientes !== 1 ? 's' : ''} pendiente${pendientes !== 1 ? 's' : ''}</div>` : '<div class="grupo-pendientes" style="color:#ef4444">Inactivo — el bot no responde</div>'}
        </div>
        <form method="POST" action="/admin/grupos/toggle" style="flex-shrink:0">
          <input type="hidden" name="groupId" value="${escapeHtml(grupo.group_id)}">
          <input type="hidden" name="activo" value="${grupo.activo ? '0' : '1'}">
          <label class="toggle" title="${grupo.activo ? 'Desactivar grupo' : 'Activar grupo'}">
            <input type="checkbox" ${checked} onchange="this.form.submit()">
            <span class="slider"></span>
          </label>
        </form>
      </div>`
  }

  if (todosGrupos.length === 0) {
    tarjetasGrupos = `<p style="color:#6b7280">Aún no hay grupos registrados. El bot los detecta automáticamente al recibir el primer mensaje de cada grupo.</p>`
  }

  res.setHeader('Content-Type', 'text/html; charset=utf-8')
  res.end(`<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ATM Bot — Panel Admin</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;padding:1.5rem}
    header{display:flex;align-items:center;justify-content:space-between;margin-bottom:2rem;flex-wrap:wrap;gap:1rem}
    .logo{font-size:1.5rem;font-weight:700;color:#facc15}
    .status{font-size:.85rem;color:#86efac;background:#14532d;padding:.3rem .8rem;border-radius:999px}
    .meta{font-size:.8rem;color:#64748b;margin-top:.25rem}
    .resumen{background:#1e293b;border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1.5rem;display:flex;gap:2rem;flex-wrap:wrap}
    .stat{text-align:center}.stat-num{font-size:2rem;font-weight:700;color:#facc15}
    .stat-label{font-size:.8rem;color:#94a3b8}
    .grupo{background:#1e293b;border-radius:12px;padding:1.5rem;margin-bottom:1.2rem}
    .grupo h2{font-size:1.1rem;margin-bottom:1rem;display:flex;align-items:center;gap:.75rem}
    .badge{font-size:.75rem;background:#374151;color:#d1d5db;padding:.2rem .6rem;border-radius:999px;font-weight:400}
    table{width:100%;border-collapse:collapse}
    th{text-align:left;font-size:.75rem;color:#64748b;text-transform:uppercase;letter-spacing:.05em;padding:.5rem .75rem;border-bottom:1px solid #334155}
    td{padding:.6rem .75rem;border-bottom:1px solid #1f2937;font-size:.9rem;vertical-align:middle}
    tr:last-child td{border-bottom:none}
    .btn-hecho{background:#166534;color:#86efac;border:none;padding:.35rem .75rem;border-radius:6px;cursor:pointer;font-size:.8rem;font-weight:600;white-space:nowrap}
    .btn-hecho:hover{background:#15803d}
    .seccion-titulo{font-size:1rem;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;margin:2rem 0 1rem}
    .grupos-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.75rem;margin-bottom:1.5rem}
    .grupo-card{background:#1e293b;border-radius:10px;padding:1rem 1.25rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;border:2px solid transparent}
    .grupo-card.activo{border-color:#166534}
    .grupo-card.inactivo{opacity:.6}
    .grupo-info{min-width:0}
    .grupo-nombre{font-weight:600;font-size:.95rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .grupo-id{font-size:.7rem;color:#475569;margin-top:.15rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .grupo-pendientes{font-size:.75rem;color:#94a3b8;margin-top:.2rem}
    .toggle{position:relative;display:inline-block;width:46px;height:26px;flex-shrink:0}
    .toggle input{opacity:0;width:0;height:0}
    .slider{position:absolute;inset:0;background:#374151;border-radius:999px;cursor:pointer;transition:.2s}
    .slider:before{content:"";position:absolute;height:18px;width:18px;left:4px;bottom:4px;background:#fff;border-radius:50%;transition:.2s}
    input:checked+.slider{background:#16a34a}
    input:checked+.slider:before{transform:translateX(20px)}
    .grupos-hint{font-size:.8rem;color:#475569;margin-top:.5rem}
    .refresh{font-size:.8rem;color:#64748b;text-align:right;margin-top:1.5rem}
    a{color:#94a3b8;text-decoration:none}a:hover{color:#e2e8f0}
  </style>
</head>
<body>
  <header>
    <div>
      <div class="logo">🍔 ATM Bot — Panel Admin</div>
      <div class="meta">Actualizado: ${ahora}</div>
    </div>
    <div class="status">● Bot ${estadoConexion === 'conectado' ? 'conectado' : 'desconectado'}</div>
  </header>

  <div class="resumen">
    <div class="stat">
      <div class="stat-num">${totalPendientes}</div>
      <div class="stat-label">Tareas pendientes</div>
    </div>
    <div class="stat">
      <div class="stat-num">${gruposActivos.length}</div>
      <div class="stat-label">Grupos activos</div>
    </div>
    <div class="stat">
      <div class="stat-num">${todosGrupos.length}</div>
      <div class="stat-label">Grupos detectados</div>
    </div>
  </div>

  <div class="seccion-titulo">Gestión de grupos</div>
  <div class="grupos-grid">${tarjetasGrupos}</div>
  <p class="grupos-hint">Los grupos aparecen aquí automáticamente cuando el bot recibe su primer mensaje. Usa el toggle para activar o desactivar cada uno.</p>

  <div class="seccion-titulo">Tareas pendientes</div>
  ${contenidoGrupos}

  <div class="refresh"><a href="${adminPath}">↻ Refrescar</a></div>
</body>
</html>`)
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function parseBody(req) {
  return new Promise((resolve) => {
    let body = ''
    req.on('data', chunk => { body += chunk.toString() })
    req.on('end', () => {
      const params = new URLSearchParams(body)
      resolve(Object.fromEntries(params.entries()))
    })
  })
}

function isAdminAuthorized(req) {
  if (!ADMIN_TOKEN) return true
  const url = new URL(req.url, `http://localhost`)
  return url.searchParams.get('token') === ADMIN_TOKEN
}

const server = createServer(async (req, res) => {
  const urlPath = req.url.split('?')[0]

  // ── PANEL ADMIN ──────────────────────────────────────────
  if (urlPath === '/admin') {
    if (!isAdminAuthorized(req)) {
      res.writeHead(401, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('No autorizado. Añade ?token=TU_TOKEN a la URL.')
      return
    }
    renderAdminPanel(res)
    return
  }

  // ── MARCAR HECHO DESDE PANEL ─────────────────────────────
  if (urlPath === '/admin/hecho' && req.method === 'POST') {
    if (!isAdminAuthorized(req)) {
      res.writeHead(401, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('No autorizado.')
      return
    }
    const body = await parseBody(req)
    const { groupId, tareaId } = body
    if (groupId && tareaId) {
      marcarHecho(groupId, parseInt(tareaId))
    }
    const redirect = `/admin${ADMIN_TOKEN ? '?token=' + ADMIN_TOKEN : ''}`
    res.writeHead(302, { Location: redirect })
    res.end()
    return
  }

  // ── TOGGLE GRUPO ACTIVO/INACTIVO ─────────────────────────
  if (urlPath === '/admin/grupos/toggle' && req.method === 'POST') {
    if (!isAdminAuthorized(req)) {
      res.writeHead(401, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('No autorizado.')
      return
    }
    const body = await parseBody(req)
    const { groupId, activo } = body
    if (groupId) {
      setGrupoActivo(groupId, activo === '1')
      console.log(`[ADMIN] Grupo ${groupId} → activo: ${activo}`)
    }
    const redirect = `/admin${ADMIN_TOKEN ? '?token=' + ADMIN_TOKEN : ''}`
    res.writeHead(302, { Location: redirect })
    res.end()
    return
  }

  // ── PÁGINA PRINCIPAL (QR / ESTADO) ───────────────────────
  res.setHeader('Content-Type', 'text/html; charset=utf-8')

  if (estadoConexion === 'conectado') {
    res.end(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ATM Bot</title>
    <style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#111;color:#fff;}
    .box{text-align:center;padding:2rem;}h1{color:#4ade80;}a{color:#facc15}</style></head>
    <body><div class="box"><div style="font-size:4rem">✅</div><h1>ATM Bot conectado</h1>
    <p>El bot está activo y escuchando mensajes en WhatsApp.</p>
    <p style="margin-top:1rem"><a href="/admin${ADMIN_TOKEN ? '?token=' + ADMIN_TOKEN : ''}">→ Abrir panel de administración</a></p>
    </div></body></html>`)
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
      currentSock = null
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
      currentSock = sock  // Siempre actualizar la referencia al socket activo
      console.log('[BOT] ✅ Conectado a WhatsApp correctamente')
      if (!cronIniciado) {
        // Pasamos un getter para que el cron siempre use el socket más reciente
        iniciarCronJobs(() => currentSock)
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