import Database from 'better-sqlite3'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))

// En Railway solo hay un volumen persistente (/app/auth).
// Se puede sobreescribir con la variable de entorno DB_PATH.
const DB_PATH = process.env.DB_PATH || join(__dirname, '../../auth/atm.db')

import { mkdirSync } from 'fs'
mkdirSync(dirname(DB_PATH), { recursive: true })

const db = new Database(DB_PATH)

// Optimizaciones de rendimiento
db.pragma('journal_mode = WAL')
db.pragma('foreign_keys = ON')

// Crear tablas si no existen
db.exec(`
  CREATE TABLE IF NOT EXISTS tareas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id      TEXT NOT NULL,
    descripcion   TEXT NOT NULL,
    estado        TEXT DEFAULT 'pendiente',
    creado_por    TEXT,
    created_at    DATETIME DEFAULT (datetime('now', 'localtime')),
    done_at       DATETIME
  );

  CREATE TABLE IF NOT EXISTS mensajes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id    TEXT NOT NULL,
    sender      TEXT NOT NULL,
    nombre      TEXT,
    texto       TEXT NOT NULL,
    timestamp   DATETIME DEFAULT (datetime('now', 'localtime'))
  );

  CREATE TABLE IF NOT EXISTS grupos_config (
    group_id      TEXT PRIMARY KEY,
    nombre        TEXT NOT NULL,
    hora_resumen  TEXT DEFAULT '09:00',
    activo        INTEGER DEFAULT 0
  );

  CREATE TABLE IF NOT EXISTS recordatorios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id   TEXT NOT NULL,
    texto      TEXT NOT NULL,
    fire_at    TEXT NOT NULL,
    creado_por TEXT,
    disparado  INTEGER DEFAULT 0
  );
`)

// Migraciones seguras
try { db.exec(`ALTER TABLE tareas ADD COLUMN asignado_a TEXT`) } catch {}

// ─── TAREAS ───────────────────────────────────────────────────

export function añadirTarea(groupId, descripcion, creadoPor, asignadoA = null) {
  const stmt = db.prepare(`
    INSERT INTO tareas (group_id, descripcion, creado_por, asignado_a)
    VALUES (?, ?, ?, ?)
  `)
  return stmt.run(groupId, descripcion, creadoPor, asignadoA)
}

export function getPendientes(groupId) {
  return db.prepare(`
    SELECT * FROM tareas
    WHERE group_id = ? AND estado = 'pendiente'
    ORDER BY created_at ASC
  `).all(groupId)
}

export function marcarHecho(groupId, id) {
  const stmt = db.prepare(`
    UPDATE tareas
    SET estado = 'hecho', done_at = datetime('now', 'localtime')
    WHERE id = ? AND group_id = ? AND estado = 'pendiente'
  `)
  return stmt.run(id, groupId)
}

export function borrarTarea(groupId, id) {
  const stmt = db.prepare(`
    DELETE FROM tareas
    WHERE id = ? AND group_id = ? AND estado = 'pendiente'
  `)
  return stmt.run(id, groupId)
}

export function getHistorial(groupId, dias = 7) {
  return db.prepare(`
    SELECT * FROM tareas
    WHERE group_id = ?
      AND estado = 'hecho'
      AND done_at >= datetime('now', 'localtime', '-' || ? || ' days')
    ORDER BY done_at DESC
    LIMIT 50
  `).all(groupId, dias)
}

export function getTodasTareas(groupId) {
  return db.prepare(`
    SELECT * FROM tareas
    WHERE group_id = ?
    ORDER BY created_at DESC
    LIMIT 50
  `).all(groupId)
}

// ─── RECORDATORIOS ────────────────────────────────────────────

export function añadirRecordatorio(groupId, texto, fireAt, creadoPor) {
  const stmt = db.prepare(`
    INSERT INTO recordatorios (group_id, texto, fire_at, creado_por)
    VALUES (?, ?, ?, ?)
  `)
  return stmt.run(groupId, texto, fireAt, creadoPor)
}

// ahoraStr: fecha en formato 'YYYY-MM-DD HH:MM:SS' en hora Madrid
// Se pasa desde el cron para evitar depender del timezone del servidor
export function getRecordatoriosPendientes(ahoraStr) {
  return db.prepare(`
    SELECT * FROM recordatorios
    WHERE disparado = 0
      AND fire_at <= ?
  `).all(ahoraStr)
}

export function marcarRecordatorioDisparado(id) {
  return db.prepare(`
    UPDATE recordatorios SET disparado = 1 WHERE id = ?
  `).run(id)
}

export function limpiarRecordatoriosAntiguos() {
  return db.prepare(`
    DELETE FROM recordatorios
    WHERE disparado = 1
      AND fire_at < datetime('now', 'localtime', '-7 days')
  `).run()
}

// ─── MENSAJES ─────────────────────────────────────────────────

export function guardarMensaje(groupId, sender, nombre, texto) {
  // Solo guarda si el texto tiene contenido real
  if (!texto || texto.trim().length < 2) return

  const stmt = db.prepare(`
    INSERT INTO mensajes (group_id, sender, nombre, texto)
    VALUES (?, ?, ?, ?)
  `)
  stmt.run(groupId, sender, nombre, texto)
}

export function getMensajesTodos(groupId, limite = 1500) {
  return db.prepare(`
    SELECT nombre, texto, timestamp
    FROM mensajes
    WHERE group_id = ?
    ORDER BY timestamp ASC
    LIMIT ?
  `).all(groupId, limite)
}

export function getMensajes(groupId, horas = 24) {
  return db.prepare(`
    SELECT nombre, texto, timestamp
    FROM mensajes
    WHERE group_id = ?
      AND timestamp >= datetime('now', 'localtime', '-' || ? || ' hours')
    ORDER BY timestamp ASC
  `).all(groupId, horas)
}

export function limpiarMensajesAntiguos() {
  return db.prepare(`
    DELETE FROM mensajes
    WHERE timestamp < datetime('now', 'localtime', '-30 days')
  `).run()
}

// ─── GRUPOS ───────────────────────────────────────────────────

export function registrarGrupo(groupId, nombre) {
  const stmt = db.prepare(`
    INSERT OR IGNORE INTO grupos_config (group_id, nombre, activo)
    VALUES (?, ?, 0)
  `)
  return stmt.run(groupId, nombre)
}

export function getGruposActivos() {
  return db.prepare(`
    SELECT * FROM grupos_config WHERE activo = 1
  `).all()
}

export function getGrupo(groupId) {
  return db.prepare(`
    SELECT * FROM grupos_config WHERE group_id = ?
  `).get(groupId)
}

export function getAllGrupos() {
  return db.prepare(`
    SELECT * FROM grupos_config ORDER BY activo DESC, nombre ASC
  `).all()
}

export function setGrupoActivo(groupId, activo) {
  return db.prepare(`
    UPDATE grupos_config SET activo = ? WHERE group_id = ?
  `).run(activo ? 1 : 0, groupId)
}

export function setHoraResumen(groupId, hora) {
  return db.prepare(`
    UPDATE grupos_config SET hora_resumen = ? WHERE group_id = ?
  `).run(hora, groupId)
}

export default db
