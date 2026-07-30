"""Detecta si un equipo visitante es asturiano (para excluirlo como lead)."""
import difflib

# Nombres conocidos de equipos asturianos (normalizado)
_ASTURIAN_TEAMS: set[str] = set()

# Palabras clave que identifican equipos asturianos
_ASTURIAN_KEYWORDS = {
    "OVIEDO", "GIJÓN", "GIJON", "ASTURIAS", "SPORTING", "VETUSTA",
    "REQUEXON", "COLLOTO", "AVILÉS", "AVILES", "VILLAFRÚA", "MAREO",
    "TELECABLE", "BALONMANO GIJÓN", "BALONMANO GIJON", "SIROKO",
    "FODEBA", "CIRCULO GIJON", "OCB", "TSK ROCES", "LOBAS GLOBAL ATAC",
}


def init_from_config(teams: list[dict]):
    """Carga los nombres de equipos asturianos desde config para uso en filtrado."""
    global _ASTURIAN_TEAMS
    _ASTURIAN_TEAMS = {t["name"].upper().strip() for t in teams}


def is_asturian(team_name: str) -> bool:
    """
    Devuelve True si el equipo es asturiano y por tanto NO es un lead.
    Usa coincidencia exacta, luego keywords, luego fuzzy.
    """
    name = team_name.upper().strip()

    # Coincidencia exacta con equipos conocidos
    if name in _ASTURIAN_TEAMS:
        return True

    # Coincidencia fuzzy con equipos conocidos
    if _ASTURIAN_TEAMS:
        matches = difflib.get_close_matches(name, _ASTURIAN_TEAMS, n=1, cutoff=0.80)
        if matches:
            return True

    # Coincidencia por keywords
    for kw in _ASTURIAN_KEYWORDS:
        if kw in name:
            return True

    return False
