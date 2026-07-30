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

import pandas as pd
import streamlit as st

# Copiar secrets de Streamlit Cloud a os.environ para que db.py y ai_search.py
# los encuentren con os.environ.get() igual que en local con .env
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

from catering_web.auth import logout_button, require_login
from sports_catering import db, engine
from sports_catering.config import load_config
from sports_catering.contact_finder import find_contact
from sports_catering.html_report import (
    EMAIL_TEMPLATE,
    SUBJECT_TEMPLATE,
    _format_date_es,
    _wa_link,
)

st.set_page_config(page_title="ATM Catering Deportivo", page_icon="🍔", layout="wide")

DEPORTES = ["Todos", "FUTBOL", "BALONCESTO", "BALONMANO", "VOLEIBOL", "HOCKEY PATINES"]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_subject(lead: dict) -> str:
    return SUBJECT_TEMPLATE.format(rival=lead.get("rival", ""), ciudad=lead.get("ciudad", "Asturias"))


def _mailto(lead: dict) -> str:
    to = urllib.parse.quote(lead.get("email") or "")
    params = urllib.parse.urlencode({"subject": _build_subject(lead), "body": EMAIL_TEMPLATE})
    return f"mailto:{to}?{params}"


def _hora_str(hora) -> str:
    if not hora:
        return ""
    return f"{int(hora):02d}:{round((hora % 1) * 60):02d}"


@st.cache_data(show_spinner=False)
def _cargar_config():
    return load_config()


# ─── Pantalla: Partidos de la semana ──────────────────────────────────────────

EQUIPOS_ASTURIANOS = {"REAL OVIEDO", "SPORTING GIJON", "SPORTING GIJÓN"}


def pantalla_partidos():
    st.title("📅 Partidos de la semana")
    st.caption("Equipos visitantes que van a jugar en Asturias. Datos del calendario guardado en Supabase.")

    cfg = _cargar_config()
    ventana = cfg.get("lead_window_days", [14, 21])

    col1, col2, col3 = st.columns([1.3, 1.3, 1.3])
    with col1:
        d_ini = st.number_input("Desde (días)", min_value=0, max_value=120, value=int(ventana[0]))
    with col2:
        d_fin = st.number_input("Hasta (días)", min_value=1, max_value=180, value=int(ventana[1]))
    with col3:
        usar_ia = st.toggle("Buscar contactos con IA", value=True,
                            help="Si el equipo no está en la base de datos, busca su contacto en Internet.")

    if st.button("🔍 Buscar partidos", type="primary"):
        now = datetime.now(timezone.utc)
        w_start = now + timedelta(days=d_ini)
        w_end   = now + timedelta(days=d_fin)

        try:
            todos = db.get_partidos(solo_proximos=True)
        except Exception as e:
            st.error(f"Error al cargar partidos: {e}")
            st.info("Comprueba que SUPABASE_URL y SUPABASE_KEY están en los secrets.")
            return

        # Filtrar por ventana de fechas y excluir derbis asturianos
        leads = []
        for p in todos:
            try:
                fecha = datetime.fromisoformat(str(p["fecha"]).replace("Z", "+00:00"))
                if w_start <= fecha <= w_end and p.get("rival", "").upper() not in EQUIPOS_ASTURIANOS:
                    leads.append(p)
            except Exception:
                pass

        if leads:
            with st.spinner("Buscando contactos..."):
                for m in leads:
                    m.update(find_contact(m["rival"], use_ai=usar_ia,
                                          city=m.get("ciudad", ""), sport=m.get("deporte", "")))

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
    fecha = lead.get("date") or lead.get("fecha")
    fecha_str = _format_date_es(fecha) if isinstance(fecha, datetime) else str(fecha or "")
    status = lead.get("status", "missing")
    rival = lead.get("rival", "")
    verificado = lead.get("verificado", False)

    badge = {
        "found_exact":   "✅ Verificado" if verificado else "📋 En base de datos",
        "found_partial": "✅ Verificado" if verificado else "📋 En base de datos",
        "found_fuzzy":   "✅ Verificado" if verificado else "📋 En base de datos",
        "found_ai":      f"🤖 IA · confianza {lead.get('confianza', 'media')}",
        "missing":       "⚠️ Sin contacto",
    }.get(status, status)

    # Recopilar todos los emails disponibles
    emails = lead.get("emails") or []
    if not emails and lead.get("email"):
        emails = [lead["email"]]
    if lead.get("emails_extra"):
        for e in lead["emails_extra"].split(","):
            e = e.strip()
            if e and e not in emails:
                emails.append(e)

    with st.container(border=True):
        # Cabecera
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{lead.get('equipo','')} vs {rival}**  \n"
                        f"`{lead.get('deporte','')}` · 📅 {fecha_str} {_hora_str(lead.get('hora'))} · "
                        f"📍 {lead.get('lugar') or lead.get('ciudad','')}")
        with c2:
            st.markdown(f"<div style='text-align:right'>{badge}</div>", unsafe_allow_html=True)

        if status == "missing":
            q = urllib.parse.quote_plus(f"{rival} club deportivo email contacto nutricionista")
            st.link_button("🔍 Buscar en Google", f"https://www.google.com/search?q={q}")
            return

        # ── Contactos del club ──────────────────────────────────────────
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
                mailto = urllib.parse.urlencode({"subject": _build_subject(lead), "body": EMAIL_TEMPLATE})
                col_btn.link_button("Enviar", f"mailto:{urllib.parse.quote(email)}?{mailto}",
                                    key=f"mail_{rival}_{email}")

        wa = _wa_link(lead.get("telefono")) if lead.get("telefono") else None
        if wa:
            st.link_button("💬 WhatsApp", wa)

        # ── Nutricionista ───────────────────────────────────────────────
        nutri_nombre = lead.get("nutricionista_nombre") or lead.get("nutricionista")
        nutri_email  = lead.get("nutricionista_email")
        nutri_ig     = lead.get("nutricionista_instagram")
        nutri_ok     = lead.get("nutricionista_confirmado", False)

        if nutri_nombre or nutri_email or nutri_ig:
            st.divider()
            confirmado_txt = " ✓ confirmado" if nutri_ok else " (sin confirmar)"
            st.markdown(f"**Nutricionista/Dietista**{confirmado_txt}")
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
                mailto_n = urllib.parse.urlencode({"subject": _build_subject(lead), "body": EMAIL_TEMPLATE})
                col_nb.link_button("Enviar", f"mailto:{urllib.parse.quote(nutri_email)}?{mailto_n}",
                                   key=f"mail_nutri_{rival}")

        # ── Verificar + correo ──────────────────────────────────────────
        st.divider()
        col_v, col_exp = st.columns([1, 3])
        if not verificado and lead.get("nombre"):
            if col_v.button("☑️ Verificar", key=f"ver_{rival}"):
                try:
                    db.marcar_verificado(lead["nombre"])
                    st.toast(f"Contacto de {rival} marcado como verificado.")
                    st.rerun()
                except RuntimeError as e:
                    st.warning(str(e))

        with col_exp:
            with st.expander("Ver correo redactado"):
                st.text_input("Asunto", value=_build_subject(lead), key=f"subj_{id(lead)}")
                st.text_area("Cuerpo", value=EMAIL_TEMPLATE, height=200, key=f"body_{id(lead)}")


# ─── Pantalla: Calendario de temporada ────────────────────────────────────────

def pantalla_calendario():
    st.title("🗓️ Calendario de temporada")
    st.caption("Todos los partidos en casa de la temporada. Actualiza cuando quieras para refrescar los datos.")

    cfg = _cargar_config()
    teams = cfg.get("teams", [])

    col1, col2, col3 = st.columns(3)
    with col1:
        ciudad_f = st.selectbox("Ciudad", ["Todas", "OVIEDO", "GIJON"])
    with col2:
        deporte_f = st.selectbox("Deporte", DEPORTES)
    with col3:
        solo_proximos = st.toggle("Solo próximos", value=True)

    if st.button("🔄 Actualizar desde calendarios",
                 help="Descarga los calendarios de todos los equipos automáticos (~30 seg)"):
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
        st.markdown(
            "Sube el Excel del calendario de liga. "
            "Debe tener columnas: **J · Fecha · Local · Fuera** (formato LaLiga). "
            "Solo se importan los partidos en casa de Oviedo y Sporting."
        )
        archivo = st.file_uploader("Selecciona el Excel", type=["xlsx"], key="cal_upload")
        temporada_inp = st.text_input("Temporada", value="2026-27", key="cal_temporada")

        if archivo:
            try:
                raw = pd.read_excel(archivo, skiprows=1)
                raw.columns = ["jornada", "fecha", "local", "esc_local",
                               "gol1", "gol2", "esc_visit", "visitante"]
                raw["jornada"] = raw["jornada"].ffill()
                raw["fecha"]   = pd.to_datetime(raw["fecha"].ffill(), errors="coerce")
                raw["local"]     = raw["local"].astype(str).str.strip()
                raw["visitante"] = raw["visitante"].astype(str).str.strip()

                _MAP = {
                    "OVIEDO":   ("REAL OVIEDO",    "OVIEDO", "CARLOS TARTIERE"),
                    "SPORTING": ("SPORTING GIJON",  "GIJON",  "EL MOLINON"),
                }
                casa = raw[raw["local"].str.upper().isin(_MAP)].copy()

                if casa.empty:
                    st.warning("No se encontraron partidos de Oviedo ni Sporting en el archivo.")
                else:
                    preview = casa[["jornada", "fecha", "local", "visitante"]].copy()
                    preview["jornada"] = preview["jornada"].astype(int)
                    preview["fecha"]   = preview["fecha"].dt.strftime("%d/%m/%Y")
                    st.caption(f"{len(casa)} partidos en casa encontrados:")
                    st.dataframe(preview.rename(columns={
                        "jornada": "J", "fecha": "Fecha",
                        "local": "Local", "visitante": "Visitante",
                    }), use_container_width=True, hide_index=True)

                    if st.button("⬆️ Guardar en Supabase", type="primary", key="btn_import_cal"):
                        rows = []
                        for _, r in casa.iterrows():
                            nombre, ciudad, lugar = _MAP[r["local"].upper()]
                            rows.append({
                                "equipo":    nombre,
                                "ciudad":    ciudad,
                                "deporte":   "FUTBOL",
                                "rival":     r["visitante"].upper(),
                                "fecha":     r["fecha"].replace(hour=12, tzinfo=timezone.utc),
                                "jornada":   int(r["jornada"]),
                                "lugar":     lugar,
                                "source":    "excel_import",
                                "temporada": temporada_inp.strip(),
                            })
                        try:
                            saved = db.upsert_partidos(rows)
                            st.success(f"✅ {saved} partidos importados correctamente.")
                            st.rerun()
                        except RuntimeError as e:
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
        st.info("Añade SUPABASE_URL y SUPABASE_KEY a los secrets.")
        return

    if not partidos:
        st.info("No hay partidos cargados. Pulsa **Actualizar desde calendarios** para importar la temporada.")
        return

    st.caption(f"{len(partidos)} partidos encontrados")

    df = pd.DataFrame(partidos)
    df["Fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%d/%m/%Y %H:%M")
    df = df.rename(columns={
        "equipo":  "Equipo local",
        "rival":   "Rival (visitante)",
        "deporte": "Deporte",
        "ciudad":  "Ciudad",
        "lugar":   "Pabellón",
    })[["Fecha", "Equipo local", "Rival (visitante)", "Deporte", "Ciudad", "Pabellón"]]

    st.dataframe(df, use_container_width=True, hide_index=True)


# ─── Pantalla: Contactos ──────────────────────────────────────────────────────

def pantalla_contactos():
    st.title("📇 Contactos de equipos")
    st.caption("Base de datos de equipos visitantes. Marca como verificado los contactos que hayas comprobado.")

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
        st.info("Añade SUPABASE_URL y SUPABASE_KEY a los secrets.")
        return

    if not contactos:
        st.info("No hay contactos todavía. Se añaden automáticamente cuando se buscan leads con IA.")
        return

    verificados = sum(1 for c in contactos if c.get("verificado"))
    c1, c2, c3 = st.columns(3)
    c1.metric("Total contactos", len(contactos))
    c2.metric("✅ Verificados", verificados)
    c3.metric("⚠️ Sin verificar", len(contactos) - verificados)
    st.divider()

    df = pd.DataFrame(contactos)
    cols_show = ["nombre", "deporte", "email", "telefono", "fuente", "confianza", "verificado"]
    for col in cols_show:
        if col not in df.columns:
            df[col] = None

    edited = st.data_editor(
        df[cols_show].copy(),
        column_config={
            "verificado": st.column_config.CheckboxColumn(
                "✅ Verificado",
                help="Marca si has comprobado que este contacto es válido",
                default=False,
            ),
            "nombre":    st.column_config.TextColumn("Club", disabled=True),
            "deporte":   st.column_config.TextColumn("Deporte", disabled=True),
            "email":     st.column_config.TextColumn("Email"),
            "telefono":  st.column_config.TextColumn("Teléfono"),
            "fuente":    st.column_config.TextColumn("Fuente", disabled=True),
            "confianza": st.column_config.TextColumn("Confianza IA", disabled=True),
        },
        use_container_width=True,
        hide_index=True,
        key="contacts_editor",
        num_rows="fixed",
    )

    if st.button("💾 Guardar cambios", type="primary"):
        cambios = 0
        for i, row in edited.iterrows():
            orig = contactos[i]
            if (row.get("verificado") != orig.get("verificado")
                    or row.get("email") != orig.get("email")
                    or row.get("telefono") != orig.get("telefono")):
                db.upsert_contacto({
                    "nombre":    row["nombre"],
                    "email":     row.get("email"),
                    "telefono":  row.get("telefono"),
                    "verificado": bool(row.get("verificado", False)),
                    "fuente":    orig.get("fuente", "manual"),
                    "deporte":   orig.get("deporte"),
                    "confianza": orig.get("confianza"),
                    "web":       orig.get("web"),
                    "instagram": orig.get("instagram"),
                    "contacto":  orig.get("contacto"),
                    "notas":     orig.get("notas"),
                })
                cambios += 1
        if cambios:
            st.success(f"✅ {cambios} contacto(s) actualizado(s).")
            st.cache_data.clear()
            st.rerun()
        else:
            st.info("No hay cambios.")

    with st.expander("➕ Añadir contacto manualmente"):
        with st.form("nuevo_contacto"):
            nc1, nc2 = st.columns(2)
            nombre_new   = nc1.text_input("Nombre del club *")
            deporte_new  = nc2.selectbox("Deporte", ["FUTBOL", "BALONCESTO", "BALONMANO", "VOLEIBOL", "HOCKEY PATINES"])
            email_new    = nc1.text_input("Email")
            telefono_new = nc2.text_input("Teléfono")
            web_new      = nc1.text_input("Web")
            notas_new    = st.text_area("Notas", height=80)
            submitted    = st.form_submit_button("Guardar", type="primary")

        if submitted:
            if not nombre_new.strip():
                st.error("El nombre del club es obligatorio.")
            else:
                try:
                    db.upsert_contacto({
                        "nombre":    nombre_new,
                        "deporte":   deporte_new,
                        "email":     email_new or None,
                        "telefono":  telefono_new or None,
                        "web":       web_new or None,
                        "notas":     notas_new or None,
                        "verificado": True,
                        "fuente":    "manual",
                    })
                    st.success(f"Contacto '{nombre_new}' guardado.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not require_login():
        return

    st.sidebar.markdown("### 🍔 ATM Catering")
    seccion = st.sidebar.radio(
        "Menú",
        ["📅 Partidos de la semana", "🗓️ Calendario de temporada", "📇 Contactos"],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    logout_button()

    if seccion.startswith("📅"):
        pantalla_partidos()
    elif seccion.startswith("🗓️"):
        pantalla_calendario()
    elif seccion.startswith("📇"):
        pantalla_contactos()


main()
