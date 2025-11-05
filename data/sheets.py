"""Google Sheets access and authentication."""
import json
import streamlit as st
import pandas as pd
from config.secrets import read_secrets, forms_sheet_id


@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Cliente autenticado de Google Sheets."""
    from google.oauth2.service_account import Credentials
    import gspread
    
    sa_json = read_secrets("GOOGLE_SERVICE_ACCOUNT", "")
    if not sa_json:
        raise RuntimeError("Falta GOOGLE_SERVICE_ACCOUNT en secrets/env.")
    
    sa_info = json.loads(sa_json)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)


@st.cache_data(ttl=60, show_spinner=False)
def sheet_to_df(sheet_id: str, tab: str) -> pd.DataFrame:
    """Lee hoja de cálculo (nombre tolerante a errores comunes)."""
    gc = get_gspread_client()
    sh = gc.open_by_key(sheet_id)
    
    try:
        return pd.DataFrame(sh.worksheet(tab).get_all_records())
    except Exception:
        for ws in sh.worksheets():
            if tab.lower() in ws.title.lower():
                return pd.DataFrame(ws.get_all_records())
        ws = sh.get_worksheet(0)
        st.warning(f"No se encontró la pestaña '{tab}'. Usando '{ws.title}'.")
        return pd.DataFrame(ws.get_all_records())


def write_df_to_sheet(sheet_id: str, tab_name: str, df: pd.DataFrame, clear_existing: bool = True):
    """
    Escribe un DataFrame a un tab de Google Sheets.
    
    Args:
        sheet_id: ID del Google Sheet
        tab_name: Nombre del tab (lo crea si no existe)
        df: DataFrame a escribir
        clear_existing: Si True, limpia el contenido existente antes de escribir
    """
    import gspread
    
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(sheet_id)
        
        # Intentar obtener el worksheet, si no existe, crearlo
        try:
            worksheet = sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=tab_name, rows=1000, cols=20)
        
        # Limpiar contenido existente si se solicita
        if clear_existing:
            worksheet.clear()
        
        # Limpiar valores problemáticos antes de exportar
        df_clean = df.replace([float('inf'), float('-inf')], None).fillna("")
        
        # Convertir DataFrame a lista de listas (incluyendo headers)
        values = [df_clean.columns.tolist()] + df_clean.astype(str).values.tolist()
        
        # Escribir datos
        worksheet.update(values, value_input_option='RAW')
        
        return True
    except Exception as e:
        raise Exception(f"Error escribiendo a Google Sheets: {e}")

