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

    # En Cloud el secreto puede llegar como dict. Local suele ser string JSON.
    if isinstance(sa_json, str):
        sa_info = json.loads(sa_json)
    elif isinstance(sa_json, dict):
        sa_info = sa_json
    else:
        raise TypeError("GOOGLE_SERVICE_ACCOUNT debe ser string JSON o dict.")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)


@st.cache_data(ttl=60, show_spinner=False)
def sheet_to_df(sheet_id: str, tab: str, cache_buster: str | None = None) -> pd.DataFrame:
    """Lee hoja de cálculo (nombre tolerante a errores comunes).

    cache_buster se usa únicamente para invalidar manualmente el caché de Streamlit.
    """
    _ = cache_buster  # Referencia para evitar advertencias de variable no usada.
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


def append_df_to_sheet(sheet_id: str, tab_name: str, df: pd.DataFrame):
    """
    Añade filas de un DataFrame a un tab existente sin limpiar lo que ya hay.
    Si el tab no existe, se crea y se escribe el encabezado.
    """
    import gspread

    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("Se requiere un DataFrame válido para anexar.")

    if df.empty:
        return False

    df_clean = df.replace([float('inf'), float('-inf')], None).fillna("")
    rows = df_clean.astype(str).values.tolist()
    if not rows:
        return False

    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(sheet_id)
        try:
            worksheet = sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=tab_name, rows=max(1000, len(rows) + 5), cols=max(20, len(df_clean.columns)))

        existing_values = worksheet.get_all_values()

        to_append = []
        if not existing_values:
            to_append.append(df_clean.columns.tolist())
            start_row = 1
        else:
            start_row = len(existing_values) + 1

        to_append.extend(rows)

        required_rows = start_row + len(to_append) - 1
        if worksheet.row_count < required_rows:
            worksheet.add_rows(required_rows - worksheet.row_count)

        worksheet.update(f"A{start_row}", to_append, value_input_option='RAW')
        return True
    except Exception as e:
        raise Exception(f"Error anexando datos a Google Sheets: {e}")