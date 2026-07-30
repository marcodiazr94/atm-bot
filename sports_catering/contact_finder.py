"""
Busca el contacto de un equipo visitante.

Orden de búsqueda:
  1. Supabase (si está configurado): exacta o parcial.
  2. Base de datos Excel (known_contacts dict): exacta → parcial → fuzzy.
  3. Búsqueda en Internet con IA (OpenAI + web search), si se activa.
     Los resultados de IA se guardan en Supabase automáticamente.
  4. Fallback: enlace de búsqueda en Google.
"""
import difflib
import urllib.parse

from sports_catering import ai_search


def find_contact(team_name: str, known_contacts: dict = None, use_ai: bool = True,
                 city: str = "", sport: str = "") -> dict:
    """
    Intenta encontrar el contacto del equipo.
    Devuelve un dict con: nombre, email, telefono, contacto, web, status, ...
    status ∈ {found_exact, found_partial, found_fuzzy, found_ai, missing}
    """
    key = _normalize(team_name)

    # 1. Supabase (si está configurado)
    try:
        from sports_catering import db
        c = db.get_contacto_por_nombre(team_name)
        if c and (c.get("email") or c.get("telefono")):
            status = "found_exact" if _normalize(c.get("nombre", "")) == key else "found_partial"
            return {**c, "status": status}
    except RuntimeError:
        pass  # Supabase no configurado — continuar con Excel

    # 2. Coincidencia exacta en Excel
    if known_contacts:
        if key in known_contacts:
            c = known_contacts[key]
            return {**c, "status": "found_exact"}

        # 2b. Coincidencia parcial
        for k, c in known_contacts.items():
            if key in k or k in key:
                return {**c, "status": "found_partial"}

        # 2c. Fuzzy matching
        keys = list(known_contacts.keys())
        matches = difflib.get_close_matches(key, keys, n=1, cutoff=0.78)
        if matches:
            c = known_contacts[matches[0]]
            return {**c, "status": "found_fuzzy", "matched_as": c.get("nombre", matches[0])}

    # 3. Búsqueda en Internet con IA
    if use_ai:
        ai = ai_search.search_team_contact(team_name, city=city, sport=sport)
        if ai and (ai.get("email") or ai.get("telefono")):
            result = {
                "nombre":    team_name,
                "telefono":  ai.get("telefono"),
                "email":     ai.get("email"),
                "contacto":  ai.get("contacto"),
                "web":       ai.get("web"),
                "instagram": ai.get("instagram"),
                "confianza": ai.get("confianza"),
                "notas":     ai.get("notas"),
                "status":    "found_ai",
            }
            # Guardar en Supabase automáticamente (verificado=False)
            try:
                from sports_catering import db
                db.upsert_contacto({
                    **result,
                    "nombre":   team_name,
                    "fuente":   "ai",
                    "deporte":  sport or None,
                })
            except Exception:
                pass
            return result

    # 4. No encontrado → generar link de búsqueda
    query = urllib.parse.quote_plus(f"{team_name} club deportivo email contacto")
    search_url = f"https://www.google.com/search?q={query}"
    return {
        "nombre":     team_name,
        "telefono":   None,
        "email":      None,
        "contacto":   None,
        "web":        None,
        "status":     "missing",
        "search_url": search_url,
    }


def _normalize(s: str) -> str:
    return s.upper().strip().replace("  ", " ")
