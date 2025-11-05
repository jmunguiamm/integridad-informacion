"""Configuration and secrets management."""
import os
import streamlit as st


def read_secrets(key: str, default: str = "") -> str:
    """Lee secrets desde entorno o Streamlit Cloud."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def forms_sheet_id() -> str:
    """Obtiene el ID del Google Sheet de formularios."""
    sid = read_secrets("FORMS_SHEET_ID", "")
    if not sid:
        raise RuntimeError("Falta FORMS_SHEET_ID en secrets/env.")
    return sid

