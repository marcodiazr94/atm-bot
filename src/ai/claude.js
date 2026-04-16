// Wrapper para la API de ChatGPT (OpenAI)

const OPENAI_API_KEY = process.env.OPENAI_API_KEY

export async function callClaude(prompt) {
  if (!OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY no configurada en variables de entorno')
  }

  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${OPENAI_API_KEY}`
    },
    body: JSON.stringify({
      model: 'gpt-4o',
      max_tokens: 1000,
      messages: [{ role: 'user', content: prompt }]
    })
  })

  if (!response.ok) {
    const err = await response.text()
    throw new Error(`Error OpenAI API: ${response.status} — ${err}`)
  }

  const data = await response.json()
  return data.choices[0].message.content
}

export async function buscarEnConversacion(mensajes, query, nombreGrupo) {
  if (mensajes.length === 0) {
    return 'No hay mensajes registrados en este grupo para buscar.'
  }

  const conversacion = mensajes
    .map(m => `[${m.timestamp}] ${m.nombre || 'Desconocido'}: ${m.texto}`)
    .join('\n')

  const prompt = `
Eres el asistente de búsqueda de ATM Burgers, una cadena de hamburguesas de Asturias (España).

Tienes el historial completo de conversación del grupo "${nombreGrupo}" (${mensajes.length} mensajes).
El usuario quiere encontrar cuándo y cómo se habló sobre el siguiente tema:

BÚSQUEDA: "${query}"

Analiza toda la conversación e identifica TODOS los momentos en que se habló sobre ese tema.
Para cada resultado relevante encontrado, indica:
- 📅 La fecha y hora aproximada
- 👤 Quién lo mencionó
- 💬 Un extracto literal o muy fiel de lo que se dijo
- 📝 Un breve resumen del contexto si hace falta

Si hay varios momentos distintos, enuméralos por orden cronológico.
Si el tema no aparece en la conversación, responde claramente que no se encontró nada.
No inventes información que no esté en los mensajes.

HISTORIAL DE CONVERSACIÓN:
${conversacion}
`

  return await callClaude(prompt)
}

export async function resumirConversacion(mensajes, nombreGrupo, horas) {
  if (mensajes.length === 0) {
    return `No hay mensajes registrados en las últimas ${horas} horas.`
  }

  const conversacion = mensajes
    .map(m => `[${m.timestamp}] ${m.nombre || 'Desconocido'}: ${m.texto}`)
    .join('\n')

  const prompt = `
Eres la secretaria virtual de ATM Burgers, una cadena de hamburguesas de Asturias (España) con locales en Oviedo y Gijón, y un food truck.

Analiza la siguiente conversación del grupo de trabajo "${nombreGrupo}" y genera un resumen ejecutivo en español.

El resumen debe incluir:
- 📋 TEMAS TRATADOS: brevemente qué se habló
- ✅ DECISIONES TOMADAS: qué se decidió (si hubo)
- ⚠️ PENDIENTE / SIN RESOLVER: temas que quedaron en el aire
- 👤 MENCIONES IMPORTANTES: si alguien fue asignado a algo concreto

Sé conciso, directo y usa bullet points. Si no hay contenido relevante en alguna sección, omítela.
No inventes nada que no esté en la conversación.

CONVERSACIÓN (últimas ${horas} horas):
${conversacion}
`

  return await callClaude(prompt)
}
