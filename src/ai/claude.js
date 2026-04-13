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
