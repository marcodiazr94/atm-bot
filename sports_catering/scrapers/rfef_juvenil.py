"""
Scraper para rfef.es — División de Honor Juvenil (y otras categorías juveniles).

Navega por todas las jornadas de la temporada vía POST y extrae
partidos de casa para el equipo objetivo.

URL base resultados: https://rfef.es/es/resultados?competition=23289323&group=23289324
"""
import time
import unicodedata
import re
from datetime import datetime

try:
    import cloudscraper
    def _make_session():
        return cloudscraper.create_scraper()
except ImportError:
    import requests
    def _make_session():
        s = requests.Session()
        s.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        return s

from bs4 import BeautifulSoup

# IDs fijos para División de Honor Juvenil temporada 2025-26
_SEASON_ID      = "21"       # 2025-2026
_COMPETITION_ID = "23289323" # División de Honor Juvenil
_FORM_ID        = "novanet_search"
_RESULTS_URL    = "https://rfef.es/es/resultados"

# Mapa grupo → group_id (Grupo 1 contiene los equipos asturianos)
_GROUP_IDS = {
    1: "23289324", 2: "23289325", 3: "23289326", 4: "23289327",
    5: "23289328", 6: "23289329", 7: "23289330",
}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s.upper()).encode("ascii", "ignore").decode()


def _parse_match_cards(soup: BeautifulSoup) -> list[dict]:
    """Extrae partidos de las tarjetas HTML de una jornada."""
    matches = []
    for card in soup.find_all("div", class_=lambda c: c and "align-items-stretch" in c and "row" in c):
        # Fecha y hora
        clock = card.find("i", class_=lambda c: c and "fa-clock" in c)
        if not clock:
            continue
        date_text = clock.parent.get_text(strip=True).replace(" - ", " ")
        try:
            match_date = datetime.strptime(date_text, "%d/%m/%Y %H:%M")
        except ValueError:
            continue

        # Venue
        marker = card.find("i", class_=lambda c: c and "fa-map-marker" in c)
        venue = marker.parent.get_text(strip=True) if marker and marker.parent else ""

        # Equipos: local en col-md-5 con text-center font-weight-bold
        #          visitante en col-md-5 con font-weight-bold text-md-right
        home_div = card.find("div", class_=lambda c: c and "text-center" in c and "font-weight-bold" in c)
        away_div = card.find("div", class_=lambda c: c and "text-md-right" in c and "font-weight-bold" in c)

        if not home_div or not away_div:
            continue
        home = home_div.get_text(strip=True)
        away = away_div.get_text(strip=True)
        if not home or not away:
            continue

        matches.append({
            "date": match_date,
            "home_team": home,
            "away_team": away,
            "venue_name": venue,
            "league": "División Honor Juvenil",
            "source": "rfef_juvenil",
        })
    return matches


def _find_group_for_team(session, target_norm: str) -> tuple[str, int]:
    """
    Busca en los 7 grupos cuál contiene el equipo objetivo.
    Devuelve (group_id, total_jornadas).
    """
    for group_num, group_id in _GROUP_IDS.items():
        params = {"competition": _COMPETITION_ID, "group": group_id}
        try:
            r = session.get(_RESULTS_URL, params=params, timeout=20)
            r.raise_for_status()
        except Exception:
            continue

        soup = BeautifulSoup(r.text, "lxml")
        # Obtener form_build_id y nº de jornadas disponibles
        build_id = ""
        bid_input = soup.find("input", {"name": "form_build_id"})
        if bid_input:
            build_id = bid_input.get("value", "")

        journey_sel = soup.find("select", {"name": "journey"})
        journey_opts = journey_sel.find_all("option") if journey_sel else []
        total_jornadas = sum(1 for o in journey_opts if o.get("value", "") not in ("_none", ""))

        # Comprobar si el equipo está en esta jornada
        cards = _parse_match_cards(soup)
        team_found = any(
            target_norm in _norm(m["home_team"]) or target_norm in _norm(m["away_team"])
            for m in cards
        )
        if team_found:
            return group_id, total_jornadas, build_id

        time.sleep(0.5)

    return None, 0, ""


def get_calendar(competition_url: str, target_team: str) -> list[dict]:
    """
    Descarga todos los partidos de la temporada para el equipo objetivo.

    competition_url: URL de la competición (se usa para extraer competition y group IDs)
                     o la URL de resultados directamente.
    target_team: keyword del equipo (p.ej. "OVIEDO", "SPORTING", "ROCES")
    """
    session = _make_session()
    target_norm = _norm(target_team)

    # Encontrar el grupo correcto
    group_id, total_jornadas, build_id = _find_group_for_team(session, target_norm)

    if not group_id:
        print(f"  [RFEF] No se encontró '{target_team}' en ningún grupo")
        return []

    if total_jornadas == 0:
        total_jornadas = 30  # fallback

    base_url = f"{_RESULTS_URL}?competition={_COMPETITION_ID}&group={group_id}"
    all_matches = []
    seen = set()

    for jornada in range(1, total_jornadas + 1):
        post_data = {
            "form_build_id": build_id,
            "form_id": _FORM_ID,
            "season": _SEASON_ID,
            "competition": _COMPETITION_ID,
            "group": group_id,
            "journey": str(jornada),
        }
        try:
            r = session.post(base_url, data=post_data, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  [RFEF] Error jornada {jornada}: {e}")
            continue

        soup = BeautifulSoup(r.text, "lxml")

        # Actualizar form_build_id para siguiente petición
        bid = soup.find("input", {"name": "form_build_id"})
        if bid:
            build_id = bid.get("value", build_id)

        cards = _parse_match_cards(soup)
        for m in cards:
            key = (m["home_team"], m["away_team"], m["date"])
            if key not in seen:
                seen.add(key)
                all_matches.append(m)

        time.sleep(0.4)

    return all_matches
