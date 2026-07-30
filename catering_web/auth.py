"""Login sencillo por contraseña para la web de catering."""
import os

import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _expected_password() -> str:
    # Prioridad: st.secrets (Railway/Streamlit) → variable de entorno → default local
    try:
        if "CATERING_PASSWORD" in st.secrets:
            return st.secrets["CATERING_PASSWORD"]
    except Exception:
        pass
    return os.environ.get("CATERING_PASSWORD", "atm2026")


def require_login() -> bool:
    """
    Muestra la pantalla de login si no se ha entrado.
    Devuelve True si el usuario está autenticado.
    """
    if st.session_state.get("autenticado"):
        return True

    st.markdown("## 🍔 ATM Catering Deportivo")
    st.caption("Acceso restringido al personal de ATM Burgers")

    with st.form("login"):
        pwd = st.text_input("Contraseña", type="password")
        ok = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if ok:
        if pwd == _expected_password():
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")

    if _expected_password() == "atm2026":
        st.info("⚠️ Estás usando la contraseña por defecto. Cámbiala con la variable "
                "de entorno `CATERING_PASSWORD` antes de publicar la web.")
    return False


def logout_button():
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["autenticado"] = False
        st.rerun()
