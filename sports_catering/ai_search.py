"""
Búsqueda de contactos de clubes deportivos en Internet usando OpenAI + búsqueda web.

Dado el nombre de un club (equipo visitante), intenta localizar su web oficial
y extraer email, teléfono, redes sociales y persona/departamento de contacto.

Requiere la variable de entorno OPENAI_API_KEY (se lee de .env si existe).
Si la clave no está o la API falla, devuelve None y el flujo cae al enlace de Google.
"""
import json
import os
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Modelo y herramienta de búsqueda web configurables por entorno.
_MODEL = os.environ.get("ATM_AI_MODEL", "gpt-4o")
# El tipo de tool de búsqueda web ha cambiado de nombre entre versiones de la API.
_WEB_SEARCH_TYPES = ["web_search", "web_search_preview"]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _get_client():
    """Devuelve un cliente de OpenAI o None si no hay clave / SDK."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-proj-xxx"):
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(api_key=api_key)


def _build_prompt(team_name: str, city: str = "", sport: str = "") -> str:
    ctx = []
    if sport:
        ctx.append(f"deporte: {sport}")
    if city:
        ctx.append(f"suele jugar como visitante en Asturias (ciudad rival: {city})")
    ctx_str = f" ({'; '.join(ctx)})" if ctx else ""
    return (
        f"Busca en Internet los datos de contacto OFICIALES del club deportivo "
        f'"{team_name}"{ctx_str}. Es un club español que compite en una liga nacional.\n\n'
        "Necesito, por orden de prioridad:\n"
        "1. Email de contacto general o de la secretaría/gerencia del club.\n"
        "2. Teléfono de contacto.\n"
        "3. URL de la web oficial.\n"
        "4. Instagram o redes sociales oficiales.\n"
        "5. Nombre de la persona o departamento de contacto si aparece.\n\n"
        "Prioriza SIEMPRE la web oficial del club y fuentes fiables (federación, "
        "web del club). No inventes datos: si no encuentras un dato con seguridad, "
        "déjalo como null. Distingue el club correcto (puede haber homónimos).\n\n"
        "Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional, con este formato exacto:\n"
        "{\n"
        '  "email": string|null,\n'
        '  "telefono": string|null,\n'
        '  "web": string|null,\n'
        '  "instagram": string|null,\n'
        '  "contacto": string|null,\n'
        '  "confianza": "alta"|"media"|"baja",\n'
        '  "notas": string|null\n'
        "}"
    )


def _parse_json_block(text: str) -> dict | None:
    """Extrae el primer objeto JSON de la respuesta del modelo."""
    if not text:
        return None
    # Quitar cercas de código markdown si las hubiera
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _call_openai(client, prompt: str) -> str:
    """Llama a la Responses API con búsqueda web. Devuelve el texto de salida."""
    last_err = None
    for tool_type in _WEB_SEARCH_TYPES:
        try:
            resp = client.responses.create(
                model=_MODEL,
                tools=[{"type": tool_type}],
                input=prompt,
            )
            return getattr(resp, "output_text", "") or ""
        except Exception as e:  # tipo de tool no soportado u otro error
            last_err = e
            continue
    if last_err:
        raise last_err
    return ""


def search_team_contact(team_name: str, city: str = "", sport: str = "") -> dict | None:
    """
    Busca los datos de contacto del club en Internet.

    Devuelve un dict con: email, telefono, web, instagram, contacto, confianza,
    notas, fuente="ai". Devuelve None si no hay clave, la API falla o no encuentra nada.
    """
    client = _get_client()
    if client is None:
        return None

    prompt = _build_prompt(team_name, city, sport)
    try:
        raw = _call_openai(client, prompt)
    except Exception as e:
        print(f"  [IA] Error buscando '{team_name}': {e}")
        return None

    data = _parse_json_block(raw)
    if not data:
        # Último recurso: rescatar un email suelto del texto
        m = _EMAIL_RE.search(raw or "")
        if not m:
            return None
        data = {"email": m.group(0), "confianza": "baja"}

    email = (data.get("email") or "").strip() or None
    if email and not _EMAIL_RE.fullmatch(email):
        # Si el email devuelto no es válido, intentar rescatar uno del campo o texto
        m = _EMAIL_RE.search(email) or _EMAIL_RE.search(raw or "")
        email = m.group(0) if m else None

    return {
        "email": email,
        "telefono": (data.get("telefono") or "").strip() or None,
        "web": (data.get("web") or "").strip() or None,
        "instagram": (data.get("instagram") or "").strip() or None,
        "contacto": (data.get("contacto") or "").strip() or None,
        "confianza": (data.get("confianza") or "baja").strip().lower(),
        "notas": (data.get("notas") or "").strip() or None,
        "fuente": "ai",
    }


if __name__ == "__main__":
    # Prueba rápida: python -m sports_catering.ai_search "CD Lugo"
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "Real Racing Club de Santander"
    print(f"Buscando contacto de: {name}\n")
    result = search_team_contact(name, sport="FUTBOL")
    if result is None:
        print("Sin resultado (¿falta OPENAI_API_KEY en .env?).")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
