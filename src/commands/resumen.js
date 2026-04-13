import { getMensajes, getGrupo } from '../database/db.js'
import { resumirConversacion } from '../ai/claude.js'

export async function cmdResumen(sock, groupId, args) {
  // Horas por defecto: 24. Se puede pasar otro número: !resumen 8
  const horas = parseInt(args?.trim()) || 24

  if (horas < 1 || horas > 168) {
    await sock.sendMessage(groupId, {
      text: '⚠️ Las horas deben estar entre 1 y 168 (1 semana).\n_Ejemplo: !resumen 8_'
    })
    return
  }

  // Mensaje de espera (la IA tarda 2-4 segundos)
  await sock.sendMessage(groupId, {
    text: '⏳ Generando resumen con IA, un momento...'
  })

  const mensajes = getMensajes(groupId, horas)
  const grupo = getGrupo(groupId)
  const nombreGrupo = grupo?.nombre || 'Grupo ATM'

  try {
    const resumen = await resumirConversacion(mensajes, nombreGrupo, horas)

    await sock.sendMessage(groupId, {
      text: `📋 *Resumen últimas ${horas}h — ${nombreGrupo}*\n\n${resumen}`
    })
  } catch (error) {
    await sock.sendMessage(groupId, {
      text: '❌ Error al generar el resumen. Comprueba que la API key de Claude está configurada.'
    })
    console.error('Error en cmdResumen:', error)
  }
}
