"""
ATM Catering Deportivo — Script semanal de automatización.

Uso:
    python sports_catering/main.py [--window-start DIAS] [--window-end DIAS] [--dry-run]

Por defecto busca partidos en casa entre hoy+14 y hoy+21 dias.
"""
import argparse
import sys
import time
import unicodedata
import webbrowser

# Forzar UTF-8 en consola Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timedelta, timezone

from sports_catering.config import load_config
from sports_catering.contact_finder import find_contact
from sports_catering.excel_manager import (
    append_contact_row,
    append_match_row,
    load_existing_matches,
    load_known_contacts,
    load_workbook,
    match_already_registered,
    save_workbook,
)
from sports_catering.html_report import generate_report
from sports_catering.scrapers import espn, feb_competiciones, feb_envivo
from sports_catering.utils.asturias_filter import init_from_config, is_asturian


def fetch_matches_for_team(team: dict) -> list[dict]:
    """Dispatch al scraper correcto según el campo 'source' del equipo."""
    source = team.get("source", "")
    name = team["name"]

    if source == "espn":
        team_id = team.get("espn_id")
        league = team.get("espn_league", "")
        if not team_id:
            print(f"  [SKIP] {name}: sin espn_id en config.json")
            return []
        matches = espn.get_team_schedule(int(team_id), league)
        time.sleep(0.5)
        return matches

    elif source == "feb_competiciones":
        autonomy_id = team.get("feb_autonomy_id")
        comp_id = team.get("feb_team_id")
        if not autonomy_id or not comp_id:
            print(f"  [SKIP] {name}: sin feb_autonomy_id/feb_team_id en config.json")
            return []
        matches = feb_competiciones.get_calendar(autonomy_id, comp_id, name)
        time.sleep(1)
        return matches

    elif source == "feb_envivo":
        slug = team.get("feb_slug", "")
        group = team.get("feb_group", 2)
        year = team.get("feb_season_year", datetime.now().year)
        if not slug:
            print(f"  [SKIP] {name}: sin feb_slug en config.json")
            return []
        matches = feb_envivo.get_calendar(slug, group, year, name)
        time.sleep(1)
        return matches

    elif source == "manual":
        print(f"  [MANUAL] {name}: verificar manualmente en {team.get('manual_url','')}")
        return []

    else:
        print(f"  [SKIP] {name}: fuente '{source}' no reconocida")
        return []


def _hora_to_float(dt: datetime) -> float:
    """Convierte hora de datetime a float (ej. 18:30 → 18.5)."""
    return dt.hour + dt.minute / 60


def _enrich_match(raw_match: dict, team_config: dict) -> dict:
    """Añade metadatos del equipo local al partido encontrado."""
    return {
        **raw_match,
        "equipo": team_config["name"],
        "ciudad": team_config["city"],
        "deporte": team_config["sport"],
        "lugar": team_config.get("venue", ""),
        "hora": _hora_to_float(raw_match["date"]) if isinstance(raw_match.get("date"), datetime) else None,
    }


def run(args):
    config = load_config()
    teams = config["teams"]
    excel_path = config["excel_path"]
    output_dir = config.get("report_output_dir", ".")
    window_start_days = args.window_start or config.get("lead_window_days", [14, 21])[0]
    window_end_days = args.window_end or config.get("lead_window_days", [14, 21])[1]

    now = datetime.now()
    window_start = now + timedelta(days=window_start_days)
    window_end = now + timedelta(days=window_end_days)

    print(f"\n{'='*60}")
    print(f"ATM CATERING DEPORTIVO — {now.strftime('%d/%m/%Y %H:%M')}")
    print(f"Buscando partidos entre {window_start.strftime('%d/%m/%Y')} y {window_end.strftime('%d/%m/%Y')}")
    print(f"{'='*60}\n")

    # Inicializar filtro de equipos asturianos
    init_from_config(teams)

    # Cargar datos existentes del Excel
    print("📂 Cargando Excel...")
    try:
        wb = load_workbook(excel_path)
        existing_matches = load_existing_matches(wb)
        known_contacts = load_known_contacts(wb)
        print(f"  {len(existing_matches)} partidos existentes, {len(known_contacts)} contactos en base de datos\n")
    except Exception as e:
        print(f"  ERROR abriendo Excel: {e}")
        print("  Asegúrate de que el archivo no está abierto en Excel.")
        sys.exit(1)

    # Obtener partidos de todas las fuentes
    all_home_matches = []
    manual_teams = []

    for team in teams:
        source = team.get("source", "")
        if source == "manual":
            manual_teams.append(team)
            continue

        print(f"🔍 {team['name']} ({team['sport']}, {source})...")
        try:
            raw_matches = fetch_matches_for_team(team)
        except Exception as e:
            print(f"  ERROR: {e}")
            raw_matches = []

        # Filtrar: solo partidos en casa dentro de la ventana
        for m in raw_matches:
            m_date = m.get("date")
            if not isinstance(m_date, datetime):
                continue

            # Quitar timezone para comparar
            m_date_naive = m_date.replace(tzinfo=None) if m_date.tzinfo else m_date

            if not (window_start <= m_date_naive <= window_end):
                continue

            # El equipo asturiano debe ser el local
            def _norm(s):
                return unicodedata.normalize("NFD", s.upper()).encode("ascii", "ignore").decode()
            home = _norm(m.get("home_team", ""))
            tname = _norm(team["name"])
            if tname not in home and home not in tname:
                continue

            away = m.get("away_team", "")
            if is_asturian(away):
                continue  # visitante también asturiano → no es lead

            enriched = _enrich_match(m, team)
            enriched["rival"] = away
            all_home_matches.append(enriched)

        if raw_matches:
            home_in_window = len([m for m in all_home_matches if m.get("equipo") == team["name"]])
            print(f"  {len(raw_matches)} partidos obtenidos → {home_in_window} en casa en la ventana\n")
        else:
            print(f"  Sin datos\n")

    # Deduplicar contra REGISTRO existente
    new_leads = []
    for m in all_home_matches:
        if match_already_registered(m["rival"], m["date"].replace(tzinfo=None), m["equipo"], existing_matches):
            print(f"  [DUP] {m['equipo']} vs {m['rival']} ({m['date'].strftime('%d/%m/%Y')}) — ya en REGISTRO")
            continue
        new_leads.append(m)

    print(f"\n{'='*60}")
    print(f"📊 RESUMEN: {len(new_leads)} partidos nuevos a contactar")
    print(f"{'='*60}\n")

    if not new_leads:
        print("✅ No hay partidos nuevos en la ventana. El Excel no se modificará.")
        if manual_teams:
            _print_manual_section(manual_teams)
        return

    # Enriquecer con contactos
    use_ai = not args.no_ai
    if use_ai:
        print("🌐 Buscando contactos (base de datos → IA/web)...")
    new_contacts = []  # contactos encontrados por IA, para cachear en la base de datos
    for m in new_leads:
        contact = find_contact(
            m["rival"], known_contacts, use_ai=use_ai,
            city=m.get("ciudad", ""), sport=m.get("deporte", ""),
        )
        m.update(contact)
        status = contact.get("status", "missing")
        email_str = contact.get("email") or "—"
        conf = f" ({contact['confianza']})" if contact.get("confianza") else ""
        print(f"  {m['equipo']} vs {m['rival']} ({m['date'].strftime('%d/%m/%Y')}) → {status}{conf} | email: {email_str}")
        if status == "found_ai":
            new_contacts.append(contact)

    print()

    # Actualizar Excel
    if not args.dry_run:
        print("💾 Actualizando Excel...")
        rows_written = 0
        for m in new_leads:
            try:
                row = append_match_row(wb, m)
                rows_written += 1
            except Exception as e:
                print(f"  ERROR escribiendo fila para {m['rival']}: {e}")

        # Cachear en EQUIPOS VISITANTES los contactos nuevos hallados por IA
        contacts_saved = 0
        for c in new_contacts:
            try:
                append_contact_row(wb, c)
                contacts_saved += 1
            except Exception as e:
                print(f"  ERROR guardando contacto {c.get('nombre')}: {e}")

        save_workbook(wb, excel_path)
        print(f"  {rows_written} filas añadidas al REGISTRO"
              + (f", {contacts_saved} contactos nuevos guardados en la base de datos" if contacts_saved else "")
              + ". Backup guardado en .bak\n")
    else:
        print("  [DRY RUN] Excel no modificado.\n")

    # Generar informe HTML
    print("📄 Generando informe HTML...")
    try:
        report_path = generate_report(new_leads, output_dir, now)
        print(f"  Informe guardado en: {report_path}\n")
        webbrowser.open(f"file:///{report_path.replace(chr(92), '/')}")
    except Exception as e:
        print(f"  ERROR generando informe: {e}")

    if manual_teams:
        _print_manual_section(manual_teams)

    print("✅ Proceso completado.\n")


def _print_manual_section(manual_teams: list[dict]):
    print("\n⚠️  EQUIPOS A VERIFICAR MANUALMENTE:")
    for t in manual_teams:
        url = t.get("manual_url", "sin URL configurada")
        print(f"  • {t['name']} ({t['sport']}) → {url}")
    print()


def main():
    parser = argparse.ArgumentParser(description="ATM Catering Deportivo — Automatización semanal")
    parser.add_argument("--window-start", type=int, default=None, help="Días desde hoy para inicio de ventana (default: 14)")
    parser.add_argument("--window-end", type=int, default=None, help="Días desde hoy para fin de ventana (default: 21)")
    parser.add_argument("--dry-run", action="store_true", help="No modifica el Excel ni abre Outlook")
    parser.add_argument("--no-ai", action="store_true", help="Desactiva la búsqueda de contactos por IA/web (solo base de datos)")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
