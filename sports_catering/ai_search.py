"""
Búsqueda profunda de contactos de clubes deportivos usando OpenAI + búsqueda web.

Busca: múltiples emails del club, nutricionista actual (nombre, email, instagram),
instagram del club, teléfono y web oficial.
"""
import json
import os
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_MODEL = os.environ.get("ATM_AI_MODEL", "gpt-4o")
_WEB_SEARCH_TYPES = ["web_search", "web_search_preview"]
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Prefijos de emails que NO interesan (protección de datos, legal, etc.)
_EMAIL_BLOCKLIST = re.compile(
    r"^(dpd|dpo|lopd|rgpd|gdpr|protecciondatos|privacidad|legal|baja)@",
    re.IGNORECASE,
)


def _get_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-proj-xxx"):
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(api_key=api_key)


def _build_prompt(team_name: str, city: str = "", sport: str = "") -> str:
    ctx_parts = []
    if sport:
        ctx_parts.append(f"deporte: {sport}")
    if city:
        ctx_parts.append(f"viaja como visitante a Asturias")
    ctx = f" ({', '.join(ctx_parts)})" if ctx_parts else ""

    return (
        f"Necesito información de contacto detallada del club deportivo español "
        f'"{team_name}"{ctx}.\n\n'
        f"INSTRUCCIONES PASO A PASO:\n"
        f"PASO 1 — Encuentra la web oficial del club y accede directamente a su página "
        f"de contacto (prueba /contacto, /contact, /club/contacto, /el-club/contacto). "
        f"Lee TODA la página y extrae cada dirección de email que aparezca, sin importar "
        f"el departamento (secretaría, comunicación, prensa, dirección deportiva, "
        f"administración, recepción, etc.).\n"
        f"PASO 2 — Busca emails adicionales en otras páginas del club: staff, directiva, "
        f"área deportiva, noticias recientes.\n"
        f"PASO 3 — Busca el NUTRICIONISTA O DIETISTA DEPORTIVO ACTUAL (temporada 2025-26 "
        f"o 2026-27) del primer equipo. Consulta noticias, LinkedIn, web del club, redes "
        f"sociales. Quiero nombre completo, email si aparece, e instagram personal.\n\n"
        f"REGLAS:\n"
        f"- Devuelve TODOS los emails encontrados (mínimo 3 si existen).\n"
        f"- EXCLUYE emails de: dpd@, dpo@, lopd@, rgpd@, protecciondatos@, privacidad@, "
        f"legal@, baja@. Estos son de protección de datos y no sirven.\n"
        f"- No inventes datos. Si no encuentras algo, pon null.\n"
        f"- Verifica que el nutricionista sea el actual, no uno de hace años.\n\n"
        f"Responde ÚNICAMENTE con este JSON exacto, sin texto adicional:\n"
        "{{\n"
        '  "emails": ["email1@club.es", "email2@club.es"],\n'
        '  "telefono": "string o null",\n'
        '  "web": "string o null",\n'
        '  "instagram_club": "string o null",\n'
        '  "nutricionista_nombre": "string o null",\n'
        '  "nutricionista_email": "string o null",\n'
        '  "nutricionista_instagram": "string o null",\n'
        '  "nutricionista_confirmado": true,\n'
        '  "confianza": "alta",\n'
        '  "notas": "string o null"\n'
        "}}"
    )


def _parse_json_block(text: str) -> dict | None:
    if not text:
        return None
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
    last_err = None
    for tool_type in _WEB_SEARCH_TYPES:
        try:
            resp = client.responses.create(
                model=_MODEL,
                tools=[{"type": tool_type}],
                input=prompt,
            )
            return getattr(resp, "output_text", "") or ""
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    return ""


def _clean_emails(raw_emails) -> list[str]:
    """Extrae emails válidos, excluyendo los de protección de datos."""
    if not raw_emails:
        return []
    if isinstance(raw_emails, str):
        candidates = _EMAIL_RE.findall(raw_emails)
    elif isinstance(raw_emails, list):
        candidates = []
        for item in raw_emails:
            if isinstance(item, str):
                candidates.extend(_EMAIL_RE.findall(item))
    else:
        return []
    seen = set()
    result = []
    for email in candidates:
        local = email.split("@")[0].lower()
        if _EMAIL_BLOCKLIST.match(email):
            continue
        if email.lower() not in seen:
            seen.add(email.lower())
            result.append(email)
    return result


def search_team_contact(team_name: str, city: str = "", sport: str = "") -> dict | None:
    """
    Búsqueda profunda del club: múltiples emails, nutricionista, instagram.

    Devuelve un dict con:
      emails (list), email (str, primero de la lista), telefono, web,
      instagram_club, nutricionista_nombre, nutricionista_email,
      nutricionista_instagram, nutricionista_confirmado,
      confianza, notas, fuente="ai"

    Devuelve None si no hay clave API o la búsqueda falla por completo.
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
        m = _EMAIL_RE.search(raw or "")
        if not m:
            return None
        data = {"emails": [m.group(0)], "confianza": "baja"}

    emails = _clean_emails(data.get("emails"))

    # Compatibilidad: si vino un solo "email" en vez de lista
    if not emails and data.get("email"):
        emails = _clean_emails(data.get("email"))

    # Si sigue sin haber emails, intentar rescatar del texto bruto
    if not emails:
        emails = _EMAIL_RE.findall(raw or "")

    if not emails:
        return None

    nutricionista_email = None
    raw_ne = (data.get("nutricionista_email") or "").strip()
    if raw_ne:
        m = _EMAIL_RE.search(raw_ne)
        nutricionista_email = m.group(0) if m else None

    return {
        "emails":                    emails,
        "email":                     emails[0],          # campo principal (compatibilidad)
        "telefono":                  (data.get("telefono") or "").strip() or None,
        "web":                       (data.get("web") or "").strip() or None,
        "instagram":                 (data.get("instagram_club") or "").strip() or None,
        "instagram_club":            (data.get("instagram_club") or "").strip() or None,
        "nutricionista_nombre":      (data.get("nutricionista_nombre") or "").strip() or None,
        "nutricionista_email":       nutricionista_email,
        "nutricionista_instagram":   (data.get("nutricionista_instagram") or "").strip() or None,
        "nutricionista_confirmado":  bool(data.get("nutricionista_confirmado", False)),
        "confianza":                 (data.get("confianza") or "baja").strip().lower(),
        "notas":                     (data.get("notas") or "").strip() or None,
        "fuente":                    "ai",
    }


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "Granada CF"
    print(f"Buscando contacto de: {name}\n")
    result = search_team_contact(name, sport="FUTBOL")
    if result is None:
        print("Sin resultado.")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
