"""Navigation utilities for pages."""
import streamlit as st


def navigation_buttons(current_page: str, page_order: list[str]):
    """
    Show consistent navigation buttons across all pages.
    Assumes you are using `st.session_state["current_page"]` to control navigation.
    """
    idx = page_order.index(current_page)
    col1, col2 = st.columns([1, 1])

    with col1:
        if idx > 0:
            if st.button("⬅️ Volver", key=f"back_{current_page}"):
                st.session_state["current_page"] = page_order[idx - 1]
                st.rerun()

    with col2:
        if idx < len(page_order) - 1:
            if st.button("Siguiente ➡️", key=f"next_{current_page}"):
                st.session_state["current_page"] = page_order[idx + 1]
                st.rerun()

