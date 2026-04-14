import Database from 'better-sqlite3'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DB_PATH = join(__dirname, '../../data/atm.db')

// Crea el directorio data si no existe
import { mkdirSync } from 'fs'
mkdirSync(join(__dirname, '../../data'), { recursive: true })

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
    activo        INTEGER DEFAULT 1
  );
`)

// ─── TAREAS ───────────────────────────────────────────────────

export function añadirTarea(groupId, descripcion, creadoPor) {
  const stmt = db.prepare(`
    INSERT INTO tareas (group_id, descripcion, creado_por)
    VALUES (?, ?, ?)
  `)
  return stmt.run(groupId, descripcion, creadoPor)
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

export function getTodasTareas(groupId) {
  return db.prepare(`
    SELECT * FROM tareas
    WHERE group_id = ?
    ORDER BY created_at DESC
    LIMIT 50
  `).all(groupId)
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
    INSERT OR IGNORE INTO grupos_config (group_id, nombre)
    VALUES (?, ?)
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

export default db
