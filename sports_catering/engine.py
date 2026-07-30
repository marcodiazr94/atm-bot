"""
Motor reutilizable de búsqueda de partidos-lead.

Separa la lógica de negocio (qué partidos hay que contactar) de la interfaz
(CLI en main.py o web en catering_web/). No tiene efectos secundarios:
no escribe en Excel ni imprime; solo devuelve datos.
"""
import time
import unicodedata
from datetime import datetime, timedelta

from sports_catering.scrapers import espn, feb_competiciones, feb_envivo, rfef_juvenil
from sports_catering.utils.asturias_filter import init_from_config, is_asturian


def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", (s or "").upper()).encode("ascii", "ignore").decode()


def fetch_team_matches(team: dict) -> list[dict]:
    """Descarga los partidos de un equipo según su 'source'. Sin filtros."""
    source = team.get("source", "")
    name = team["name"]

    if source == "espn":
        if not team.get("espn_id"):
            return []
        m = espn.get_team_schedule(int(team["espn_id"]), team.get("espn_league", ""))
        time.sleep(0.4)
        return m

    if source == "feb_competiciones":
        if not team.get("feb_autonomy_id") or not team.get("feb_team_id"):
            return []
        m = feb_competiciones.get_calendar(team["feb_autonomy_id"], team["feb_team_id"], name)
        time.sleep(0.8)
        return m

    if source == "feb_envivo":
        if not team.get("feb_slug"):
            return []
        m = feb_envivo.get_calendar(
            team["feb_slug"], team.get("feb_group", 2),
            team.get("feb_season_year", datetime.now().year),
            team.get("feb_team_keyword", name),
        )
        time.sleep(0.8)
        return m

    if source == "rfef_juvenil":
        if not team.get("rfef_url"):
            return []
        m = rfef_juvenil.get_calendar(team["rfef_url"], team.get("rfef_team_keyword", name))
        time.sleep(0.8)
        return m

    return []  # 'manual' u otras fuentes no automatizadas


def _hora_float(dt: datetime):
    return dt.hour + dt.minute / 60 if isinstance(dt, datetime) else None


def _enrich(raw: dict, team: dict) -> dict:
    return {
        **raw,
        "equipo": team["name"],
        "ciudad": team["city"],
        "deporte": team["sport"],
        "lugar": team.get("venue", ""),
        "hora": _hora_float(raw.get("date")),
        "rival": raw.get("away_team", ""),
    }


def cargar_temporada_completa(teams: list[dict],
                              on_progress=None) -> tuple[list[dict], list[dict]]:
    """
    Descarga TODOS los partidos en casa de la temporada para equipos automáticos,
    sin filtro de fecha.

    Devuelve (partidos, equipos_manuales).
    on_progress(nombre_equipo, i, total): callback opcional.
    """
    init_from_config(teams)
    partidos: list[dict] = []

    auto_teams = [t for t in teams if t.get("source") not in ("manual", "", None)]
    manual = [t for t in teams if t.get("source") == "manual"]
    total = len(auto_teams)

    for i, team in enumerate(auto_teams):
        if on_progress:
            on_progress(team["name"], i, total)
        try:
            raw_matches = fetch_team_matches(team)
        except Exception:
            raw_matches = []

        for m in raw_matches:
            m_date = m.get("date")
            if not isinstance(m_date, datetime):
                continue

            home = _norm(m.get("home_team", ""))
            tname = _norm(team["name"])
            kw = _norm(team.get("feb_team_keyword") or team.get("rfef_team_keyword") or "")
            if not (tname in home or home in tname or (kw and (kw in home or home in kw))):
                continue

            if is_asturian(m.get("away_team", "")):
                continue

            partidos.append(_enrich(m, team))

    partidos.sort(key=lambda x: (x["date"].replace(tzinfo=None) if x["date"].tzinfo else x["date"]))
    return partidos, manual


def buscar_partidos_casa(teams: list[dict], window_start: datetime, window_end: datetime,
                         on_progress=None) -> tuple[list[dict], list[dict]]:
    """
    Devuelve (leads, equipos_manuales): partidos en casa dentro de la ventana de fechas.
    on_progress(nombre_equipo, i, total): callback opcional para barra de progreso.
    """
    all_partidos, manual = cargar_temporada_completa(teams, on_progress)

    leads = []
    for m in all_partidos:
        m_naive = m["date"].replace(tzinfo=None) if m["date"].tzinfo else m["date"]
        if window_start <= m_naive <= window_end:
            leads.append(m)

    return leads, manual


def leads_demo(now: datetime = None) -> list[dict]:
    """Partidos de ejemplo para ver la interfaz cuando la temporada está parada."""
    now = now or datetime.now()
    base = now + timedelta(days=16)
    return [
        {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
         "lugar": "CARLOS TARTIERE", "rival": "CD LUGO",
         "date": base.replace(hour=18, minute=30), "hora": 18.5,
         "home_team": "Real Oviedo", "away_team": "CD Lugo"},
        {"equipo": "OCB", "ciudad": "OVIEDO", "deporte": "BALONCESTO",
         "lugar": "PALACIO DEPORTES", "rival": "CB BREOGAN",
         "date": base.replace(hour=12, minute=0), "hora": 12.0,
         "home_team": "Oviedo Baloncesto", "away_team": "CB Breogán"},
        {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
         "lugar": "EL MOLINON", "rival": "REAL RACING CLUB",
         "date": (base + timedelta(days=1)).replace(hour=16, minute=15), "hora": 16.25,
         "home_team": "Sporting Gijón", "away_team": "Real Racing Club de Santander"},
    ]
