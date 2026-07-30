"""
Scraper para baloncestoenvivo.feb.es (competiciones nacionales FEB).
Navega por jornadas usando POST requests con ASP.NET ViewState.
URL patrón: https://baloncestoenvivo.feb.es/resultados/{competition}/{type}/{year}
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _get_viewstate(soup: BeautifulSoup) -> dict:
    """Extrae campos hidden de ASP.NET para POST requests."""
    fields = {}
    for name in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION", "__EVENTTARGET", "__EVENTARGUMENT"]:
        el = soup.find("input", {"name": name})
        if el:
            fields[name] = el.get("value", "")
    return fields


def _get_jornada_options(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Devuelve lista de (value, label) de las jornadas disponibles."""
    sel = soup.find("select", {"id": lambda x: x and "jornadas" in x.lower()})
    if not sel:
        return []
    return [(opt.get("value", ""), opt.get_text(strip=True)) for opt in sel.find_all("option")]


def _parse_matches_from_table(soup: BeautifulSoup, target_team: str) -> list[dict]:
    """Extrae partidos de las tablas HTML. Devuelve solo los del equipo objetivo."""
    matches = []
    target_upper = target_team.upper()

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows[1:]:  # skip header
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) < 3:
                continue
            # Cols: Equipos | Resultado | Fecha | Hora
            equipos = cols[0]
            resultado = cols[1] if len(cols) > 1 else ""
            fecha_str = cols[2] if len(cols) > 2 else ""
            hora_str = cols[3] if len(cols) > 3 else "18:00"

            # Separar equipos: "HOME-AWAY" o "HOME - AWAY"
            sep = " - " if " - " in equipos else "-"
            parts = equipos.split(sep, 1)
            if len(parts) != 2:
                continue
            home, away = parts[0].strip(), parts[1].strip()

            # Saltar partidos ya jugados (tienen score tipo "85-72")
            if resultado and resultado != "*-*" and "-" in resultado:
                try:
                    s1, s2 = resultado.split("-")
                    if s1.strip().isdigit() and s2.strip().isdigit():
                        continue  # ya jugado
                except Exception:
                    pass

            # Filtrar por equipo objetivo en casa
            if target_upper not in home.upper():
                continue

            try:
                date = datetime.strptime(f"{fecha_str} {hora_str}", "%d/%m/%Y %H:%M")
            except ValueError:
                continue

            matches.append({
                "date": date,
                "home_team": home,
                "away_team": away,
                "league": "FEB-Nacional",
                "source": "feb_envivo",
            })
    return matches


def get_calendar(competition_slug: str, group_type: int, season_year: int, target_team: str) -> list[dict]:
    """
    Descarga el calendario completo navegando por jornadas.
    competition_slug: p.ej. "segundafeb", "lebplata"
    group_type: número de grupo (normalmente 2)
    season_year: p.ej. 2025
    target_team: nombre del equipo asturiano a filtrar
    """
    base_url = f"https://baloncestoenvivo.feb.es/resultados/{competition_slug}/{group_type}/{season_year}"
    try:
        r = requests.get(base_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"  [FEB-EnVivo] Error cargando {base_url}: {e}")
        return []

    soup = BeautifulSoup(r.text, "lxml")
    all_matches = []

    # Parsear la jornada actual
    all_matches.extend(_parse_matches_from_table(soup, target_team))

    # Obtener lista de jornadas futuras y navegar por ellas
    jornadas = _get_jornada_options(soup)
    viewstate = _get_viewstate(soup)
    if not jornadas:
        return all_matches

    # Nombre del select de jornadas
    sel = soup.find("select", {"id": lambda x: x and "jornadas" in x.lower()})
    sel_name = sel.get("name", "") if sel else ""

    for value, label in jornadas[1:]:  # saltar la primera (ya procesada)
        post_data = dict(viewstate)
        post_data["__EVENTTARGET"] = sel_name
        post_data["__EVENTARGUMENT"] = ""
        post_data[sel_name] = value

        try:
            r2 = requests.post(base_url, data=post_data, headers=HEADERS, timeout=15)
            r2.raise_for_status()
        except Exception:
            continue

        soup2 = BeautifulSoup(r2.text, "lxml")
        all_matches.extend(_parse_matches_from_table(soup2, target_team))
        viewstate = _get_viewstate(soup2)

    return all_matches
