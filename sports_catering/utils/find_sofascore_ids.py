"""
Utilidad de una sola ejecución para descubrir los IDs de SofaScore de cada equipo asturiano.
Ejecutar: python sports_catering/utils/find_sofascore_ids.py
Luego verificar manualmente y copiar los IDs a config.json
"""
import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
}

TEAMS_TO_SEARCH = [
    ("REAL OVIEDO", "football"),
    ("SPORTING GIJON", "football"),
    ("REAL OVIEDO FEMENINO", "football"),
    ("SPORTING FEMENINO", "football"),
    ("OVIEDO VETUSTA", "football"),
    ("REAL OVIEDO B", "football"),
    ("SPORTING GIJON B", "football"),
    ("OCB OVIEDO", "basketball"),
    ("CIRCULO GIJON", "basketball"),
    ("FODEBA GIJON", "basketball"),
    ("SIROKO GIJON", "basketball"),
    ("BALONMANO GIJON", "handball"),
    ("OVIEDO BALONMANO", "handball"),
    ("BM OVIEDO BASE", "handball"),
    ("CV OVIEDO", "volleyball"),
]

SPORT_MAP = {
    "football": 1,
    "basketball": 2,
    "handball": 6,
    "volleyball": 23,
}


def search_team(query: str, sport_name: str):
    url = f"https://api.sofascore.com/api/v1/search/all?q={requests.utils.quote(query)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ERROR buscando '{query}': {e}")
        return

    teams = data.get("teams", {}).get("hits", [])
    if not teams:
        print(f"  Sin resultados para '{query}'")
        return

    sport_id = SPORT_MAP.get(sport_name)
    filtered = [t for t in teams if t.get("entity", {}).get("sport", {}).get("id") == sport_id]
    if not filtered:
        filtered = teams[:3]

    print(f"\n🔍 '{query}' ({sport_name}):")
    for t in filtered[:4]:
        entity = t.get("entity", {})
        team_id = entity.get("id")
        name = entity.get("name", "?")
        country = entity.get("country", {}).get("name", "?")
        slug = entity.get("slug", "")
        url_check = f"https://www.sofascore.com/team/football/{slug}/{team_id}"
        print(f"  ID={team_id:>8}  {name:<40}  {country:<15}  {url_check}")


def main():
    print("=" * 80)
    print("BÚSQUEDA DE IDs SOFASCORE — ATM CATERING DEPORTIVO")
    print("Verifica cada ID en sofascore.com antes de añadirlo a config.json")
    print("=" * 80)

    for query, sport in TEAMS_TO_SEARCH:
        search_team(query, sport)
        time.sleep(1.2)

    print("\n" + "=" * 80)
    print("NOTA: BM Gijón Femenino ya tiene ID confirmado: 1106950")
    print("Para los que no aparezcan, busca manualmente en sofascore.com")
    print("=" * 80)


if __name__ == "__main__":
    main()
