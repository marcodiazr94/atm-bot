# 🍔 ATM Catering Deportivo

Gestión de catering deportivo post-partido para equipos visitantes en Asturias.

---

## Comandos disponibles

| Comando | Descripción |
|---|---|
| `!pendientes` | Lista las tareas pendientes |
| `!añadir [tarea]` | Añade una tarea a la lista |
| `!hecho [número]` | Marca una tarea como completada |
| `!resumen` | Resumen IA de las últimas 24h |
| `!resumen [horas]` | Resumen IA de las últimas N horas |
| `!ayuda` | Muestra la lista de comandos |

---

## Despliegue en Railway — Paso a paso

### 1. Requisitos previos
- Cuenta en [GitHub](https://github.com) (gratis)
- Cuenta en [Railway](https://railway.app) (gratis)
- API Key de [Anthropic](https://console.anthropic.com) (para los resúmenes con IA)
- SIM de prepago con WhatsApp activado (el número del bot)

### 2. Subir el código a GitHub

1. Crea un repositorio nuevo en GitHub (privado, sin inicializar)
2. En tu ordenador, abre una terminal en la carpeta del proyecto
3. Ejecuta:
```bash
git init
git add .
git commit -m "ATM Bot inicial"
git remote add origin https://github.com/TU_USUARIO/atm-bot.git
git push -u origin main
```

### 3. Desplegar en Railway

1. Ve a [railway.app](https://railway.app) → New Project → GitHub Repository
2. Selecciona el repositorio `atm-bot`
3. Railway detecta automáticamente que es Node.js y lo despliega

### 4. Configurar variables de entorno en Railway

En tu proyecto de Railway → pestaña **Variables**, añade:

| Variable | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | Tu clave de Anthropic |
| `ADMIN_NUMERO` | Tu número (ej: 34612345678) |
| `GRUPOS_AUTORIZADOS` | Vacío por ahora (se rellena después) |
| `HORA_RESUMEN_DIARIO` | `0 9 * * *` |

### 5. Añadir disco persistente en Railway

1. En tu proyecto → **Add Service** → **Volume**
2. Monta el volumen en `/app/data` (para la base de datos SQLite)
3. Crea otro volumen en `/app/auth` (para las credenciales de WhatsApp)

### 6. Escanear el QR de WhatsApp

1. Ve a Railway → tu servicio → pestaña **Logs**
2. Verás un código QR en la terminal
3. En el teléfono de la SIM del bot: WhatsApp → ··· → Dispositivos vinculados → Vincular dispositivo
4. Escanea el QR
5. El bot confirmará: "✅ Conectado a WhatsApp correctamente"

### 7. Obtener los IDs de los grupos

1. Añade el número del bot a los grupos de ATM desde tu teléfono
2. Escribe cualquier mensaje en el grupo (o `!ayuda`)
3. En los logs de Railway verás: `[MSG] Grupo: XXXXXXXXXXX@g.us`
4. Copia esos IDs y ponlos en la variable `GRUPOS_AUTORIZADOS` separados por comas

### 8. ¡Listo!

El bot ya está activo. A las 9:00 cada mañana mandará automáticamente los pendientes del día.

---

## Estructura del proyecto

```
atm-bot/
├── src/
│   ├── index.js          ← Arranque y conexión WhatsApp
│   ├── bot.js            ← Router de comandos
│   ├── commands/         ← Un archivo por comando
│   ├── database/db.js    ← SQLite
│   ├── ai/claude.js      ← Integración con Claude API
│   └── cron/jobs.js      ← Tareas programadas
├── .env.example          ← Plantilla de variables de entorno
├── railway.json          ← Configuración de Railway
└── package.json
```

---

## Stack tecnológico

- **Node.js** — Entorno de ejecución
- **Baileys** — Conexión con WhatsApp (no oficial)
- **SQLite** — Base de datos local
- **node-cron** — Tareas programadas
- **Claude API** — IA para resúmenes inteligentes
- **Railway** — Servidor en la nube

---

_Desarrollado para ATM Burgers 🍔 Oviedo & Gijón_
