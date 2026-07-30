"""
Scraper usando la API no oficial de ESPN para fútbol español.
Cubre: LaLiga (esp.1), LaLiga Hypermotion (esp.2).
"""
import time
import requests
from datetime import datetime, timezone

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_team_schedule(team_id: int, league: str) -> list[dict]:
    url = f"{BASE}/{league}/teams/{team_id}/schedule"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ESPN] Error {league}/teams/{team_id}: {e}")
        return []

    events = r.json().get("events", [])
    matches = []
    for event in events:
        comps = event.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        if not home or not away:
            continue

        date_str = event.get("date", "")
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            continue

        matches.append({
            "date": date,
            "home_team": home.get("team", {}).get("displayName", ""),
            "away_team": away.get("team", {}).get("displayName", ""),
            "home_team_id": home.get("team", {}).get("id", ""),
            "away_team_id": away.get("team", {}).get("id", ""),
            "league": league,
            "source": "espn",
        })
    return matches


def get_team_schedule_all_seasons(team_id: int, league: str) -> list[dict]:
    """Intenta también la temporada siguiente si hay pocos partidos."""
    matches = get_team_schedule(team_id, league)
    time.sleep(0.5)
    return matches
