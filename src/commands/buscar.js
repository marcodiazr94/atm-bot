import { getMensajesTodos } from '../database/db.js'
import { buscarEnConversacion } from '../ai/claude.js'

export async function cmdBuscar(sock, groupId, nombreGrupo, args) {
  const query = args.trim()

  if (!query) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Escribe qué quieres buscar.\n_Ejemplo: !buscar cuándo se habló del cambio de carta_'
    })
    return
  }

  const mensajes = getMensajesTodos(groupId)

  if (mensajes.length === 0) {
    await sock.sendMessage(groupId, {
      text: '📭 No hay mensajes guardados en este grupo todavía.'
    })
    return
  }

  await sock.sendMessage(groupId, {
    text: `🔍 Buscando en ${mensajes.length} mensajes guardados, un momento...`
  })

  try {
    const resultado = await buscarEnConversacion(mensajes, query, nombreGrupo)
    await sock.sendMessage(groupId, {
      text: `🔍 *Resultados para:* "${query}"\n\n${resultado}`
    })
  } catch (error) {
    console.error('[BUSCAR] Error en búsqueda IA:', error)
    await sock.sendMessage(groupId, {
      text: '❌ Error al realizar la búsqueda. Inténtalo de nuevo en un momento.'
    })
  }
}
