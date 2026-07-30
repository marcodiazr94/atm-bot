"""
Scraper para competiciones.feb.es (ligas autonómicas de baloncesto).
Usado para equipos en ligas federativas regionales.
URL patrón: https://competiciones.feb.es/autonomicas/Calendarios.aspx?a={autonomy_id}&c={team_id}&med=0
"""
import re
import requests
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Formato de texto en la tabla: "HOME - AWAY SCORE\nFECHA HORA"
# Para partidos sin jugar: "HOME - AWAY\nFECHA HORA" (sin score)
MATCH_PATTERN = re.compile(
    r"([A-ZÁÉÍÓÚÑÜ][^-\n]{2,60}?)\s*-\s*([A-ZÁÉÍÓÚÑÜ][^\n\d]{2,60?}?)\s*(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2})",
    re.IGNORECASE,
)


def get_calendar(autonomy_id: str, team_id: str, target_team_name: str) -> list[dict]:
    """
    Descarga y parsea el calendario de una URL de competiciones.feb.es.
    Devuelve los partidos donde target_team_name juega en casa.
    """
    url = f"https://competiciones.feb.es/autonomicas/Calendarios.aspx?a={autonomy_id}&c={team_id}&med=0"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"  [FEB] Error descargando {url}: {e}")
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "lxml")

    # El calendario está en el texto de la primera celda grande de la tabla
    full_text = soup.get_text(" ", strip=True)

    matches = _parse_feb_calendar_text(full_text, target_team_name)
    return matches


def _parse_feb_calendar_text(text: str, target_team: str) -> list[dict]:
    """
    Parsea el texto plano de un calendario FEB.
    Formato: "HOME - AWAY [SCORE] FECHA HORA"
    El score puede ser "XX-XX" para jugados o ausente para futuros.
    """
    matches = []
    target_upper = target_team.upper().strip()

    # Dividir por fechas de partido (dd/mm/yyyy)
    date_re = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})")
    # Buscar todas las secuencias "EQUIPO A - EQUIPO B [SCORE] FECHA HORA"
    block_re = re.compile(
        r"([A-ZÁÉÍÓÚÑÜÀÈÌÒÙ\w][A-ZÁÉÍÓÚÑÜÀÈÌÒÙ\w\s.,\'()-]{3,60}?)"
        r"\s*-\s*"
        r"([A-ZÁÉÍÓÚÑÜÀÈÌÒÙ\w][A-ZÁÉÍÓÚÑÜÀÈÌÒÙ\w\s.,\'()-]{3,60?}?)"
        r"(?:\s+\d{1,3}-\d{1,3})?"  # score opcional
        r"\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})",
        re.IGNORECASE,
    )

    for m in block_re.finditer(text):
        home_raw = m.group(1).strip()
        away_raw = m.group(2).strip()
        date_raw = m.group(3)
        time_raw = m.group(4)

        # Solo interesa cuando el equipo asturiano juega en casa
        if target_upper not in home_raw.upper():
            continue

        try:
            date = datetime.strptime(f"{date_raw} {time_raw}", "%d/%m/%Y %H:%M")
        except ValueError:
            continue

        matches.append({
            "date": date,
            "home_team": home_raw,
            "away_team": away_raw,
            "league": "FEB-Autonomica",
            "source": "feb_competiciones",
        })

    return matches
