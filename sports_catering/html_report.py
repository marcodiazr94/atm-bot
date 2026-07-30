"""
Genera un informe HTML con tarjetas de email para cada partido nuevo.
Cada tarjeta incluye el email pre-rellenado con la plantilla y un botón mailto.
"""
import urllib.parse
from datetime import datetime
from pathlib import Path

EMAIL_TEMPLATE = """\
Hola,

Os escribo porque hemos visto que próximamente jugáis en Asturias y queríamos proponeros una opción de catering post-partido para el equipo.

En ATM burgers trabajamos habitualmente con catering deportivo, adaptándonos a las necesidades de cada plantilla: menús cerrados o individuales, control de alergias e intolerancias, opciones sin gluten y tiempos de entrega ajustados al final del partido.

Nuestra forma de trabajar es sencilla:
Enviamos un formulario individual para que cada jugador y miembro del staff pueda elegir su menú según sus preferencias y requisitos, y nos encargamos de que todo esté listo en el horario y lugar acordado.

También podemos configurar un menú cerrado según vuestros requisitos. Podéis echar un ojo a nuestra carta en atmburgers.com.

Si os encaja la idea, podemos comentarlo rápidamente y ajustar la propuesta a lo que necesitéis.
Será un placer recibiros durante vuestra estancia en Asturias y formar parte de vuestra experiencia.

Un saludo"""

SUBJECT_TEMPLATE = "Catering post-partido | {rival} en {ciudad} - ATM Burgers"


def _format_date_es(dt: datetime) -> str:
    DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
              "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{DAYS[dt.weekday()]} {dt.day} de {MONTHS[dt.month - 1]} de {dt.year}"


def _build_email_body(match: dict) -> str:
    return EMAIL_TEMPLATE


def _build_subject(match: dict) -> str:
    return SUBJECT_TEMPLATE.format(
        rival=match.get("rival", ""),
        ciudad=match.get("ciudad", "Asturias"),
    )


def _mailto_link(to: str, subject: str, body: str) -> str:
    params = urllib.parse.urlencode({"subject": subject, "body": body})
    to_enc = urllib.parse.quote(to)
    return f"mailto:{to_enc}?{params}"


def _wa_link(telefono: str) -> str | None:
    """Genera un enlace wa.me (click-to-chat) a partir de un teléfono español."""
    if not telefono:
        return None
    digits = "".join(c for c in str(telefono) if c.isdigit())
    if not digits:
        return None
    # Si son 9 dígitos (móvil/fijo español sin prefijo), anteponer 34
    if len(digits) == 9:
        digits = "34" + digits
    return f"https://wa.me/{digits}"


def _contact_badge(lead: dict) -> str:
    """Etiqueta según el origen del contacto."""
    status = lead.get("status", "")
    if status == "found_ai":
        conf = (lead.get("confianza") or "media").lower()
        return f'<span class="badge ai">🤖 IA · confianza {conf}</span>'
    if status.startswith("found"):
        return '<span class="badge found">✓ Contacto en BD</span>'
    return ""


def generate_report(leads: list[dict], output_dir: str, run_date: datetime = None) -> str:
    """
    Genera el archivo HTML con todas las tarjetas de email.
    Devuelve la ruta al archivo generado.
    """
    if run_date is None:
        run_date = datetime.now()

    output_path = Path(output_dir) / f"atm_catering_{run_date.strftime('%Y%m%d')}.html"

    with_email = [l for l in leads if l.get("email")]
    without_email = [l for l in leads if not l.get("email")]

    cards_html = ""
    for i, lead in enumerate(with_email):
        subject = _build_subject(lead)
        body = _build_email_body(lead)
        mailto = _mailto_link(lead["email"], subject, body)
        fecha_str = _format_date_es(lead["fecha"]) if isinstance(lead.get("fecha"), datetime) else str(lead.get("fecha", ""))
        hora_val = lead.get("hora")
        hora_str = f"{int(hora_val):02d}:{round((hora_val % 1) * 60):02d}" if hora_val else ""
        contact_badge = _contact_badge(lead)

        # Línea extra con teléfono / web si están disponibles
        extra = []
        if lead.get("telefono"):
            wa = _wa_link(lead["telefono"])
            tel_html = f'📞 {lead["telefono"]}'
            if wa:
                tel_html += f' <a href="{wa}" target="_blank">WhatsApp</a>'
            extra.append(tel_html)
        if lead.get("web"):
            extra.append(f'🌐 <a href="{lead["web"]}" target="_blank">web</a>')
        if lead.get("instagram"):
            extra.append(f'📷 <a href="{lead["instagram"]}" target="_blank">Instagram</a>')
        extra_html = f'<div class="card-extra">{" &nbsp;·&nbsp; ".join(extra)}</div>' if extra else ""

        cards_html += f"""
        <div class="card card-ok">
          <div class="card-header">
            <div class="card-title">
              <span class="sport-tag">{lead.get('deporte','')}</span>
              <strong>{lead.get('equipo','')} vs {lead.get('rival','')}</strong>
            </div>
            {contact_badge}
          </div>
          <div class="card-meta">
            📅 {fecha_str} {hora_str} &nbsp;|&nbsp; 📍 {lead.get('lugar', lead.get('ciudad',''))} &nbsp;|&nbsp; 🏙️ {lead.get('ciudad','')}
          </div>
          <div class="card-email-info">
            <div class="email-to"><strong>Para:</strong> {lead.get('email','')}</div>
            <div class="email-subject"><strong>Asunto:</strong> {subject}</div>
          </div>
          {extra_html}
          <div class="card-body-preview">
            <pre>{body[:300]}…</pre>
          </div>
          <div class="card-actions">
            <a href="{mailto}" class="btn btn-primary">✉️ Abrir en Outlook</a>
          </div>
        </div>"""

    missing_cards = ""
    for lead in without_email:
        fecha_str = _format_date_es(lead["fecha"]) if isinstance(lead.get("fecha"), datetime) else str(lead.get("fecha", ""))
        search_url = lead.get("search_url", f"https://www.google.com/search?q={urllib.parse.quote_plus(lead.get('rival',''))}")
        subject = _build_subject(lead)
        body = _build_email_body(lead)
        mailto_no_to = f"mailto:?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"

        # Si la IA encontró teléfono aunque no email, mostrarlo con WhatsApp
        tel_action = ""
        if lead.get("telefono"):
            wa = _wa_link(lead["telefono"])
            tel_action = f'<a href="{wa}" target="_blank" class="btn btn-search">💬 WhatsApp {lead["telefono"]}</a>' if wa else ""

        missing_cards += f"""
        <div class="card card-missing">
          <div class="card-header">
            <div class="card-title">
              <span class="sport-tag">{lead.get('deporte','')}</span>
              <strong>{lead.get('equipo','')} vs {lead.get('rival','')}</strong>
            </div>
            <span class="badge missing">⚠ Falta email</span>
          </div>
          <div class="card-meta">
            📅 {fecha_str} &nbsp;|&nbsp; 🏙️ {lead.get('ciudad','')}
          </div>
          <div class="card-actions">
            {tel_action}
            <a href="{search_url}" target="_blank" class="btn btn-search">🔍 Buscar contacto en Google</a>
            <a href="{mailto_no_to}" class="btn btn-secondary">✉️ Preparar email (sin destinatario)</a>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATM Catering Deportivo — {run_date.strftime('%d/%m/%Y')}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; padding: 20px; }}
  .header {{ background: #1a1a2e; color: white; padding: 20px 24px; border-radius: 10px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 22px; font-weight: 700; }}
  .header .subtitle {{ opacity: 0.8; margin-top: 4px; font-size: 14px; }}
  .stats {{ display: flex; gap: 12px; margin-bottom: 24px; }}
  .stat {{ background: white; border-radius: 8px; padding: 14px 18px; flex: 1; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  .stat-num {{ font-size: 28px; font-weight: 700; color: #1a1a2e; }}
  .stat-label {{ font-size: 12px; color: #888; margin-top: 2px; }}
  .section-title {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #555; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(480px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .card {{ background: white; border-radius: 10px; padding: 18px; box-shadow: 0 1px 4px rgba(0,0,0,.1); border-left: 4px solid #4caf50; }}
  .card-missing {{ border-left-color: #ff9800; }}
  .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }}
  .card-title {{ display: flex; align-items: center; gap: 8px; font-size: 15px; flex-wrap: wrap; }}
  .sport-tag {{ background: #e8f4fd; color: #1565c0; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; }}
  .badge {{ font-size: 11px; padding: 2px 8px; border-radius: 12px; white-space: nowrap; }}
  .badge.found {{ background: #e8f5e9; color: #2e7d32; }}
  .badge.ai {{ background: #ede7f6; color: #5e35b1; }}
  .badge.missing {{ background: #fff3e0; color: #e65100; }}
  .card-meta {{ font-size: 13px; color: #666; margin-bottom: 10px; }}
  .card-extra {{ font-size: 13px; color: #555; margin-bottom: 10px; }}
  .card-extra a {{ color: #1565c0; text-decoration: none; }}
  .card-email-info {{ background: #f8f9fa; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px; font-size: 13px; }}
  .card-email-info div {{ margin-bottom: 4px; }}
  .card-body-preview {{ background: #f8f9fa; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px; }}
  .card-body-preview pre {{ font-family: inherit; font-size: 12px; color: #555; white-space: pre-wrap; line-height: 1.5; }}
  .card-actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .btn {{ display: inline-block; padding: 9px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 500; cursor: pointer; }}
  .btn-primary {{ background: #1a1a2e; color: white; }}
  .btn-primary:hover {{ background: #2d2d4e; }}
  .btn-search {{ background: #1565c0; color: white; }}
  .btn-search:hover {{ background: #1976d2; }}
  .btn-secondary {{ background: #eee; color: #333; }}
  .empty {{ text-align: center; color: #999; padding: 40px; background: white; border-radius: 10px; }}
</style>
</head>
<body>

<div class="header">
  <h1>🍔 ATM Catering Deportivo</h1>
  <div class="subtitle">Partidos a contactar — Generado el {run_date.strftime('%d/%m/%Y a las %H:%M')}</div>
</div>

<div class="stats">
  <div class="stat">
    <div class="stat-num">{len(leads)}</div>
    <div class="stat-label">Partidos nuevos encontrados</div>
  </div>
  <div class="stat">
    <div class="stat-num" style="color:#2e7d32">{len(with_email)}</div>
    <div class="stat-label">Con email listo para enviar</div>
  </div>
  <div class="stat">
    <div class="stat-num" style="color:#e65100">{len(without_email)}</div>
    <div class="stat-label">Sin email — buscar contacto</div>
  </div>
</div>

{"<div class='section-title'>📧 Listos para enviar</div><div class='cards'>" + cards_html + "</div>" if with_email else ""}
{"<div class='section-title'>⚠️ Falta contacto — buscar manualmente</div><div class='cards'>" + missing_cards + "</div>" if without_email else ""}
{"<div class='empty'>✅ No hay partidos nuevos en la ventana de 14-21 días.</div>" if not leads else ""}

</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
