"""
Importa el calendario de Segunda División 2026-27 a Supabase.
Datos extraídos del Excel oficial. Solo partidos en casa de Real Oviedo y Sporting Gijón.

Uso:
    python importar_segunda_2627.py
    python importar_segunda_2627.py --dry-run
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sports_catering import db

# 42 partidos en casa (21 Oviedo + 21 Sporting), temporada 2026-27
PARTIDOS = [
    # ── REAL OVIEDO (local) ─────────────────────────────────────────────
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "GRANADA",          "fecha": "2026-08-16", "jornada": 1},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "LEGANÉS",          "fecha": "2026-08-23", "jornada": 2},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "BURGOS",           "fecha": "2026-09-06", "jornada": 4},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "SPORTING GIJÓN",   "fecha": "2026-09-27", "jornada": 7},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "EIBAR",            "fecha": "2026-10-11", "jornada": 9},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "LAS PALMAS",       "fecha": "2026-11-01", "jornada": 12},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "GIRONA",           "fecha": "2026-11-15", "jornada": 14},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "CELTA FORTUNA",    "fecha": "2026-11-29", "jornada": 16},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "REAL SOCIEDAD B",  "fecha": "2026-12-13", "jornada": 18},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "CASTELLÓN",        "fecha": "2027-01-03", "jornada": 20},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "ALMERÍA",          "fecha": "2027-01-17", "jornada": 22},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "CÁDIZ",            "fecha": "2027-01-31", "jornada": 24},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "SABADELL",         "fecha": "2027-02-14", "jornada": 26},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "TENERIFE",         "fecha": "2027-02-28", "jornada": 28},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "CÓRDOBA",          "fecha": "2027-03-14", "jornada": 30},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "VALLADOLID",       "fecha": "2027-03-28", "jornada": 32},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "ELDENSE",          "fecha": "2027-04-11", "jornada": 34},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "ALBACETE",         "fecha": "2027-05-02", "jornada": 37},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "CEUTA",            "fecha": "2027-05-16", "jornada": 39},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "MALLORCA",         "fecha": "2027-05-23", "jornada": 40},
    {"equipo": "REAL OVIEDO", "ciudad": "OVIEDO", "deporte": "FUTBOL",
     "rival": "ANDORRA",          "fecha": "2027-06-06", "jornada": 42},

    # ── SPORTING GIJÓN (local) ──────────────────────────────────────────
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "SABADELL",         "fecha": "2026-08-16", "jornada": 1},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "BURGOS",           "fecha": "2026-08-23", "jornada": 2},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "GIRONA",           "fecha": "2026-09-06", "jornada": 4},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "ELDENSE",          "fecha": "2026-09-13", "jornada": 5},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "CELTA FORTUNA",    "fecha": "2026-10-04", "jornada": 8},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "ALBACETE",         "fecha": "2026-10-18", "jornada": 10},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "VALLADOLID",       "fecha": "2026-11-08", "jornada": 13},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "LAS PALMAS",       "fecha": "2026-11-22", "jornada": 15},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "GRANADA",          "fecha": "2026-12-06", "jornada": 17},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "LEGANÉS",          "fecha": "2026-12-20", "jornada": 19},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "CÓRDOBA",          "fecha": "2027-01-10", "jornada": 21},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "CASTELLÓN",        "fecha": "2027-01-24", "jornada": 23},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "CEUTA",            "fecha": "2027-02-07", "jornada": 25},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "ANDORRA",          "fecha": "2027-02-21", "jornada": 27},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "CÁDIZ",            "fecha": "2027-03-07", "jornada": 29},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "MALLORCA",         "fecha": "2027-03-21", "jornada": 31},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "TENERIFE",         "fecha": "2027-04-04", "jornada": 33},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "REAL SOCIEDAD B",  "fecha": "2027-04-11", "jornada": 34},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "REAL OVIEDO",      "fecha": "2027-04-25", "jornada": 36},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "EIBAR",            "fecha": "2027-05-16", "jornada": 39},
    {"equipo": "SPORTING GIJON", "ciudad": "GIJON", "deporte": "FUTBOL",
     "rival": "ALMERÍA",          "fecha": "2027-05-30", "jornada": 41},
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    oviedo   = [p for p in PARTIDOS if p["equipo"] == "REAL OVIEDO"]
    sporting = [p for p in PARTIDOS if p["equipo"] == "SPORTING GIJON"]
    print(f"Segunda División 2026-27 — Oviedo: {len(oviedo)} | Sporting: {len(sporting)} | Total: {len(PARTIDOS)}\n")

    rows = []
    for p in PARTIDOS:
        fecha_dt = datetime.strptime(p["fecha"], "%Y-%m-%d").replace(
            hour=12, tzinfo=timezone.utc
        )
        rows.append({
            **p,
            "fecha":     fecha_dt,
            "lugar":     "CARLOS TARTIERE" if p["equipo"] == "REAL OVIEDO" else "EL MOLINON",
            "source":    "manual_import",
            "temporada": "2026-27",
        })

    if args.dry_run:
        for r in rows:
            print(f"  J{r['jornada']:02d} {r['fecha'].strftime('%d/%m/%Y')}  {r['equipo']} vs {r['rival']}")
        print(f"\n[DRY RUN] {len(rows)} partidos — no se ha escrito nada.")
        return

    print("Insertando en Supabase...")
    try:
        saved = db.upsert_partidos(rows)
        print(f"\n✓ {saved} partidos guardados correctamente.")
    except RuntimeError as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
