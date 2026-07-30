"""
Script one-shot: migra los contactos del Excel (hoja EQUIPOS VISITANTES)
a la tabla `contactos` de Supabase.

Uso:
    python migrar_excel_supabase.py
    python migrar_excel_supabase.py --dry-run   # solo muestra, no escribe
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sports_catering.config import load_config
from sports_catering.excel_manager import load_known_contacts, load_workbook
from sports_catering import db


def main():
    parser = argparse.ArgumentParser(description="Migrar contactos Excel → Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra los datos, no escribe en Supabase")
    args = parser.parse_args()

    cfg = load_config()
    excel_path = cfg.get("excel_path") or cfg.get("catering_excel_path")
    if not excel_path:
        print("ERROR: No se encontró excel_path en config.json")
        sys.exit(1)

    print(f"Cargando Excel: {excel_path}")
    try:
        wb = load_workbook(excel_path)
        known = load_known_contacts(wb)
    except Exception as e:
        print(f"ERROR leyendo Excel: {e}")
        sys.exit(1)

    print(f"{len(known)} contactos encontrados en la hoja EQUIPOS VISITANTES\n")

    ok = 0
    errors = 0
    for key, c in known.items():
        row = {
            "nombre":    c.get("nombre") or key,
            "email":     c.get("email"),
            "telefono":  c.get("telefono"),
            "contacto":  c.get("contacto"),
            "verificado": False,
            "fuente":    "excel_import",
        }
        if args.dry_run:
            print(f"  [DRY] {row['nombre']} | email: {row['email']} | tel: {row['telefono']}")
        else:
            try:
                db.upsert_contacto(row)
                print(f"  ✓ {row['nombre']}")
                ok += 1
            except Exception as e:
                print(f"  ERROR {row['nombre']}: {e}")
                errors += 1

    if not args.dry_run:
        print(f"\n{'='*50}")
        print(f"Migración completada: {ok} contactos importados, {errors} errores.")


if __name__ == "__main__":
    main()
