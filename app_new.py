"""
app.py — Streamlit router and layout only
Main entry point for the Information Integrity Workshop application.
"""
import streamlit as st

# Import page renderers (to be migrated to pages/ directory)
# For now, keeping them in a separate pages module
from app import (
    render_setup_trainer_page,
    render_introduction_page,
    render_form1_page,
    render_analysis_trends_page,
    render_form2_page,
    render_news_flow_page,
    render_explanation_page,
    render_workshop_insights_page,
)

# ---------- CONFIG BÁSICA ----------
st.set_page_config(
    page_title="Taller • Integridad de la Información",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- ROUTER ----------
ROUTES = {
    "Cuestionario para formador": render_setup_trainer_page,      
    "Introducción al taller": render_introduction_page,           
    "Cuestionario 1": render_form1_page,                          
    "Análisis y tema dominante": render_analysis_trends_page,   
    "Cuestionario 2": render_form2_page,                          
    "Noticias del taller": render_news_flow_page,
    "Explicacion del taller": render_explanation_page,                
    "Análisis final del taller": render_workshop_insights_page,   
}


def main():
    """Main application router."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = list(ROUTES.keys())[0]

    with st.sidebar:
        st.markdown("### 🧭 Navegación")
        pages = list(ROUTES.keys())
        idx = pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0
        page = st.radio("Ir a", pages, index=idx, label_visibility="collapsed")

    st.session_state.current_page = page

    if st.session_state.get("selected_page") in ROUTES:
        st.session_state.current_page = st.session_state.selected_page
        st.session_state.selected_page = None

    ROUTES.get(st.session_state.current_page, lambda: st.info("Selecciona una página."))()


if __name__ == "__main__":
    main()

