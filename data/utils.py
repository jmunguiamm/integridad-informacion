"""Data utility functions for date handling and column detection."""
import pandas as pd
import streamlit as st
from datetime import datetime
from dateutil import parser as date_parser
from .sheets import sheet_to_df
from config.secrets import forms_sheet_id, read_secrets


def get_date_column_name(df: pd.DataFrame) -> str:
    """Obtiene el nombre de la columna de fecha. Por defecto es 'Marca temporal' (primera columna de Google Forms)."""
    if len(df.columns) == 0:
        return None
    
    # La columna "Marca temporal" es típicamente la primera columna en Google Forms
    first_col = df.columns[0]
    
    # Verificar si es "Marca temporal" o alguna variación (búsqueda flexible)
    first_col_lower = first_col.lower()
    if "marca temporal" in first_col_lower or "timestamp" in first_col_lower or "fecha" in first_col_lower or "date" in first_col_lower:
        return first_col
    
    # Si no, buscar explícitamente en todas las columnas
    for col in df.columns:
        col_lower = col.lower()
        if "marca temporal" in col_lower or "timestamp" in col_lower or (col == df.columns[0] and "fecha" in col_lower):
            return col
    
    # Si no encuentra explícitamente, usar la primera columna (asumiendo que es la marca temporal por convención de Google Forms)
    return first_col


def normalize_date(date_value) -> str:
    """Normaliza una fecha a formato string YYYY-MM-DD para comparación."""
    if pd.isna(date_value):
        return None
    
    try:
        if isinstance(date_value, str):
            # Intentar parsear la fecha
            parsed = date_parser.parse(date_value, fuzzy=True)
            return parsed.strftime('%Y-%m-%d')
        elif isinstance(date_value, (datetime, pd.Timestamp)):
            return date_value.strftime('%Y-%m-%d')
    except:
        pass
    
    return str(date_value)


def get_available_workshop_dates():
    """Obtiene las fechas disponibles del Form 0 para seleccionar talleres.

    Preferimos la columna específica de configuración del taller
    **'Fecha de implementación'** si existe en el Form 0. Esto evita
    confusiones con la zona horaria de la marca temporal de Google Forms,
    y garantiza que la lista muestre la fecha real del taller y no el
    momento en que se respondió el formulario."""
    FORMS_SHEET_ID = forms_sheet_id()
    FORM0_TAB = read_secrets("FORM0_TAB", "")
    
    if not FORM0_TAB:
        return []
    
    try:
        df0 = sheet_to_df(FORMS_SHEET_ID, FORM0_TAB)
        if df0.empty:
            return []

        # 1️⃣ Intentar usar la columna específica "Fecha de implementación"
        impl_col = None
        for col in df0.columns:
            col_clean = col.strip().lower()
            if col_clean == "fecha de implementación".lower() or col_clean == "fecha de implementacion":
                impl_col = col
                break

        if impl_col:
            # Normalizar usando la fecha de implementación del taller
            df0['_normalized_date'] = df0[impl_col].apply(normalize_date)
        else:
            # 2️⃣ Fallback: usar la columna de marca temporal detectada automáticamente
            date_col = get_date_column_name(df0)
            if not date_col:
                return []
            df0['_normalized_date'] = df0[date_col].apply(normalize_date)

        # Normalizar fechas y obtener valores únicos (más reciente primero)
        df0 = df0.dropna(subset=['_normalized_date'])
        
        if df0.empty:
            return []
        
        unique_dates = sorted(df0['_normalized_date'].unique(), reverse=True)
        return unique_dates
        
    except Exception as e:
        st.warning(f"Error obteniendo fechas del Form 0: {e}")
        return []


def load_joined_responses():
    """Lee Form0, Form1, Form2 del MISMO Sheet (FORMS_SHEET_ID) y une por 'tarjeta'.
    Filtra las respuestas por la fecha seleccionada en session_state."""
    FORMS_SHEET_ID = forms_sheet_id()
    
    # Obtener la fecha del taller seleccionada
    workshop_date = st.session_state.get("selected_workshop_date")
    
    forms = []
    mapping = [
        ("FORM0_TAB", "F0"),
        ("FORM1_TAB", "F1"),
        ("FORM2_TAB", "F2"),
    ]
    
    from config.secrets import read_secrets
    from .cleaning import filter_df_by_date
    
    for tab_key, tag in mapping:
        tab = read_secrets(tab_key, "")
        if not tab:
            continue
        try:
            df = sheet_to_df(FORMS_SHEET_ID, tab)
            df.columns = [c.strip() for c in df.columns]
            df["source_form"] = tag
            
            # Filtrar por fecha del taller seleccionada (excepto Form 0 que usamos como referencia)
            if tag != "F0" and workshop_date:
                df = filter_df_by_date(df, workshop_date)
            
            forms.append(df)
        except Exception as e:
            st.warning(f"No pude leer pestaña {tab_key}='{tab}': {e}")

    if not forms:
        return pd.DataFrame(), None

    df_all = pd.concat(forms, ignore_index=True)

    # Detectar la columna clave de unión (número de tarjeta)
    key_candidates = [c for c in df_all.columns if "tarjeta" in c.lower()]
    if key_candidates:
        key = key_candidates[0]
        df_all[key] = df_all[key].astype(str).str.strip()
    else:
        key = None

    return df_all, key

