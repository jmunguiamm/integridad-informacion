"""Utility components for UI."""
import streamlit as st


def autorefresh_toggle(key="auto_refresh_key", millis=60_000):
    """Botón de auto-refresh opcional."""
    auto = st.toggle("🔄 Auto-refresh cada 60s", value=False)
    if auto:
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=millis, key=key)
        except Exception:
            st.info("Para auto-refresh instala `streamlit-autorefresh`.")
    return auto

