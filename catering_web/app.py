"""
ATM Catering Deportivo — Interfaz web (Streamlit).

Arranque local:
    streamlit run catering_web/app.py
"""
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib

import pandas as pd
import streamlit as st

try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

from catering_web.auth import logout_button, require_login
from sports_catering import db, engine
importlib.reload(db)
from sports_catering.config import load_config
from sports_catering.contact_finder import find_contact
from sports_catering.html_report import (
    EMAIL_TEMPLATE,
    SUBJECT_TEMPLATE,
    _format_date_es,
    _wa_link,
)

st.set_page_config(page_title="ATM Catering Deportivo", page_icon="🍔", layout="wide")

# ── Constantes ─────────────────────────────────────────────────────────────────

DEPORTES = ["Todos", "FUTBOL", "BALONCESTO", "BALONMANO", "VOLEIBOL", "HOCKEY PATINES"]

EQUIPOS_ASTURIANOS = {
    "REAL OVIEDO", "SPORTING GIJON", "SPORTING GIJÓN",
    "TSK ROCES", "REAL OVIEDO VETUSTA", "LLANERA",
    "CONFIA BASE OVIEDO", "REAL AVILES", "REAL AVILÉS",
}

DIAS_AVISO = 15  # antelación mínima recomendada para contactar

ESTADOS_DISPLAY = {
    "sin_contactar":     "⬜ Sin contactar",
    "email_enviado":     "📧 Email enviado",
    "pedido_confirmado": "✅ Pedido confirmado",
    "sin_respuesta":     "🔕 Sin respuesta",
    "no_interesado":     "❌ No interesado",
}
ESTADOS_LISTA = list(ESTADOS_DISPLAY.values())
ESTADOS_DB    = {v: k for k, v in ESTADOS_DISPLAY.items()}

ESTADOS_PAGO_DISPLAY = {
    "pendiente": "⏳ Pendiente",
    "cobrado":   "💰 Cobrado",
    "cancelado": "❌ Cancelado",
}
ESTADOS_PAGO_LISTA = list(ESTADOS_PAGO_DISPLAY.values())
ESTADOS_PAGO_DB    = {v: k for k, v in ESTADOS_PAGO_DISPLAY.items()}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_subject(lead: dict) -> str:
    return SUBJECT_TEMPLATE.format(
        rival=lead.get("rival", ""),
        ciudad=lead.get("ciudad", "Asturias"),
    )


def _hora_str(hora) -> str:
    if not hora:
        return ""
    return f"{int(hora):02d}:{round((hora % 1) * 60):02d}"


def _fecha_dt(p) -> datetime | None:
    try:
        return datetime.fromisoformat(str(p["fecha"]).replace("Z", "+00:00"))
    except Exception:
        return None


def _dias_para(p) -> int | None:
    fd = _fecha_dt(p)
    if fd is None:
        return None
    return (fd - datetime.now(timezone.utc)).days


@st.cache_data(show_spinner=False)
def _cargar_config():
    return load_config()


def _es_derbi(p: dict) -> bool:
    return p.get("rival", "").upper() in EQUIPOS_ASTURIANOS


# ── B: Pantalla de inicio / Dashboard ─────────────────────────────────────────

def pantalla_inicio():
    st.title("🏠 Panel de control")

    try:
        todos = db.get_partidos(solo_proximos=True)
    except Exception as e:
        st.error(f"Error al conectar con Supabase: {e}")
        return

    now = datetime.now(timezone.utc)
    proximos_30, urgentes = [], []

    for p in todos:
        if _es_derbi(p):
            continue
        fd = _fecha_dt(p)
        if fd is None:
            continue
        dias = (fd - now).days
        if 0 <= dias <= 30:
            proximos_30.append(p)
        if 0 <= dias <= DIAS_AVISO and (p.get("estado") or "sin_contactar") == "sin_contactar":
            urgentes.append(p)

    proximos_30.sort(key=lambda p: _fecha_dt(p) or now)
    urgentes.sort(key=lambda p: _fecha_dt(p) or now)

    # ── E: Banner de alertas urgentes ─────────────────────────────────────
    if urgentes:
        lineas = [f"⚠️ **{len(urgentes)} partido(s) en los próximos {DIAS_AVISO} días sin contactar:**"]
        for p in urgentes:
            dias = _dias_para(p)
            fd   = _fecha_dt(p)
            lineas.append(
                f"- **{p.get('equipo','')} vs {p.get('rival','')}** · "
                f"en {dias} día(s) ({fd.strftime('%d/%m') if fd else '?'}) · "
                f"{p.get('deporte','')} · {p.get('ciudad','')}"
            )
        st.warning("\n".join(lineas))
    else:
        st.success(f"✅ No hay partidos urgentes (próximos {DIAS_AVISO} días) sin contactar.")

    st.divider()

    # ── Métricas ──────────────────────────────────────────────────────────
    confirmados      = [p for p in todos if p.get("estado") == "pedido_confirmado"]
    ing_confirmado   = sum(float(p.get("importe_confirmado") or 0) for p in todos)
    cobrado          = sum(float(p.get("importe_confirmado") or 0)
                          for p in todos if p.get("estado_pago") == "cobrado")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Próximos 30 días", len(proximos_30))
    m2.metric(f"Sin contactar (≤{DIAS_AVISO} días)", len(urgentes))
    m3.metric("Pedidos confirmados", len(confirmados))
    m4.metric("Ingresos confirmados", f"{ing_confirmado:.0f} €")

    # ── Estado de los próximos 30 días ─────────────────────────────────────
    if proximos_30:
        st.divider()
        st.subheader("Estado de los próximos 30 días")

        por_estado = {}
        for p in proximos_30:
            e = p.get("estado") or "sin_contactar"
            por_estado.setdefault(e, []).append(p)

        for estado_key in ["sin_contactar", "email_enviado", "pedido_confirmado",
                           "sin_respuesta", "no_interesado"]:
            partidos_e = por_estado.get(estado_key, [])
            if not partidos_e:
                continue
            label     = ESTADOS_DISPLAY.get(estado_key, estado_key)
            expandido = estado_key in ("sin_contactar", "email_enviado")
            with st.expander(f"{label} — {len(partidos_e)} partido(s)", expanded=expandido):
                for p in partidos_e:
                    fd   = _fecha_dt(p)
                    dias = _dias_para(p)
                    alerta   = " 🔴" if (dias is not None and 0 <= dias <= DIAS_AVISO) else ""
                    fecha_txt = fd.strftime("%d/%m/%Y") if fd else "?"
                    st.markdown(
                        f"**{p.get('equipo','')} vs {p.get('rival','')}**{alerta} · "
                        f"{fecha_txt} · {p.get('deporte','')} · {p.get('ciudad','')}"
                    )
                    if p.get("notas_partido"):
                        st.caption(f"📝 {p['notas_partido']}")

    # ── Resumen financiero ─────────────────────────────────────────────────
    if ing_confirmado > 0:
        st.divider()
        st.subheader("Resumen financiero — Temporada")
        f1, f2 = st.columns(2)
        f1.metric("Total confirmado", f"{ing_confirmado:.0f} €")
        f2.metric("Total cobrado", f"{cobrado:.0f} €")


# ── Pantalla: Partidos de la semana ───────────────────────────────────────────

def pantalla_partidos():
    st.title("📅 Partidos de la semana")
    st.caption("Equipos visitantes que van a jugar en Asturias.")

    # E: alerta rápida al inicio
    try:
        todos_check = db.get_partidos(solo_proximos=True)
        urgentes = [
            p for p in todos_check
            if not _es_derbi(p)
            and (_dias_para(p) is not None)
            and 0 <= _dias_para(p) <= DIAS_AVISO
            and (p.get("estado") or "sin_contactar") == "sin_contactar"
        ]
        if urgentes:
            st.warning(
                f"⚠️ **{len(urgentes)} partido(s)** en los próximos {DIAS_AVISO} días "
                f"sin contactar. Amplia el rango si no los ves abajo."
            )
    except Exception:
        pass

    cfg     = _cargar_config()
    ventana = cfg.get("lead_window_days", [14, 21])

    col1, col2, col3 = st.columns([1.3, 1.3, 1.3])
    with col1:
        d_ini = st.number_input("Desde (días)", min_value=0, max_value=120, value=int(ventana[0]))
    with col2:
        d_fin = st.number_input("Hasta (días)", min_value=1, max_value=180, value=int(ventana[1]))
    with col3:
        usar_ia = st.toggle("Buscar contactos con IA", value=True,
                            help="Si el equipo no está en la base de datos, lo busca en Internet.")

    if st.button("🔍 Buscar partidos", type="primary"):
        now     = datetime.now(timezone.utc)
        w_start = now + timedelta(days=d_ini)
        w_end   = now + timedelta(days=d_fin)

        try:
            todos = db.get_partidos(solo_proximos=True)
        except Exception as e:
            st.error(f"Error al cargar partidos: {e}")
            return

        leads = []
        for p in todos:
            fd = _fecha_dt(p)
            if fd and w_start <= fd <= w_end and not _es_derbi(p):
                leads.append(p)

        if leads:
            with st.spinner("Buscando contactos..."):
                for m in leads:
                    pid = m.get("id")           # guardar antes de que find_contact lo sobreescriba
                    m.update(find_contact(m["rival"], use_ai=usar_ia,
                                          city=m.get("ciudad", ""), sport=m.get("deporte", "")))
                    m["partido_id"] = pid       # restaurar con clave propia

        st.session_state["leads"] = leads

    leads = st.session_state.get("leads")
    if leads is None:
        st.info("Pulsa **Buscar partidos** para empezar.")
        return
    if not leads:
        st.success("✅ No hay partidos en la ventana seleccionada.")
        st.caption("Si acabas de importar el calendario, prueba a ampliar el rango de días.")
        return

    con_email = [l for l in leads if l.get("email")]
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Partidos encontrados", len(leads))
    m2.metric("Con email listo", len(con_email))
    m3.metric("Sin email", len(leads) - len(con_email))
    st.divider()

    for lead in leads:
        _tarjeta_partido(lead)


def _tarjeta_partido(lead: dict):
    fecha_dt   = _fecha_dt(lead)
    fecha_str  = _format_date_es(fecha_dt) if fecha_dt else str(lead.get("fecha") or "")
    status     = lead.get("status", "missing")
    rival      = lead.get("rival", "")
    verificado = lead.get("verificado", False)
    partido_id = lead.get("partido_id") or lead.get("id")
    dias       = _dias_para(lead)

    badge = {
        "found_exact":   "✅ Verificado" if verificado else "📋 En base de datos",
        "found_partial": "✅ Verificado" if verificado else "📋 En base de datos",
        "found_fuzzy":   "✅ Verificado" if verificado else "📋 En base de datos",
        "found_ai":      f"🤖 IA · confianza {lead.get('confianza', 'media')}",
        "missing":       "⚠️ Sin contacto",
    }.get(status, status)

    urgencia = "🔴 " if (dias is not None and 0 <= dias <= DIAS_AVISO) else ""

    emails = lead.get("emails") or []
    if not emails and lead.get("email"):
        emails = [lead["email"]]
    if lead.get("emails_extra"):
        for e in lead["emails_extra"].split(","):
            e = e.strip()
            if e and e not in emails:
                emails.append(e)

    with st.container(border=True):

        # ── Cabecera ─────────────────────────────────────────────────────
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(
                f"**{urgencia}{lead.get('equipo','')} vs {rival}**  \n"
                f"`{lead.get('deporte','')}` · 📅 {fecha_str} {_hora_str(lead.get('hora'))} · "
                f"📍 {lead.get('lugar') or lead.get('ciudad','')}"
            )
        with c2:
            st.markdown(f"<div style='text-align:right'>{badge}</div>", unsafe_allow_html=True)

        # ── A: Estado del contacto ────────────────────────────────────────
        if partido_id:
            estado_actual_db  = lead.get("estado") or "sin_contactar"
            estado_actual_txt = ESTADOS_DISPLAY.get(estado_actual_db, "⬜ Sin contactar")
            col_est, col_save = st.columns([4, 1])
            with col_est:
                nuevo_estado_txt = st.selectbox(
                    "Estado",
                    ESTADOS_LISTA,
                    index=ESTADOS_LISTA.index(estado_actual_txt) if estado_actual_txt in ESTADOS_LISTA else 0,
                    key=f"est_{partido_id}",
                    label_visibility="collapsed",
                )
            with col_save:
                if st.button("Guardar", key=f"save_est_{partido_id}", use_container_width=True):
                    nuevo_db = ESTADOS_DB.get(nuevo_estado_txt, "sin_contactar")
                    try:
                        db.update_partido(partido_id, estado=nuevo_db)
                        lead["estado"] = nuevo_db
                        st.toast(f"Estado: {nuevo_estado_txt}")
                    except Exception as e:
                        st.error(str(e))

        if status == "missing":
            q = urllib.parse.quote_plus(f"{rival} club deportivo email contacto")
            st.link_button("🔍 Buscar en Google", f"https://www.google.com/search?q={q}")
            _widget_notas(lead, partido_id)
            return

        # ── Contactos del club ────────────────────────────────────────────
        st.markdown("**Contactos del club**")
        info_linea = []
        if lead.get("telefono"):
            info_linea.append(f"📞 {lead['telefono']}")
        if lead.get("web"):
            info_linea.append(f"🌐 [{lead['web']}]({lead['web']})")
        if lead.get("instagram") or lead.get("instagram_club"):
            ig = lead.get("instagram") or lead.get("instagram_club")
            info_linea.append(f"📸 {ig}")
        if info_linea:
            st.caption(" · ".join(info_linea))

        if emails:
            for email in emails:
                col_email, col_btn = st.columns([3, 1])
                col_email.markdown(f"✉️ `{email}`")
                mailto_q = urllib.parse.urlencode(
                    {"subject": _build_subject(lead), "body": EMAIL_TEMPLATE}
                )
                col_btn.link_button(
                    "Enviar", f"mailto:{urllib.parse.quote(email)}?{mailto_q}",
                    key=f"mail_{rival}_{email}",
                )

        wa = _wa_link(lead.get("telefono")) if lead.get("telefono") else None
        if wa:
            st.link_button("💬 WhatsApp", wa)

        # ── Nutricionista ────────────────────────────────────────────────
        nutri_nombre = lead.get("nutricionista_nombre") or lead.get("nutricionista")
        nutri_email  = lead.get("nutricionista_email")
        nutri_ig     = lead.get("nutricionista_instagram")
        nutri_ok     = lead.get("nutricionista_confirmado", False)

        if nutri_nombre or nutri_email or nutri_ig:
            st.divider()
            st.markdown(f"**Nutricionista/Dietista**{' ✓' if nutri_ok else ' (sin confirmar)'}")
            nutri_linea = []
            if nutri_nombre:
                nutri_linea.append(f"👤 {nutri_nombre}")
            if nutri_ig:
                nutri_linea.append(f"📸 {nutri_ig}")
            if nutri_linea:
                st.caption(" · ".join(nutri_linea))
            if nutri_email:
                col_ne, col_nb = st.columns([3, 1])
                col_ne.markdown(f"✉️ `{nutri_email}`")
                mailto_n = urllib.parse.urlencode(
                    {"subject": _build_subject(lead), "body": EMAIL_TEMPLATE}
                )
                col_nb.link_button(
                    "Enviar", f"mailto:{urllib.parse.quote(nutri_email)}?{mailto_n}",
                    key=f"mail_nutri_{rival}",
                )

        # ── Buscar más contactos ──────────────────────────────────────────
        if status != "found_ai" and (len(emails) <= 1 or not (nutri_nombre or nutri_email)):
            if st.button("🔄 Buscar más contactos con IA", key=f"rebus_{rival}"):
                with st.spinner(f"Buscando más información sobre {rival}..."):
                    ai = find_contact(rival, use_ai=True,
                                      city=lead.get("ciudad", ""), sport=lead.get("deporte", ""))
                st.session_state[f"extra_{rival}"] = ai
                st.rerun()

        extra = st.session_state.get(f"extra_{rival}")
        if extra and extra.get("status") == "found_ai":
            new_emails = extra.get("emails") or ([extra["email"]] if extra.get("email") else [])
            for em in new_emails:
                if em not in emails:
                    col_e, col_b = st.columns([3, 1])
                    col_e.markdown(f"✉️ `{em}` *(IA)*")
                    mailto_x = urllib.parse.urlencode(
                        {"subject": _build_subject(lead), "body": EMAIL_TEMPLATE}
                    )
                    col_b.link_button(
                        "Enviar", f"mailto:{urllib.parse.quote(em)}?{mailto_x}",
                        key=f"mail_extra_{rival}_{em}",
                    )

        # ── C: Email editable ─────────────────────────────────────────────
        st.divider()
        with st.expander("✉️ Personalizar email antes de enviar"):
            asunto_edit = st.text_input("Asunto", value=_build_subject(lead),
                                        key=f"subj_{rival}")
            cuerpo_edit = st.text_area("Cuerpo", value=EMAIL_TEMPLATE, height=220,
                                       key=f"body_{rival}")
            if emails:
                dest = st.selectbox("Destinatario", emails, key=f"dest_{rival}")
                mailto_custom = urllib.parse.urlencode(
                    {"subject": asunto_edit, "body": cuerpo_edit}
                )
                st.link_button(
                    "📤 Abrir en gestor de correo",
                    f"mailto:{urllib.parse.quote(dest)}?{mailto_custom}",
                    type="primary", use_container_width=True,
                )

        # ── Verificar contacto ─────────────────────────────────────────────
        if not verificado and lead.get("nombre"):
            if st.button("☑️ Marcar contacto como verificado", key=f"ver_{rival}"):
                try:
                    db.marcar_verificado(lead["nombre"])
                    st.toast(f"Contacto de {rival} marcado como verificado.")
                    st.rerun()
                except Exception as e:
                    st.warning(str(e))

        # ── F: Notas del partido ──────────────────────────────────────────
        _widget_notas(lead, partido_id)


def _widget_notas(lead: dict, partido_id: str | None):
    if not partido_id:
        return
    notas_actuales = lead.get("notas_partido") or ""
    with st.expander("📝 Notas del partido", expanded=bool(notas_actuales)):
        notas_nuevas = st.text_area(
            "Notas", value=notas_actuales, height=80,
            placeholder="Ej: prefieren menú sin gluten · entregar 2h antes · contactar con el utillero...",
            key=f"notas_{partido_id}",
            label_visibility="collapsed",
        )
        if st.button("Guardar notas", key=f"save_notas_{partido_id}"):
            try:
                db.update_partido(partido_id, notas_partido=notas_nuevas or None)
                lead["notas_partido"] = notas_nuevas
                st.toast("Notas guardadas.")
            except Exception as e:
                st.error(str(e))


# ── Generador de ficha de cocina ──────────────────────────────────────────────

def _generar_ficha_cocina(p: dict, fd, fecha_str: str) -> str:
    rival      = p.get("rival", "")
    equipo     = p.get("equipo", "")
    deporte    = p.get("deporte", "")
    ciudad     = p.get("ciudad", "")
    hora_part  = _hora_str(p.get("hora")) or "—"
    hora_entr  = p.get("hora_entrega") or "—"
    chofer     = p.get("telefono_chofer") or "—"
    direccion  = p.get("direccion_entrega") or "—"
    importe    = f"{float(p.get('importe_confirmado') or 0):.0f} €"
    notas      = p.get("notas_partido") or ""
    link_sheet = p.get("link_sheet") or ""
    estado_p   = ESTADOS_PAGO_DISPLAY.get(p.get("estado_pago") or "pendiente", "⏳ Pendiente")

    sheet_html = (
        f'<a href="{link_sheet}" style="color:#1a73e8">Ver pedidos individuales en Google Sheet →</a>'
        if link_sheet else "<em>Sin enlace registrado</em>"
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Ficha de cocina — {rival} {fecha_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #fff; color: #222; padding: 32px; max-width: 720px; margin: auto; }}
  .header {{ background: #1a1a2e; color: #fff; border-radius: 10px;
             padding: 20px 24px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 20px; }}
  .header .sub {{ opacity: .75; font-size: 13px; margin-top: 4px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
  .box {{ border: 1px solid #e0e0e0; border-radius: 8px; padding: 14px 16px; }}
  .box .label {{ font-size: 11px; text-transform: uppercase; color: #888;
                 letter-spacing: .5px; margin-bottom: 4px; }}
  .box .value {{ font-size: 18px; font-weight: 600; }}
  .sheet-box {{ border: 2px solid #1a73e8; border-radius: 8px; padding: 14px 16px;
                margin-bottom: 20px; }}
  .sheet-box .label {{ font-size: 11px; text-transform: uppercase; color: #1a73e8;
                       letter-spacing: .5px; margin-bottom: 6px; }}
  .notes {{ background: #fffde7; border-left: 4px solid #f9a825;
            padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 20px;
            font-size: 14px; line-height: 1.6; }}
  .footer {{ font-size: 11px; color: #aaa; text-align: center; margin-top: 32px; }}
  @media print {{ body {{ padding: 16px; }} }}
</style>
</head>
<body>

<div class="header">
  <h1>🍔 Ficha de cocina — {equipo} vs {rival}</h1>
  <div class="sub">{deporte} · {fecha_str} {hora_part} · {ciudad}</div>
</div>

<div class="grid">
  <div class="box">
    <div class="label">Hora de entrega</div>
    <div class="value">🕐 {hora_entr}</div>
  </div>
  <div class="box">
    <div class="label">Receptor / chofer</div>
    <div class="value">🚗 {chofer}</div>
  </div>
  <div class="box" style="grid-column: span 2">
    <div class="label">Dirección de entrega</div>
    <div class="value" style="font-size:15px">📍 {direccion}</div>
  </div>
  <div class="box">
    <div class="label">Importe</div>
    <div class="value">💰 {importe}</div>
  </div>
  <div class="box">
    <div class="label">Estado de pago</div>
    <div class="value" style="font-size:15px">{estado_p}</div>
  </div>
</div>

<div class="sheet-box">
  <div class="label">📊 Pedidos individuales de jugadores</div>
  {sheet_html}
</div>

{"<div class='notes'><strong>📝 Notas:</strong><br>" + notas.replace(chr(10), "<br>") + "</div>" if notas else ""}

<div class="footer">Generado por ATM Catering Deportivo · atmburgers.com</div>

</body>
</html>"""


# ── D: Pantalla de pedidos e ingresos ─────────────────────────────────────────

def pantalla_pedidos():
    st.title("💰 Pedidos e ingresos")
    st.caption(
        "Registra el importe de cada pedido y el estado de pago para controlar "
        "lo que genera la iniciativa de catering deportivo."
    )

    try:
        todos = db.get_partidos()
    except Exception as e:
        st.error(f"Error al conectar con Supabase: {e}")
        return

    partidos = [p for p in todos if not _es_derbi(p)]

    if not partidos:
        st.info("No hay partidos en el calendario. Importa los calendarios desde 'Calendario de temporada'.")
        return

    # ── Filtros ──────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    f1, f2, f3 = st.columns(3)
    with f1:
        solo_futuro = st.toggle("Solo próximos", value=True)
    with f2:
        solo_con_importe = st.toggle("Solo con importe registrado", value=False)
    with f3:
        filtro_pago = st.selectbox(
            "Estado de pago", ["Todos"] + ESTADOS_PAGO_LISTA, label_visibility="visible"
        )

    if solo_futuro:
        partidos = [p for p in partidos if (_fecha_dt(p) or now) >= now]
    if solo_con_importe:
        partidos = [p for p in partidos if p.get("importe_confirmado")]
    if filtro_pago != "Todos":
        val_db = ESTADOS_PAGO_DB.get(filtro_pago)
        if val_db:
            partidos = [p for p in partidos
                        if (p.get("estado_pago") or "pendiente") == val_db]

    partidos.sort(key=lambda p: _fecha_dt(p) or now)

    # ── Totales ──────────────────────────────────────────────────────────
    total_conf  = sum(float(p.get("importe_confirmado") or 0) for p in partidos)
    total_cobr  = sum(float(p.get("importe_confirmado") or 0)
                      for p in partidos if p.get("estado_pago") == "cobrado")
    n_pedidos   = sum(1 for p in partidos if p.get("importe_confirmado"))

    t1, t2, t3 = st.columns(3)
    t1.metric("Pedidos registrados", n_pedidos)
    t2.metric("Total confirmado", f"{total_conf:.0f} €")
    t3.metric("Total cobrado", f"{total_cobr:.0f} €")

    st.divider()

    if not partidos:
        st.info("No hay partidos con los filtros seleccionados.")
        return

    # ── Lista de partidos ─────────────────────────────────────────────────
    for p in partidos:
        pid = p.get("id")
        fd  = _fecha_dt(p)
        fecha_str = fd.strftime("%d/%m/%Y") if fd else "?"
        estado_contacto = ESTADOS_DISPLAY.get(p.get("estado") or "sin_contactar", "⬜ Sin contactar")
        estado_pago_txt = ESTADOS_PAGO_DISPLAY.get(p.get("estado_pago") or "pendiente", "⏳ Pendiente")
        imp_conf        = float(p.get("importe_confirmado") or 0)
        tiene_logistica = any(p.get(k) for k in ("hora_entrega", "telefono_chofer",
                                                   "direccion_entrega", "link_sheet"))

        with st.container(border=True):
            row_h, row_m = st.columns([3, 1])
            with row_h:
                st.markdown(
                    f"**{p.get('equipo','')} vs {p.get('rival','')}** · "
                    f"📅 {fecha_str} · `{p.get('deporte','')}` · {p.get('ciudad','')}"
                )
                st.caption(f"Contacto: {estado_contacto} · Pago: {estado_pago_txt}")
                logistica_linea = []
                if p.get("hora_entrega"):
                    logistica_linea.append(f"🕐 {p['hora_entrega']}")
                if p.get("telefono_chofer"):
                    logistica_linea.append(f"🚗 {p['telefono_chofer']}")
                if p.get("direccion_entrega"):
                    logistica_linea.append(f"📍 {p['direccion_entrega']}")
                if logistica_linea:
                    st.caption(" · ".join(logistica_linea))
                if p.get("link_sheet"):
                    st.markdown(f"📊 [Ver pedidos en Google Sheet]({p['link_sheet']})")
                if p.get("notas_partido"):
                    st.caption(f"📝 {p['notas_partido']}")
            with row_m:
                if imp_conf > 0:
                    st.metric("Confirmado", f"{imp_conf:.0f} €",
                              label_visibility="visible")

            # ── Formulario de edición ──────────────────────────────────────
            with st.expander("✏️ Registrar / editar pedido"):
                pe1, pe2 = st.columns(2)
                nuevo_conf = pe1.number_input(
                    "Importe del pedido (€)", min_value=0.0, step=10.0,
                    value=float(p.get("importe_confirmado") or 0),
                    key=f"conf_{pid}",
                )
                nuevo_pago_txt = pe2.selectbox(
                    "Estado de pago",
                    ESTADOS_PAGO_LISTA,
                    index=ESTADOS_PAGO_LISTA.index(estado_pago_txt)
                          if estado_pago_txt in ESTADOS_PAGO_LISTA else 0,
                    key=f"pago_{pid}",
                )

                st.markdown("**Logística de entrega**")
                lg1, lg2 = st.columns(2)
                nueva_hora = lg1.text_input(
                    "Hora de entrega", value=p.get("hora_entrega") or "",
                    placeholder="ej. 20:30", key=f"hora_{pid}",
                )
                nuevo_chofer = lg2.text_input(
                    "Teléfono del chofer / receptor", value=p.get("telefono_chofer") or "",
                    placeholder="ej. 612 345 678", key=f"chofer_{pid}",
                )
                nueva_dir = st.text_input(
                    "Campo / dirección de entrega", value=p.get("direccion_entrega") or "",
                    placeholder="ej. Carlos Tartiere, zona vestuarios visitante",
                    key=f"dir_{pid}",
                )
                nuevo_sheet = st.text_input(
                    "Enlace Google Sheet de pedidos", value=p.get("link_sheet") or "",
                    placeholder="https://docs.google.com/spreadsheets/...",
                    key=f"sheet_{pid}",
                )
                nueva_nota = st.text_area(
                    "Notas adicionales", value=p.get("notas_partido") or "",
                    height=68,
                    placeholder="Alergias, nº de personas, instrucciones especiales...",
                    key=f"nota_ped_{pid}",
                )

                btn1, btn2 = st.columns([1, 1])
                if btn1.button("💾 Guardar", key=f"save_ped_{pid}", type="primary",
                               use_container_width=True):
                    try:
                        db.update_partido(
                            pid,
                            importe_confirmado=nuevo_conf if nuevo_conf > 0 else None,
                            estado_pago=ESTADOS_PAGO_DB.get(nuevo_pago_txt, "pendiente"),
                            hora_entrega=nueva_hora or None,
                            telefono_chofer=nuevo_chofer or None,
                            direccion_entrega=nueva_dir or None,
                            link_sheet=nuevo_sheet or None,
                            notas_partido=nueva_nota or None,
                        )
                        st.toast("Pedido guardado.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

                # Solo mostrar ficha si hay algo que mostrar
                if tiene_logistica or imp_conf > 0 or p.get("link_sheet"):
                    if btn2.button("🖨️ Ficha de cocina", key=f"ficha_{pid}",
                                   use_container_width=True):
                        html = _generar_ficha_cocina(p, fd, fecha_str)
                        st.download_button(
                            "⬇️ Descargar ficha (HTML)",
                            data=html,
                            file_name=f"ficha_{p.get('rival','partido').replace(' ','_')}_{fecha_str.replace('/','')}.html",
                            mime="text/html",
                            key=f"dl_ficha_{pid}",
                        )


# ── Pantalla: Calendario de temporada ─────────────────────────────────────────

def pantalla_calendario():
    st.title("🗓️ Calendario de temporada")
    st.caption("Todos los partidos en casa de la temporada.")

    cfg   = _cargar_config()
    teams = cfg.get("teams", [])

    col1, col2, col3 = st.columns(3)
    with col1:
        ciudad_f = st.selectbox("Ciudad", ["Todas", "OVIEDO", "GIJON"])
    with col2:
        deporte_f = st.selectbox("Deporte", DEPORTES)
    with col3:
        solo_proximos = st.toggle("Solo próximos", value=True)

    if st.button("🔄 Actualizar desde calendarios",
                 help="Descarga los calendarios automáticos (~30 seg)"):
        barra = st.progress(0.0, text="Iniciando...")

        def _prog(nombre, i, total):
            barra.progress((i + 1) / max(total, 1), text=f"Consultando: {nombre}")

        with st.spinner("Descargando calendarios de la temporada..."):
            partidos, manuales = engine.cargar_temporada_completa(teams, on_progress=_prog)
        barra.empty()

        try:
            saved = db.upsert_partidos(partidos)
            st.success(f"✅ {saved} partidos guardados/actualizados en Supabase.")
        except RuntimeError as e:
            st.error(str(e))
            return

        if manuales:
            with st.expander(f"⚠️ {len(manuales)} equipos sin scraper automático"):
                for t in manuales:
                    st.markdown(f"- **{t['name']}** ({t['sport']}) → "
                                f"[{t.get('manual_url','—')}]({t.get('manual_url','#')})")

    with st.expander("📥 Importar calendario desde Excel"):
        tab_laliga, tab_generico = st.tabs(
            ["⚽ Formato LaLiga (Oviedo & Sporting)", "🏀 Formato genérico (cualquier equipo)"]
        )

        with tab_laliga:
            st.caption("Excel oficial de LaLiga. Se importan automáticamente los partidos en casa de Oviedo y Sporting.")
            archivo_ll = st.file_uploader("Excel LaLiga", type=["xlsx"], key="cal_upload_ll")
            temp_ll    = st.text_input("Temporada", value="2026-27", key="cal_temp_ll")

            if archivo_ll:
                try:
                    raw = pd.read_excel(archivo_ll, skiprows=1)
                    raw.columns = ["jornada", "fecha", "local", "esc_local",
                                   "gol1", "gol2", "esc_visit", "visitante"]
                    raw["jornada"]   = raw["jornada"].ffill()
                    raw["fecha"]     = pd.to_datetime(raw["fecha"].ffill(), errors="coerce")
                    raw["local"]     = raw["local"].astype(str).str.strip()
                    raw["visitante"] = raw["visitante"].astype(str).str.strip()

                    _MAP_LL = {
                        "OVIEDO":   ("REAL OVIEDO",    "OVIEDO", "CARLOS TARTIERE"),
                        "SPORTING": ("SPORTING GIJON", "GIJON",  "EL MOLINON"),
                    }
                    casa = raw[raw["local"].str.upper().isin(_MAP_LL)].copy()

                    if casa.empty:
                        st.warning("No se encontraron partidos de Oviedo ni Sporting.")
                    else:
                        prev = casa[["jornada", "fecha", "local", "visitante"]].copy()
                        prev["fecha"] = prev["fecha"].dt.strftime("%d/%m/%Y")
                        st.caption(f"{len(casa)} partidos encontrados:")
                        st.dataframe(prev.rename(columns={"jornada": "J", "fecha": "Fecha",
                                     "local": "Local", "visitante": "Visitante"}),
                                     use_container_width=True, hide_index=True)
                        if st.button("⬆️ Guardar en Supabase", type="primary", key="btn_ll"):
                            rows = []
                            for _, r in casa.iterrows():
                                nombre, ciudad, lugar = _MAP_LL[r["local"].upper()]
                                rows.append({
                                    "equipo": nombre, "ciudad": ciudad, "deporte": "FUTBOL",
                                    "rival":  r["visitante"].upper(),
                                    "fecha":  r["fecha"].replace(hour=12, tzinfo=timezone.utc),
                                    "jornada": int(r["jornada"]), "lugar": lugar,
                                    "source": "excel_import", "temporada": temp_ll.strip(),
                                })
                            try:
                                saved = db.upsert_partidos(rows)
                                st.success(f"✅ {saved} partidos importados.")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                except Exception as e:
                    st.error(f"Error leyendo el archivo: {e}")

        with tab_generico:
            st.caption(
                "Para balonmano, baloncesto, fútbol femenino o cualquier otro equipo. "
                "El Excel debe tener al menos tres columnas: **fecha**, **equipo local** y **equipo visitante**."
            )
            g1, g2 = st.columns(2)
            equipo_g        = g1.text_input("Nombre del equipo *", placeholder="ej. Balonmano Gijón", key="g_equipo")
            ciudad_g        = g2.selectbox("Ciudad", ["GIJON", "OVIEDO"], key="g_ciudad")
            deporte_g       = g1.selectbox("Deporte", ["FUTBOL", "BALONCESTO", "BALONMANO",
                                                        "VOLEIBOL", "HOCKEY PATINES"], key="g_deporte")
            lugar_g         = g2.text_input("Pabellón", placeholder="ej. Pabellón La Tejerona", key="g_lugar")
            temp_g          = g1.text_input("Temporada", value="2026-27", key="g_temp")
            nombre_en_excel = g2.text_input("Nombre del equipo en el Excel *",
                                            placeholder="Texto exacto que aparece como local",
                                            key="g_nombre_excel")

            archivo_g = st.file_uploader("Excel del calendario", type=["xlsx", "xls", "csv"],
                                          key="cal_upload_g")

            if archivo_g:
                try:
                    df_g = pd.read_csv(archivo_g) if archivo_g.name.endswith(".csv") \
                           else pd.read_excel(archivo_g)

                    st.caption(f"Columnas detectadas: {', '.join(df_g.columns.tolist())}")
                    col_fecha = st.selectbox("¿Cuál es la columna de FECHA?",    df_g.columns.tolist(), key="g_col_fecha")
                    col_local = st.selectbox("¿Cuál es la columna de LOCAL?",    df_g.columns.tolist(), key="g_col_local")
                    col_visit = st.selectbox("¿Cuál es la columna de VISITANTE?", df_g.columns.tolist(), key="g_col_visit")

                    if equipo_g and nombre_en_excel:
                        df_g["_fecha"] = pd.to_datetime(df_g[col_fecha], errors="coerce")
                        df_g["_local"] = df_g[col_local].astype(str).str.strip()
                        df_g["_visit"] = df_g[col_visit].astype(str).str.strip()
                        casa_g = df_g[df_g["_local"].str.upper() == nombre_en_excel.strip().upper()].copy()

                        if casa_g.empty:
                            st.warning(f"No se encontraron partidos donde el local sea '{nombre_en_excel}'.")
                            st.dataframe(df_g[[col_local]].drop_duplicates().head(20),
                                         use_container_width=True, hide_index=True)
                        else:
                            prev_g = casa_g[["_fecha", "_local", "_visit"]].copy()
                            prev_g["_fecha"] = prev_g["_fecha"].dt.strftime("%d/%m/%Y")
                            st.caption(f"{len(casa_g)} partidos en casa encontrados:")
                            st.dataframe(prev_g.rename(columns={"_fecha": "Fecha",
                                         "_local": "Local", "_visit": "Visitante"}),
                                         use_container_width=True, hide_index=True)

                            if st.button("⬆️ Guardar en Supabase", type="primary", key="btn_gen"):
                                rows_g = []
                                for _, r in casa_g.iterrows():
                                    if pd.isna(r["_fecha"]):
                                        continue
                                    rows_g.append({
                                        "equipo":    equipo_g.strip().upper(),
                                        "ciudad":    ciudad_g,
                                        "deporte":   deporte_g,
                                        "rival":     r["_visit"].upper(),
                                        "fecha":     r["_fecha"].replace(hour=12, tzinfo=timezone.utc),
                                        "lugar":     lugar_g or None,
                                        "source":    "excel_import",
                                        "temporada": temp_g.strip(),
                                    })
                                try:
                                    saved = db.upsert_partidos(rows_g)
                                    st.success(f"✅ {saved} partidos de {equipo_g} importados.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                except Exception as e:
                    st.error(f"Error leyendo el archivo: {e}")

    st.divider()
    try:
        partidos = db.get_partidos(
            ciudad=ciudad_f if ciudad_f != "Todas" else None,
            deporte=deporte_f if deporte_f != "Todos" else None,
            solo_proximos=solo_proximos,
        )
    except RuntimeError as e:
        st.error(f"Supabase no configurado: {e}")
        return

    if not partidos:
        st.info("No hay partidos cargados. Pulsa **Actualizar desde calendarios** para importar la temporada.")
        return

    st.caption(f"{len(partidos)} partidos encontrados · Cambia el estado directamente en la tabla y pulsa **Guardar cambios**.")

    df_raw = pd.DataFrame(partidos).reset_index(drop=True)
    ids_serie     = df_raw["id"].copy()
    estados_serie = df_raw["estado"].map(ESTADOS_DISPLAY).fillna("⬜ Sin contactar").copy()

    df_display = pd.DataFrame({
        "Fecha":             pd.to_datetime(df_raw["fecha"]).dt.strftime("%d/%m/%Y"),
        "Equipo local":      df_raw["equipo"],
        "Rival (visitante)": df_raw["rival"],
        "Estado":            estados_serie,
        "Deporte":           df_raw["deporte"],
        "Ciudad":            df_raw["ciudad"],
        "Pabellón":          df_raw.get("lugar", pd.Series([""] * len(df_raw))),
    }).reset_index(drop=True)

    edited = st.data_editor(
        df_display,
        column_config={
            "Estado": st.column_config.SelectboxColumn(
                "Estado",
                options=ESTADOS_LISTA,
                required=True,
            )
        },
        use_container_width=True,
        hide_index=True,
        key="cal_editor",
    )

    if st.button("💾 Guardar cambios de estado", type="primary"):
        cambios = 0
        for i in range(len(df_display)):
            if estados_serie.iloc[i] != edited.iloc[i]["Estado"]:
                nuevo_db = ESTADOS_DB.get(edited.iloc[i]["Estado"], "sin_contactar")
                try:
                    db.update_partido(ids_serie.iloc[i], estado=nuevo_db)
                    cambios += 1
                except Exception as e:
                    st.error(f"Error en fila {i}: {e}")
        if cambios:
            st.toast(f"✅ {cambios} estado(s) actualizados.")
            st.rerun()
        else:
            st.toast("Sin cambios que guardar.")


# ── Pantalla: Contactos ────────────────────────────────────────────────────────

def pantalla_contactos():
    st.title("📇 Contactos de equipos")
    st.caption("Base de datos de equipos visitantes.")

    col1, col2 = st.columns([2, 1])
    with col1:
        q = st.text_input("🔍 Buscar por nombre", placeholder="ej. CD Lugo")
    with col2:
        filtro = st.selectbox("Mostrar", ["Todos", "✅ Verificados", "⚠️ Sin verificar"])

    verificado_filter = None
    if filtro == "✅ Verificados":
        verificado_filter = True
    elif filtro == "⚠️ Sin verificar":
        verificado_filter = False

    try:
        contactos = db.get_contactos(verificado=verificado_filter, q=q or None)
    except RuntimeError as e:
        st.error(f"Supabase no configurado: {e}")
        return

    if not contactos:
        st.info("No hay contactos todavía. Se añaden automáticamente al buscar leads con IA.")
    else:
        verificados = sum(1 for c in contactos if c.get("verificado"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Total contactos", len(contactos))
        c2.metric("✅ Verificados", verificados)
        c3.metric("⚠️ Sin verificar", len(contactos) - verificados)
        st.divider()

        for c in contactos:
            nombre    = c.get("nombre", "")
            verificado = c.get("verificado", False)
            badge     = "✅" if verificado else "⚠️"

            emails = []
            if c.get("email"):
                emails.append(c["email"])
            if c.get("emails_extra"):
                for e in c["emails_extra"].split(","):
                    e = e.strip()
                    if e and e not in emails:
                        emails.append(e)

            with st.container(border=True):
                h1, h2 = st.columns([4, 1])
                with h1:
                    st.markdown(
                        f"**{badge} {nombre}** · `{c.get('deporte','') or ''}` · "
                        f"*{c.get('fuente','') or ''}*"
                        + (f" · confianza {c.get('confianza')}" if c.get("confianza") else "")
                    )
                with h2:
                    if st.button("🗑️ Borrar", key=f"del_{nombre}"):
                        try:
                            db._get_client().table("contactos").delete().eq(
                                "nombre", nombre.upper().strip()
                            ).execute()
                            st.toast(f"Contacto '{nombre}' eliminado.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                info = []
                if c.get("telefono"):
                    info.append(f"📞 {c['telefono']}")
                if c.get("web"):
                    info.append(f"🌐 [{c['web']}]({c['web']})")
                if c.get("instagram"):
                    info.append(f"📸 {c['instagram']}")
                if info:
                    st.caption(" · ".join(info))

                for email in emails:
                    st.markdown(f"✉️ `{email}`")

                nutri = c.get("nutricionista")
                if nutri or c.get("nutricionista_email") or c.get("nutricionista_instagram") or c.get("nutricionista_telefono"):
                    parts = []
                    if nutri:
                        parts.append(f"👤 {nutri}")
                    if c.get("nutricionista_telefono"):
                        parts.append(f"📞 {c['nutricionista_telefono']}")
                    if c.get("nutricionista_instagram"):
                        parts.append(f"📸 {c['nutricionista_instagram']}")
                    if c.get("nutricionista_email"):
                        parts.append(f"✉️ {c['nutricionista_email']}")
                    st.caption("Nutricionista: " + " · ".join(parts))

                btn1, btn2 = st.columns([1, 3])
                if not verificado:
                    if btn1.button("☑️ Verificar", key=f"ver_c_{nombre}"):
                        db.marcar_verificado(nombre)
                        st.toast(f"'{nombre}' marcado como verificado.")
                        st.rerun()

                with btn2:
                    with st.expander("✏️ Editar"):
                        with st.form(f"edit_{nombre}"):
                            e1, e2 = st.columns(2)
                            new_email    = e1.text_input("Email principal",  value=c.get("email") or "")
                            new_tel      = e2.text_input("Teléfono",         value=c.get("telefono") or "")
                            new_emails_x = e1.text_input("Emails extra (separados por coma)",
                                                          value=c.get("emails_extra") or "")
                            new_web      = e2.text_input("Web",              value=c.get("web") or "")
                            st.markdown("**Nutricionista / Dietista**")
                            n1, n2 = st.columns(2)
                            new_nutri      = n1.text_input("Nombre",
                                                            value=c.get("nutricionista") or "")
                            new_nutri_tel  = n2.text_input("Teléfono nutricionista",
                                                            value=c.get("nutricionista_telefono") or "")
                            new_nutri_em   = n1.text_input("Email nutricionista",
                                                            value=c.get("nutricionista_email") or "")
                            new_nutri_ig   = n2.text_input("Instagram nutricionista",
                                                            value=c.get("nutricionista_instagram") or "")
                            save_edit = st.form_submit_button("Guardar", type="primary")
                        if save_edit:
                            db.upsert_contacto({
                                "nombre":                    nombre,
                                "email":                     new_email or None,
                                "emails_extra":              new_emails_x or None,
                                "telefono":                  new_tel or None,
                                "web":                       new_web or None,
                                "nutricionista_nombre":      new_nutri or None,
                                "nutricionista_telefono":    new_nutri_tel or None,
                                "nutricionista_instagram":   new_nutri_ig or None,
                                "nutricionista_email":       new_nutri_em or None,
                                "verificado":                verificado,
                                "fuente":                    c.get("fuente", "manual"),
                                "deporte":                   c.get("deporte"),
                                "confianza":                 c.get("confianza"),
                                "instagram":                 c.get("instagram"),
                                "notas":                     c.get("notas"),
                            })
                            st.toast(f"'{nombre}' actualizado.")
                            st.rerun()

    st.divider()
    with st.expander("➕ Añadir contacto manualmente"):
        with st.form("nuevo_contacto"):
            nc1, nc2 = st.columns(2)
            nombre_new       = nc1.text_input("Nombre del club *")
            deporte_new      = nc2.selectbox("Deporte", ["FUTBOL", "BALONCESTO", "BALONMANO",
                                                          "VOLEIBOL", "HOCKEY PATINES"])
            email_new        = nc1.text_input("Email principal")
            telefono_new     = nc2.text_input("Teléfono")
            emails_extra_new = nc1.text_input("Emails extra (separados por coma)")
            web_new          = nc2.text_input("Web")
            st.markdown("**Nutricionista / Dietista**")
            nn1, nn2 = st.columns(2)
            nutri_new        = nn1.text_input("Nombre")
            nutri_tel_new    = nn2.text_input("Teléfono nutricionista")
            nutri_email_new  = nn1.text_input("Email nutricionista")
            nutri_ig_new     = nn2.text_input("Instagram nutricionista")
            notas_new        = st.text_area("Notas", height=60)
            submitted        = st.form_submit_button("Guardar", type="primary")

        if submitted:
            if not nombre_new.strip():
                st.error("El nombre del club es obligatorio.")
            else:
                try:
                    db.upsert_contacto({
                        "nombre":                    nombre_new,
                        "deporte":                   deporte_new,
                        "email":                     email_new or None,
                        "emails_extra":              emails_extra_new or None,
                        "telefono":                  telefono_new or None,
                        "web":                       web_new or None,
                        "nutricionista_nombre":      nutri_new or None,
                        "nutricionista_telefono":    nutri_tel_new or None,
                        "nutricionista_instagram":   nutri_ig_new or None,
                        "nutricionista_email":       nutri_email_new or None,
                        "notas":                     notas_new or None,
                        "verificado":                True,
                        "fuente":                    "manual",
                    })
                    st.success(f"Contacto '{nombre_new}' guardado.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not require_login():
        return

    st.sidebar.markdown("### 🍔 ATM Catering")
    seccion = st.sidebar.radio(
        "Menú",
        [
            "🏠 Inicio",
            "📅 Partidos de la semana",
            "💰 Pedidos e ingresos",
            "🗓️ Calendario de temporada",
            "📇 Contactos",
        ],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    logout_button()

    if seccion.startswith("🏠"):
        pantalla_inicio()
    elif seccion.startswith("📅"):
        pantalla_partidos()
    elif seccion.startswith("💰"):
        pantalla_pedidos()
    elif seccion.startswith("🗓️"):
        pantalla_calendario()
    elif seccion.startswith("📇"):
        pantalla_contactos()


main()
