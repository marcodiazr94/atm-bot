"""
Cliente Supabase para ATM Catering Deportivo.

Lee SUPABASE_URL y SUPABASE_KEY del entorno (o .env).
Si no están configurados, las funciones lanzan RuntimeError descriptivo.
"""
import os
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key or url.startswith("https://xxx"):
        raise RuntimeError(
            "Falta SUPABASE_URL o SUPABASE_KEY en el .env. "
            "Crea el proyecto en supabase.com y añade las variables."
        )
    from supabase import create_client
    return create_client(url, key)


def _to_filter_str(dt) -> str:
    """Convierte datetime a string ISO UTC que acepta el cliente Supabase."""
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(dt)


def _to_iso(dt) -> str | None:
    if not dt:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return None


# ── Partidos ──────────────────────────────────────────────────────────────────

def upsert_partidos(partidos: list[dict]) -> int:
    """
    Inserta o actualiza partidos en Supabase.
    Devuelve el número de filas procesadas.
    """
    if not partidos:
        return 0
    client = _get_client()
    rows = []
    for p in partidos:
        fecha = p.get("fecha") or p.get("date")
        rows.append({
            "equipo":    p.get("equipo", ""),
            "ciudad":    p.get("ciudad", ""),
            "deporte":   p.get("deporte", ""),
            "rival":     p.get("rival", ""),
            "fecha":     _to_iso(fecha),
            "hora":      p.get("hora"),
            "lugar":     p.get("lugar", "") or "",
            "source":    p.get("source", "") or "",
            "temporada": p.get("temporada", "") or "",
            "jornada":   p.get("jornada"),
        })
    client.table("partidos").upsert(rows, on_conflict="equipo,rival,fecha").execute()
    return len(rows)


def get_partidos(ciudad: str = None, deporte: str = None, solo_proximos: bool = False,
                 fecha_desde: datetime = None, fecha_hasta: datetime = None) -> list[dict]:
    """Devuelve partidos de Supabase ordenados por fecha con filtros opcionales."""
    client = _get_client()
    q = client.table("partidos").select("*").order("fecha")
    if ciudad:
        q = q.eq("ciudad", ciudad.upper())
    if deporte:
        q = q.eq("deporte", deporte.upper())
    if solo_proximos:
        q = q.gte("fecha", datetime.now(timezone.utc).isoformat())
    if fecha_desde:
        q = q.gte("fecha", _to_filter_str(fecha_desde))
    if fecha_hasta:
        q = q.lte("fecha", _to_filter_str(fecha_hasta))
    resp = q.execute()
    return resp.data or []


# ── Contactos ─────────────────────────────────────────────────────────────────

def get_contactos(verificado: bool = None, q: str = None) -> list[dict]:
    """Devuelve contactos con filtros opcionales, ordenados por nombre."""
    client = _get_client()
    query = client.table("contactos").select("*").order("nombre")
    if verificado is not None:
        query = query.eq("verificado", verificado)
    if q:
        query = query.ilike("nombre", f"%{q.upper()}%")
    resp = query.execute()
    return resp.data or []


def upsert_contacto(contacto: dict) -> dict:
    """
    Inserta o actualiza un contacto por nombre (normalizado a mayúsculas).
    Devuelve el registro resultante.
    """
    client = _get_client()
    nombre = (contacto.get("nombre") or "").upper().strip()
    if not nombre:
        raise ValueError("El contacto debe tener nombre.")

    # emails_extra: lista de emails adicionales además del principal
    emails_raw = contacto.get("emails") or []
    emails_extra = None
    if isinstance(emails_raw, list) and len(emails_raw) > 1:
        emails_extra = ",".join(emails_raw[1:])

    row = {
        "nombre":                   nombre,
        "deporte":                  contacto.get("deporte") or None,
        "email":                    contacto.get("email") or None,
        "emails_extra":             emails_extra,
        "telefono":                 contacto.get("telefono") or None,
        "contacto":                 contacto.get("contacto") or None,
        "web":                      contacto.get("web") or None,
        "instagram":                contacto.get("instagram") or contacto.get("instagram_club") or None,
        "verificado":               bool(contacto.get("verificado", False)),
        "fuente":                   contacto.get("fuente") or "manual",
        "confianza":                contacto.get("confianza") or None,
        "notas":                    contacto.get("notas") or None,
        "nutricionista":            contacto.get("nutricionista_nombre") or None,
        "nutricionista_email":      contacto.get("nutricionista_email") or None,
        "nutricionista_instagram":  contacto.get("nutricionista_instagram") or None,
        "ultima_actualizacion":     datetime.now(timezone.utc).isoformat(),
    }
    resp = client.table("contactos").upsert(row, on_conflict="nombre").execute()
    return resp.data[0] if resp.data else row


def marcar_verificado(nombre: str, verificado: bool = True):
    """Actualiza el campo verificado de un contacto por nombre."""
    client = _get_client()
    client.table("contactos").update({
        "verificado": verificado,
        "ultima_actualizacion": datetime.now(timezone.utc).isoformat(),
    }).eq("nombre", nombre.upper().strip()).execute()


def delete_contacto(nombre: str):
    """Elimina un contacto por nombre."""
    client = _get_client()
    client.table("contactos").delete().eq("nombre", nombre.upper().strip()).execute()


def _norm(s: str) -> str:
    """Normaliza a mayúsculas sin acentos para comparaciones tolerantes."""
    import unicodedata
    return unicodedata.normalize("NFD", s.upper().strip()).encode("ascii", "ignore").decode()


def get_contacto_por_nombre(nombre: str) -> dict | None:
    """
    Busca un contacto en Supabase con tolerancia a tildes y variaciones de nombre.
    Orden: exacto → ILIKE → fuzzy en Python (difflib sobre todos los contactos).
    """
    if not nombre:
        return None
    client = _get_client()
    key = nombre.upper().strip()

    resp = client.table("contactos").select("*").eq("nombre", key).limit(1).execute()
    if resp.data:
        return resp.data[0]

    resp = client.table("contactos").select("*").ilike("nombre", f"%{key}%").limit(1).execute()
    if resp.data:
        return resp.data[0]

    # Fuzzy matching en Python con normalización de acentos
    import difflib
    todos = (client.table("contactos").select("id,nombre").execute().data or [])
    if not todos:
        return None
    key_norm = _norm(nombre)
    candidatos = {c["nombre"]: _norm(c["nombre"]) for c in todos}
    matches = difflib.get_close_matches(key_norm, list(candidatos.values()), n=1, cutoff=0.72)
    if matches:
        nombre_orig = next(n for n, v in candidatos.items() if v == matches[0])
        resp = client.table("contactos").select("*").eq("nombre", nombre_orig).limit(1).execute()
        if resp.data:
            return resp.data[0]
    return None
