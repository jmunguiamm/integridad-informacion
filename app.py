# app.py — Taller Integridad de la Información (versión con mejoras de navegación/QR/UX)

import os, json, re, time
from io import BytesIO
import pandas as pd
import streamlit as st
import difflib
from datetime import datetime
from dateutil import parser as date_parser


# ---------- CONFIG BÁSICA ----------
st.set_page_config(
    page_title="Taller • Integridad de la Información",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
    )

# ---------- UTILIDADES ----------
def _forms_sheet_id() -> str:
    sid = _read_secrets("FORMS_SHEET_ID", "")
    if not sid:
        raise RuntimeError("Falta FORMS_SHEET_ID en secrets/env.")
    return sid

def _read_secrets(key: str, default: str = ""):
    """Lee secrets desde entorno o Streamlit Cloud."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

@st.cache_resource(show_spinner=False)
def _get_gspread_client():
    """Cliente autenticado de Google Sheets."""
    from google.oauth2.service_account import Credentials
    import gspread
    sa_json = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")
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
def _sheet_to_df(sheet_id: str, tab: str) -> pd.DataFrame:
    """Lee hoja de cálculo (nombre tolerante a errores comunes)."""
    gc = _get_gspread_client()
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

def _get_date_column_name(df: pd.DataFrame) -> str:
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

def _normalize_date(date_value) -> str:
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

def _get_available_workshop_dates():
    """Obtiene las fechas disponibles del Form 0 para seleccionar talleres."""
    FORMS_SHEET_ID = _forms_sheet_id()
    FORM0_TAB = _read_secrets("FORM0_TAB", "")
    
    if not FORM0_TAB:
        return []
    
    try:
        df0 = _sheet_to_df(FORMS_SHEET_ID, FORM0_TAB)
        if df0.empty:
            return []
        
        # Obtener columna de fecha (Marca temporal)
        date_col = _get_date_column_name(df0)
        if not date_col:
            return []
        
        # Normalizar fechas y obtener valores únicos
        df0['_normalized_date'] = df0[date_col].apply(_normalize_date)
        df0 = df0.dropna(subset=['_normalized_date'])
        
        if df0.empty:
            return []
        
        # Obtener fechas únicas ordenadas (más reciente primero)
        unique_dates = sorted(df0['_normalized_date'].unique(), reverse=True)
        return unique_dates
        
    except Exception as e:
        st.warning(f"Error obteniendo fechas del Form 0: {e}")
        return []

def _filter_df_by_date(df: pd.DataFrame, target_date: str) -> pd.DataFrame:
    """Filtra un DataFrame por fecha usando la columna 'Marca temporal' (primera columna)."""
    if df.empty or not target_date:
        return df
    
    # Obtener columna de fecha (Marca temporal) - siempre usar la primera columna si no se encuentra explícitamente
    date_col = _get_date_column_name(df)
    
    # Si no hay columna de fecha, usar la primera columna (asumiendo que es la marca temporal)
    if not date_col and len(df.columns) > 0:
        date_col = df.columns[0]
    
    if not date_col:
        # Si realmente no hay columnas, retornar sin filtrar
        return df
    
    # Normalizar fechas y filtrar
    df_copy = df.copy()
    try:
        df_copy['_normalized_date'] = df_copy[date_col].apply(_normalize_date)
        filtered = df_copy[df_copy['_normalized_date'] == target_date]
        
        if not filtered.empty:
            filtered = filtered.drop(columns=['_normalized_date'])
            return filtered
    except Exception as e:
        # Si hay error en el filtrado, retornar el DataFrame original
        return df
    
    return pd.DataFrame()

def _normalize_form_data(form1: pd.DataFrame, form2: pd.DataFrame, workshop_date: str = None, show_debug: bool = False):
    """
    Transforma Form1 y Form2 en formato normalizado según el esquema especificado.
    
    Args:
        form1: DataFrame del Form1
        form2: DataFrame del Form2
        workshop_date: Fecha del taller para filtrar (opcional)
        show_debug: Si True, muestra información de debug en Streamlit
    
    Returns:
        Tupla (DataFrame normalizado, DataFrame largo intermedio) o DataFrame normalizado si show_debug=False
        DataFrame normalizado con columnas: Taller, Marca temporal, Encuadre, Número de tarjeta, Género, Pregunta, Valor
    """
    # Filtrar por fecha si se especifica
    if workshop_date:
        if show_debug:
            st.write(f"🔍 Filtrando por fecha del taller: {workshop_date}")
            st.write(f"  - Form1 antes del filtro: {len(form1)} filas")
            st.write(f"  - Form2 antes del filtro: {len(form2)} filas")
        
        form1_filtered = _filter_df_by_date(form1.copy(), workshop_date)
        form2_filtered = _filter_df_by_date(form2.copy(), workshop_date)
        
        if show_debug:
            st.write(f"  - Form1 después del filtro: {len(form1_filtered)} filas")
            st.write(f"  - Form2 después del filtro: {len(form2_filtered)} filas")
            
            if form1_filtered.empty:
                st.warning("⚠️ Form1 quedó vacío después del filtrado por fecha. Verifica que la fecha coincida.")
            if form2_filtered.empty:
                st.warning("⚠️ Form2 quedó vacío después del filtrado por fecha. Verifica que la fecha coincida.")
        
        form1 = form1_filtered
        form2 = form2_filtered
    
    # Verificar que los DataFrames no estén vacíos después del filtrado
    if form1.empty:
        if show_debug:
            st.error("❌ Form1 está vacío. No se puede procesar.")
        return (pd.DataFrame(), pd.DataFrame()) if show_debug else pd.DataFrame()
    
    if form2.empty:
        if show_debug:
            st.error("❌ Form2 está vacío. No se puede procesar.")
        return (pd.DataFrame(), pd.DataFrame()) if show_debug else pd.DataFrame()
    
    # === 1️⃣ Preparar Form1 base ===
    # Buscar columnas relevantes (flexible con nombres)
    form1_cols = {col.lower(): col for col in form1.columns}
    
    if show_debug:
        st.write("🔍 Buscando columnas en Form1...")
        st.write(f"Total columnas: {len(form1.columns)}")
    
    # Buscar columna de tarjeta - buscar "tarjeta" en cualquier parte del nombre
    tarjeta_col = None
    for col in form1.columns:
        col_lower = col.lower()
        if "tarjeta" in col_lower:
            tarjeta_col = col
            if show_debug:
                st.write(f"✅ Columna de tarjeta encontrada: '{col}'")
            break
    
    # Si no encuentra, buscar por otros términos
    if not tarjeta_col:
        for key in ["número", "numero", "number", "card", "asignado"]:
            for col in form1.columns:
                col_lower = col.lower()
                if key in col_lower:
                    tarjeta_col = col
                    if show_debug:
                        st.write(f"✅ Columna de tarjeta encontrada (por '{key}'): '{col}'")
                    break
            if tarjeta_col:
                break
    
    # Buscar columna de género
    genero_col = None
    for col in form1.columns:
        col_lower = col.lower()
        if "género" in col_lower or "genero" in col_lower:
            genero_col = col
            if show_debug:
                st.write(f"✅ Columna de género encontrada: '{col}'")
            break
    
    # Si no encuentra género, buscar por otros términos
    if not genero_col:
        for key in ["gender", "sexo", "identificas"]:
            for col in form1.columns:
                col_lower = col.lower()
                if key in col_lower:
                    genero_col = col
                    if show_debug:
                        st.write(f"✅ Columna de género encontrada (por '{key}'): '{col}'")
                    break
            if genero_col:
                break
    
    # Obtener columna de marca temporal
    marca_col = _get_date_column_name(form1)
    
    if show_debug:
        st.write(f"📋 Columnas detectadas en Form1:")
        st.write(f"  - Tarjeta: {tarjeta_col or '❌ NO ENCONTRADA'}")
        st.write(f"  - Marca temporal: {marca_col or '❌ NO ENCONTRADA'}")
        st.write(f"  - Género: {genero_col or '❌ NO ENCONTRADA'}")
        if not marca_col:
            st.write("🔍 Primeras columnas de Form1:")
            for i, col in enumerate(form1.columns[:5], 1):
                st.write(f"  {i}. '{col}'")
    
    if not tarjeta_col or not marca_col:
        error_msg = f"No se encontraron columnas necesarias en Form1. Tarjeta: {tarjeta_col}, Marca temporal: {marca_col}"
        if show_debug:
            st.error(f"❌ {error_msg}")
            st.write("📋 Todas las columnas de Form1:")
            for i, col in enumerate(form1.columns, 1):
                st.write(f"  {i}. '{col}'")
        raise ValueError(error_msg)
    
    # Preparar base de Form1
    form1_base_cols = [marca_col, tarjeta_col]
    if genero_col:
        form1_base_cols.append(genero_col)
    
    form1_base = form1[form1_base_cols].copy()
    form1_base.columns = ["marca_temporal", "tarjeta"] + (["genero"] if genero_col else [])
    form1_base["Taller"] = workshop_date or "T_001"
    
    # === 2️⃣ Mapeo de encuadres ===
    encuadre_map = {
        1: "Desconfianza y responsabilización de actores",
        2: "Polarización social y exclusión",
        3: "Miedo y control",
    }
    
    # === 3️⃣ Patrones para identificar preguntas del Form2 ===
    patterns = [
        ("¿Qué emociones identificas en ti en reacción a la noticia? (1)", 1, "Emociones"),
        ("¿Cuáles son los elementos de este mensaje que influyeron más en tu reacción? (1)", 1, "Elementos"),
        ("¿Qué tan confiable consideras que es la información contenida en la noticia 1?", 1, "Confianza"),
        ("¿Qué emociones identificas en ti en reacción a la noticia 2?", 2, "Emociones"),
        ("¿Cuáles son los elementos de este mensaje que influyeron más en tu reacción? (2)", 2, "Elementos"),
        ("¿Qué tan confiable consideras que es la información contenida en la noticia 2?", 2, "Confianza"),
        ("¿Qué emociones identificas en ti en reacción a la noticia? (3)", 3, "Emociones"),
        ("¿Cuáles son los elementos de este mensaje que influyeron más en tu reacción? (3)", 3, "Elementos"),
        ("¿Qué tan confiable consideras que es la información contenida en la noticia 3?", 3, "Confianza"),
    ]
    
    # === 4️⃣ Transformar Form2 en formato largo ===
        # === 4️⃣ Transformar Form2 en formato largo ===
    rows = []

    # ✅ Buscar columna de tarjeta y marca temporal con los nombres reales detectados
    tarjeta_col_f2 = "Ingresa el número asignado en la tarjeta que se te dio"
    marca_col_f2 = "Marca temporal"

    # ⚙️ Mapeo de encuadres (ya definido antes)
    encuadre_map = {
        1: "Desconfianza y responsabilización de actores",
        2: "Polarización social y exclusión",
        3: "Miedo y control",
    }

    # 🔍 Patrones de preguntas con su encuadre
    patterns = [
        ("¿Qué emociones identificas en ti en reacción a la noticia? (1)", 1, "Emociones"),
        ("¿Cuáles son los elementos de este mensaje que influyeron más en tu reacción? (1)", 1, "Elementos"),
        ("¿Qué tan confiable consideras que es la información contenida en la noticia 1?", 1, "Confianza"),
        ("¿Qué emociones identificas en ti en reacción a la noticia 2?", 2, "Emociones"),
        ("¿Cuáles son los elementos de este mensaje que influyeron más en tu reacción? (2)", 2, "Elementos"),
        ("¿Qué tan confiable consideras que es la información contenida en la noticia 2?", 2, "Confianza"),
        ("¿Qué emociones identificas en ti en reacción a la noticia? (3)", 3, "Emociones"),
        ("¿Cuáles son los elementos de este mensaje que influyeron más en tu reacción? (3)", 3, "Elementos"),
        ("¿Qué tan confiable consideras que es la información contenida en la noticia 3?", 3, "Confianza"),
    ]

    # ✅ Iterar filas de Form2
    for _, row in form2.iterrows():
        tarjeta = str(row.get(tarjeta_col_f2, "")).strip()
        marca = row.get(marca_col_f2, None)

        if not tarjeta or pd.isna(marca):
            continue

        for pattern_text, enc_id, pregunta in patterns:
            matching_col = next((col for col in form2.columns if col.strip().lower() == pattern_text.strip().lower()), None)
            if matching_col and pd.notna(row[matching_col]) and str(row[matching_col]).strip():
                valor = str(row[matching_col]).strip()
                rows.append({
                    "Taller": workshop_date or "T_001",
                    "Marca temporal": marca,
                    "Encuadre": encuadre_map[enc_id],
                    "Número de tarjeta": tarjeta,
                    "Pregunta": pregunta,
                    "Valor": valor
                })

    # 🧩 Generar DataFrame final
    df_long = pd.DataFrame(rows)
    
    if not rows:
        if show_debug:
            st.warning("⚠️ No se encontraron filas que coincidan con los patrones.")
            st.write("📋 Patrones buscados:")
            for pattern_text, enc_id, pregunta in patterns:
                st.write(f"  - {pattern_text} (Encuadre {enc_id}, Tipo: {pregunta})")
            st.write("📊 Columnas disponibles en Form2:")
            for col in form2.columns:
                st.write(f"  - '{col}'")
        return (pd.DataFrame(), pd.DataFrame()) if show_debug else pd.DataFrame()
    
    df_long = pd.DataFrame(rows)
    
    if show_debug:
        st.success(f"✅ Formato largo creado: {len(df_long)} filas")
        st.write(f"📊 Columnas en df_long: {list(df_long.columns)}")
        st.write(f"📈 Encuadres encontrados: {df_long['Encuadre'].unique()}")
        st.write(f"📝 Preguntas encontradas: {df_long['Pregunta'].unique()}")
    
    # === 5️⃣ Agregar género desde Form1 ===
    if genero_col and not form1_base.empty:
        # Convertir tarjeta a string para hacer merge
        form1_base["tarjeta"] = form1_base["tarjeta"].astype(str).str.strip()
        df_long["Número de tarjeta"] = df_long["Número de tarjeta"].astype(str).str.strip()
        
        df_final = df_long.merge(
            form1_base[["tarjeta", "genero"]],
            left_on="Número de tarjeta",
            right_on="tarjeta",
            how="left"
        ).drop(columns=["tarjeta"])
    else:
        df_final = df_long.copy()
        df_final["genero"] = None
    
    # === 6️⃣ Ordenar y renombrar columnas ===
    column_order = ["Taller", "Marca temporal", "Encuadre", "Número de tarjeta", "genero", "Pregunta", "Valor"]
    df_final = df_final[column_order].rename(columns={"genero": "Género"})
    
        # === 7️⃣ Expandir filas con valores separados por coma ===
    if "Valor" in df_final.columns:
        # Separar por comas y eliminar espacios
        df_final["Valor"] = df_final["Valor"].astype(str).apply(
            lambda x: [v.strip() for v in x.split(",") if v.strip()]
        )
        # Explota listas en filas
        df_final = df_final.explode("Valor", ignore_index=True)

    if show_debug:
        return df_final, df_long
    return df_final

def _write_df_to_sheet(sheet_id: str, tab_name: str, df: pd.DataFrame, clear_existing: bool = True):
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
        gc = _get_gspread_client()
        sh = gc.open_by_key(sheet_id)
        
        # Intentar obtener el worksheet, si no existe, crearlo
        try:
            worksheet = sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=tab_name, rows=1000, cols=20)
        
        # Limpiar contenido existente si se solicita
        if clear_existing:
            worksheet.clear()
        
        # Convertir DataFrame a lista de listas (incluyendo headers)
        # 🧹 Limpiar valores problemáticos antes de exportar
        df_clean = df.replace([float('inf'), float('-inf')], None).fillna("")

        # Convertir DataFrame a lista de listas (incluyendo headers)
        values = [df_clean.columns.tolist()] + df_clean.astype(str).values.tolist()

        
        # Escribir datos
        worksheet.update(values, value_input_option='RAW')
        
        return True
    except Exception as e:
        raise Exception(f"Error escribiendo a Google Sheets: {e}")


def _autorefresh_toggle(key="auto_refresh_key", millis=60_000):
    """Botón de auto-refresh opcional."""
    auto = st.toggle("🔄 Auto-refresh cada 60s", value=False)
    if auto:
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=millis, key=key)
        except Exception:
            st.info("Para auto-refresh instala `streamlit-autorefresh`.")
    return auto

def _find_image_by_prefix(prefix: str, folder="images"):
    """Busca una imagen local que empiece con el prefijo indicado (ej. 'taller1')."""
    import os
    valid_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    if not os.path.isdir(folder):
        return None
    for f in os.listdir(folder):
        if f.lower().startswith(prefix.lower()) and f.lower().endswith(valid_exts):
            return os.path.join(folder, f)
    return None

def _typing_then_bubble(
    message_text: str,
    image_path: str = None,
    typing_path: str = "images/typing.gif",
    encuadre: str = None,
    ):
    """
    Muestra mensaje tipo WhatsApp con animación 'escribiendo…',
    burbuja verde alineada a la derecha e imagen opcional dentro,
    y una cajita superior con el tipo de encuadre si aplica.
    """
    import html, re, time, os

    # --- Animación 'escribiendo...' (si existe el GIF) ---
    if os.path.isfile(typing_path):
        holder = st.empty()
        with holder.container():
            st.image(typing_path, width=60)
            time.sleep(1.1)
        holder.empty()

    # --- Sanitizar texto y evitar inyección de HTML peligroso ---
    # Elimina bloques prohibidos (script/iframe)
    message_text = re.sub(r'<(script|iframe).*?>.*?</\1>', '', message_text, flags=re.I | re.S)
    # Extrae de forma conservadora un posible bloque <div> embebido y lo elimina del texto
    embedded_html = ""
    html_match = re.search(r"(<div[^>]*?>[\s\S]*?</div>)", message_text, flags=re.I)
    if html_match:
        embedded_html = html_match.group(1)
        message_text = message_text.replace(embedded_html, "")

    # Escapa el resto para mostrarlo como texto dentro de la burbuja
    safe_msg = html.escape(message_text, quote=False).replace("\n", "<br>")


    # --- Cajita del encuadre (si aplica) ---
    if encuadre:
        st.markdown(
            f"""
            <div style="
              background-color:#f1f0f0;
              border-radius:8px;
              padding:6px 12px;
              text-align:center;
              color:#333;
              font-size:14px;
              font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
              margin-bottom:8px;
            ">
              🗞️ <b>Encuadre:</b> {html.escape(encuadre)}
            </div>
            """,
            unsafe_allow_html=True
        )
    enfoque_html = ""
    if encuadre:
        enfoque_html = f"""
        <div style="
        font-size:16px;
        font-weight:600;
        color:#0a0a0a;
        margin-bottom:6px;
        ">
        {html.escape(encuadre)}
        </div>
        """
    # --- Imagen tipo 'card' dentro del mensaje ---
    img_html = ""
    if image_path and os.path.isfile(image_path):
        import base64
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")

        img_html = f"""
        <div style="
        background-color:#fff;
        border-radius:12px;
        overflow:hidden;
        margin-top:10px;
        box-shadow:0 1px 3px rgba(0,0,0,0.15);
        ">
        <img src="data:image/jpeg;base64,{img_base64}" 
            style="width:100%; display:block; border-bottom:1px solid #ddd; border-radius:12px;">
        </div>
        """

    # --- Burbuja verde tipo WhatsApp ---
    html_block = f"""
    <div style="display:flex; justify-content:flex-end; margin:10px 0;">
    <div style="
        background-color:#dcf8c6;
        border-radius:18px 18px 4px 18px;
        padding:12px 16px;
        max-width:90%;
        font-family:'Roboto', system-ui, -apple-system, sans-serif;
        font-size:15px;
        color:#111;
        line-height:1.5;
        box-shadow:0 2px 4px rgba(0,0,0,0.2);
        animation: fadeIn 0.4s ease-out;
    ">
        <div style="color:#777;font-size:12px;margin-bottom:4px;">↪︎↪︎ Reenviado muchas veces</div>
        {enfoque_html}
        {safe_msg}
        {embedded_html}
        {img_html}
        <div style="text-align:right;color:#777;font-size:12px;margin-top:6px;">7:15 PM ✅✅</div>
    </div>
    </div>
        <style>
        @keyframes fadeIn {{
            from {{opacity:0; transform:translateY(8px);}}
            to {{opacity:1; transform:translateY(0);}}
        }}
        </style>
        """
    # Renderizamos como componente HTML para evitar que Markdown escape <img>
    try:
        import streamlit.components.v1 as components
        # Altura estimada más generosa para dar espacio a imagen y texto
        estimated_height = 900 if img_html else 550
        components.html(html_block, height=estimated_height)
    except Exception:
        st.markdown(html_block, unsafe_allow_html=True)

def _qr_image_for(url: str):
    """Genera QR PNG de un link."""
    try:
        import qrcode
        buf = BytesIO()
        qrcode.make(url).save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None

@st.cache_resource(show_spinner=False)
def _openai_client():
    """Devuelve cliente OpenAI."""
    from openai import OpenAI
    api_key = _read_secrets("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY.")
    return OpenAI(api_key=api_key)

def _load_joined_responses():
    """Lee Form0, Form1, Form2 del MISMO Sheet (FORMS_SHEET_ID) y une por 'tarjeta'.
    Filtra las respuestas por la fecha seleccionada en session_state."""
    FORMS_SHEET_ID = _forms_sheet_id()

    # Obtener la fecha del taller seleccionada
    workshop_date = st.session_state.get("selected_workshop_date")
    
    forms = []
    mapping = [
        ("FORM0_TAB", "F0"),
        ("FORM1_TAB", "F1"),
        ("FORM2_TAB", "F2"),
    ]
    for tab_key, tag in mapping:
        tab = _read_secrets(tab_key, "")
        if not tab:
            continue
        try:
            df = _sheet_to_df(FORMS_SHEET_ID, tab)
            df.columns = [c.strip() for c in df.columns]
            df["source_form"] = tag
            
            # Filtrar por fecha del taller seleccionada (excepto Form 0 que usamos como referencia)
            if tag != "F0" and workshop_date:
                df = _filter_df_by_date(df, workshop_date)
            
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

def _analyze_reactions(df_all, key):
    """Analyze reactions and patterns across Form 0–2 (para página Análisis de reacciones)."""
    sample = df_all.head(200).to_dict(orient="records")
    sample_txt = "\n".join([f"{i+1}) {row}" for i, row in enumerate(sample)])

    prompt = f"""
    Eres un analista de talleres educativos sobre desinformación.

    Tienes datos combinados de tres formularios:
    - [Form 0] Contexto del grupo y del docente.
    - [Form 1] Percepciones de inseguridad y emociones previas.
    - [Form 2] Reacciones ante las noticias con diferentes encuadres narrativos.

    Cada fila puede estar vinculada por un número de tarjeta que representa a una persona.

    Tu tarea:
    1️⃣ Identifica patrones de reacción emocional ante las tres noticias (miedo, enojo, empatía, desconfianza, indiferencia, etc.).
    2️⃣ Distingue qué encuadres (desconfianza, polarización, miedo/control, historia personal) provocaron más reacciones emocionales fuertes o reflexivas.
    3️⃣ Detecta diferencias por contexto del grupo (según Form 0) y por percepciones iniciales (Form 1).
    4️⃣ Resume los hallazgos en 4 secciones:
    - “Principales patrones emocionales”
    - “Comparación entre encuadres”
    - “Factores del contexto que influyen”
    - “Recomendaciones pedagógicas para la siguiente sesión”
    5️⃣ Agrega un breve párrafo de síntesis general para el reporte final.

    Datos:
    {sample_txt}

    Responde en Markdown estructurado.
    """
    client = _openai_client()
    with st.spinner("🔎 Analizando reacciones y patrones..."):
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.4,
            max_tokens=1200,
            messages=[
                {"role":"system","content":"Eres un analista pedagógico experto en alfabetización mediática."},
                {"role":"user","content":prompt}
            ]
        )
    return resp.choices[0].message.content.strip()

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

    with col2:
        if idx < len(page_order) - 1:
            if st.button("Siguiente ➡️", key=f"next_{current_page}"):
                st.session_state["current_page"] = page_order[idx + 1]
# ---------- PÁGINAS ----------

def render_setup_trainer_page():
    """Setup del formador (Form 0)."""
    st.header("🧩 Setup sesión — Formador")
    FORM0_URL = _read_secrets("FORM0_URL", "")
    FORMS_SHEET_ID = _forms_sheet_id()    
    FORM0_TAB = _read_secrets("FORM0_TAB", "")
    SA = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")
    
    cols = st.columns(4)
    with cols[0]: st.metric("Form 0 URL", "OK" if FORM0_URL else "Falta")
    with cols[1]: st.metric("Sheet ID", "OK" if FORMS_SHEET_ID else "Falta")
    with cols[2]: st.metric("Worksheet", FORM0_TAB or "—")
    with cols[3]: st.metric("ServiceAccount", "OK" if SA else "Falta")

    if FORM0_URL:
        qr = _qr_image_for(FORM0_URL)
        if qr:
            st.image(qr, caption="Escanea para abrir Form 0", width=220)
        st.link_button("📝 Abrir Form 0", FORM0_URL, use_container_width=True)
    
    # Selector de fecha del taller
    st.markdown("---")
    st.subheader("📅 Seleccionar taller a analizar")
    
    if FORMS_SHEET_ID and FORM0_TAB and SA:
        try:
            available_dates = _get_available_workshop_dates()
            
            if available_dates:
                # Inicializar session_state si no existe
                if "selected_workshop_date" not in st.session_state:
                    # Por defecto, usar la fecha más reciente
                    st.session_state.selected_workshop_date = available_dates[0]
                
                # Selector de fecha
                selected_date = st.selectbox(
                    "Selecciona la fecha del taller a analizar:",
                    options=available_dates,
                    index=0 if st.session_state.selected_workshop_date not in available_dates 
                           else available_dates.index(st.session_state.selected_workshop_date),
                    help="Las respuestas de Form 1 y Form 2 se filtrarán por esta fecha."
                )
                
                # Actualizar session_state
                st.session_state.selected_workshop_date = selected_date
                
                st.success(f"✅ Taller seleccionado: **{selected_date}**")
                st.info(f"📊 Todas las páginas mostrarán solo las respuestas del taller del {selected_date}")
            else:
                st.warning("⚠️ No se encontraron talleres (fechas) en el Form 0. Asegúrate de que haya respuestas en el formulario.")
                st.session_state.selected_workshop_date = None
        except Exception as e:
            st.error(f"Error cargando fechas disponibles: {e}")
            st.session_state.selected_workshop_date = None
    else:
        st.info("⚠️ Configura las credenciales para seleccionar un taller.")
        st.session_state.selected_workshop_date = None


def render_introduction_page():
    """🌎 Página de introducción con carrusel automático de imágenes locales."""
    import os
    import streamlit as st
    import streamlit.components.v1 as components

    st.header("🌎 Introducción al Taller de Integridad de la Información")
    st.markdown(
        "Bienvenid@ al taller de **Integridad de la Información**. "
        "Desliza las imágenes para conocer el contexto del proyecto y los pasos del ejercicio."
        )

    # --- Presentación AccLab (Google Slides embebida y adaptable) ---
    st.markdown("### 🎞️ Presentación AccLab")
    components.html(
    """
    <style>
    .responsive-slides {
        position: relative;
        width: 100%;
        padding-top: 56.25%; /* 16:9 ratio */
    }
    .responsive-slides iframe {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        transform: scale(1.5); /* adjust scale for better fit */
        transform-origin: top left;
    }

    @media (max-width: 900px) {
        .responsive-slides iframe {
            transform: scale(0.7);
        }
    }
    </style>

    <div class="responsive-slides">
        <iframe 
            src="https://docs.google.com/presentation/d/e/2PACX-1vSyG19Nv6Cl-8y3zFbaDpLxBlxA54lUWTQrLK5NTnp4Qh4CcJhB1J_peZIiF8GGYfu5XbL93RCMzhLZ/pubembed?start=false&loop=false&delayms=3000"
            frameborder="0"
            allowfullscreen>
        </iframe>
    </div>
    """,
    height=600,
    )


    # --- Buscar imágenes en carpeta /images ---
    #img_folder = "images"
    #supported_exts = (".jpg", ".jpeg", ".png", ".gif")
    #if not os.path.isdir(img_folder):
    #    os.makedirs(img_folder, exist_ok=True)

    #all_imgs = [os.path.join(img_folder, f) for f in os.listdir(img_folder) if f.lower().endswith(supported_exts)]
    #all_imgs.sort()  # orden alfabético

    #if all_imgs:
    #    st.markdown("### 📸 Galería del taller")
     #   idx = st.slider("Desliza para explorar", 0, len(all_imgs)-1, 0, key="intro_slider")
      #  caption = os.path.basename(all_imgs[idx]).replace("_", " ").replace("-", " ").rsplit(".", 1)[0].capitalize()
       # st.image(all_imgs[idx], caption=caption, use_container_width=True)
    #else:
    #    st.warning("⚠️ No se encontraron imágenes en la carpeta `/images`. Agrega archivos .jpg, .png o .gif para mostrarlas aquí.")

    st.markdown("""
    ---
    ## 💡 Propósito
    Este taller busca **entender cómo las narrativas cambian la forma en que percibimos las noticias**  
    y desarrollar una mirada crítica frente a la desinformación y los sesgos informativos.

    ## 🧭 Estructura del taller
    1️⃣ **Cuestionario 1** — Percepciones de inseguridad y exposición a noticias.  
    2️⃣ **Análisis y tema dominante** — El modelo de IA identifica el patrón principal.  
    3️⃣ **Cuestionario 2** — Reacciones de la audiencia.  
    4️⃣ **Noticias del taller** — Tres versiones de una noticia (WhatsApp).  
    5️⃣ **Análisis final del taller** — Dashboard + conclusiones.

    🔔 **Consejo:** navega en orden desde el menú lateral para seguir la secuencia del taller.
    """)
    navigation_buttons(current_page="Introducción al taller", page_order=list(ROUTES.keys()))


def render_form1_page():
    """Cuestionario 1 – QR y conteo."""
    st.header("📋 Cuestionario 1 (audiencia)")
    FORM1_URL = _read_secrets("FORM1_URL", "")
    FORMS_SHEET_ID = _forms_sheet_id()
    FORM1_TAB = _read_secrets("FORM1_TAB", "")
    SA = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")
    
    if FORM1_URL:
        qr = _qr_image_for(FORM1_URL)
        if qr:
            st.image(qr, caption="Escanea para abrir Cuestionario 1", width=220)
        st.link_button("📝 Abrir Cuestionario 1", FORM1_URL, use_container_width=True)

    _autorefresh_toggle("form1_autorefresh")

    if not (FORMS_SHEET_ID and FORM1_TAB and SA):
        st.info("Configura credenciales para ver conteo.")
        return

    try:
        df = _sheet_to_df(FORMS_SHEET_ID, FORM1_TAB)
        
        # Filtrar por fecha del taller seleccionada
        workshop_date = st.session_state.get("selected_workshop_date")
        if workshop_date:
            df = _filter_df_by_date(df, workshop_date)
            st.info(f"📅 Mostrando respuestas del taller del {workshop_date}")
        else:
            st.warning("⚠️ No hay taller seleccionado. Ve a 'Cuestionario para formador' para seleccionar una fecha.")
        
        st.metric("Respuestas del taller", len(df))
        if not df.empty:
            st.dataframe(df.tail(10), use_container_width=True)
        else:
            st.warning("No hay respuestas para este taller en el rango de fechas.")
    except Exception as e:
        st.error(f"Error leyendo Cuestionario 1: {e}")
    navigation_buttons(current_page="Cuestionario 1", page_order=list(ROUTES.keys()))


def render_analysis_trends_page():
    """Analiza Form 1 completo → tema dominante + nube de palabras (manteniendo tu prompt)."""
    st.header("📈 Análisis y tema dominante")

    FORMS_SHEET_ID = _forms_sheet_id()
    FORM1_TAB = _read_secrets("FORM1_TAB", "")
    FORM0_TAB = _read_secrets("FORM0_TAB", "")
    SA = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")
    OPENAI = _read_secrets("OPENAI_API_KEY", "")
    if not (FORMS_SHEET_ID and FORM1_TAB and SA and OPENAI):
        st.error("Faltan credenciales (Form 1/OpenAI/SA).")
        return

    try:
        # Obtener fecha del taller seleccionada
        workshop_date = st.session_state.get("selected_workshop_date")
        
        if not workshop_date:
            st.warning("⚠️ No hay taller seleccionado. Ve a 'Cuestionario para formador' para seleccionar una fecha.")
            return
        
        df  = _sheet_to_df(FORMS_SHEET_ID, FORM1_TAB)
        # Filtrar Form 1 por fecha del taller
        df = _filter_df_by_date(df, workshop_date)
        st.info(f"📅 Analizando respuestas del taller del {workshop_date}")
        
        df0 = _sheet_to_df(FORMS_SHEET_ID, FORM0_TAB) if FORM0_TAB else pd.DataFrame()
        # Filtrar Form 0 también por fecha (para contexto)
        if not df0.empty:
            df0 = _filter_df_by_date(df0, workshop_date)
    except Exception as e:
        st.error(f"Error leyendo Form 1: {e}")
        return

    if df.empty:
        st.info("Sin respuestas aún para este taller.")
        return
    
    if not df0.empty:
        context_text = "\n".join([
            f"{i+1}) " + " | ".join([f"{k}={v}" for k, v in row.items()])
            for i, row in enumerate(df0.to_dict('records')[:30])
        ])

  
    # ---- OpenAI: análisis de tema dominante + WordCloud ----
    from wordcloud import WordCloud, STOPWORDS
    import matplotlib.pyplot as plt


    # --- Form 1 (respuestas principales) ---
    sample = "\n".join([
        f"{i+1}) " + " | ".join([f"{k}={v}" for k, v in row.items()])
        for i, row in enumerate(df.to_dict('records')[:100])
    ])

    #  :
    analysis_prompt = f"""
    Actúa como un **analista de datos cualitativos experto en comunicación social, seguridad y percepción pública**. 
    Tu tarea es interpretar información proveniente de talleres educativos sobre integridad de la información, desinformación y emociones sociales.

    Dispones de dos fuentes de entrada:

    [Formulario 0 – Contexto del grupo y del entorno local]
    {context_text or "(vacío)"}

    [Formulario 1 – Percepciones de inseguridad y consumo informativo]
    {sample}

    ---

    🎯 **Objetivo del análisis:**
    Identificar el **tema o fenómeno dominante** que genera inseguridad entre las personas participantes, 
    entendiendo el **contexto y el tipo específico de problema** (no solo la categoría general).

    El tema dominante debe reflejar no solo “qué” tipo de fenómeno ocurre, 
    sino también “**en qué contexto o modalidad**” (por ejemplo: “violencia de género en espacios públicos”, 
    “criminalidad asociada al narcotráfico”, “corrupción institucional ligada a la seguridad”, etc.).

    ---

    🧩 **Tareas específicas:**
    1️⃣ Analiza ambas fuentes para determinar el **tema o fenómeno dominante** con su contexto: tipo de hecho, actores, causas y entorno social o mediático.  
    2️⃣ Distingue las **subdimensiones o manifestaciones** del fenómeno (por ejemplo, “violencia” → “violencia de género” o “violencia digital”).  
    3️⃣ Describe las **emociones predominantes** (miedo, enojo, desconfianza, indignación, tristeza, etc.) y su relación con el contexto del grupo.  
    4️⃣ Resume las **causas percibidas** y los **actores involucrados** (autoridades, grupos delictivos, comunidad, medios, etc.).  
    5️⃣ Sugiere hasta **10 palabras clave** representativas del tema y su entorno.  
    6️⃣ Incluye **2 respuestas representativas** de los formularios que ilustren el fenómeno y su tono emocional.

    ---

    📄 **Formato de salida (JSON válido y estructurado):**
    {{
    "dominant_theme": "<tema o fenómeno dominante, frase corta y contextualizada>",
    "rationale": "<explicación breve en 2–4 oraciones que justifique por qué se identificó este tema y cómo se manifiesta en contexto>",
    "emotional_tone": "<emociones predominantes detectadas>",
    "top_keywords": ["<palabra1>", "<palabra2>", "<palabra3>", ...],
    "representative_answers": ["<cita1>", "<cita2>"]
    }}

    ---

    🧠 **Reglas:**
    - El tema debe ser **específico y contextual** (no solo “violencia” o “inseguridad”). Ejemplo: “violencia de género en espacios públicos”, “corrupción policial asociada al narcotráfico”, “desempleo juvenil y percepción de abandono institucional”.  
    - Usa solo información que pueda inferirse de los datos.  
    - Mantén tono analítico, educativo y en español mexicano natural.  
    - Devuelve **únicamente JSON estructurado**.
    """


    try:
        client = _openai_client()
        with st.spinner("🔍 Analizando respuestas del Form 0 y Form 1…"):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=900,
                messages=[
                    {"role": "system", "content": "Eres un analista de datos cualitativos especializado en emociones sociales."},
                    {"role": "user", "content": analysis_prompt},
                ],
            )
        text = resp.choices[0].message.content.strip()
        data = json.loads(re.search(r"\{[\s\S]*\}", text).group(0))
    except Exception as e:
        st.error(f"Error de análisis: {e}")
        return

    # ---- Guardar el tema dominante ----
    dom = data.get("dominant_theme", "N/A")
    # ✅ Persistimos el análisis para otras páginas

    st.session_state["analysis_json_f1"] = data       # JSON completo (por si luego quieres reutilizarlo)
    st.session_state["dominant_theme"]   = dom        # solo el tema
    st.session_state["analysis_cached_at"] = time.time()
    
    # ---- Mostrar resultados ----
    st.subheader("🧠 Tema dominante detectado")
    st.markdown(f"**Tema:** `{dom}`")

    if data.get("rationale"):
        st.markdown(f"**Por qué:** {data['rationale']}")
    if data.get("emotional_tone"):
        st.markdown(f"**Tono emocional predominante:** {data['emotional_tone']}")
    if data.get("top_keywords"):
        st.markdown("**Palabras clave:** " + " · ".join([f"`{x}`" for x in data["top_keywords"]]))
    if data.get("representative_answers"):
        st.markdown("**Ejemplos representativos:**")
        for q in data["representative_answers"]:
            st.markdown(f"- {q}")

     # ---- NUBE DE PALABRAS ----
    st.markdown("---")
    st.subheader("☁️ Nube de palabras — Palabras clave")

    try:
        # Usamos las palabras clave extraídas del análisis (top_keywords)
        keywords = data.get("top_keywords", [])
        if not keywords:
            st.warning("No se encontraron palabras clave para generar la nube.")
        else:
            from wordcloud import WordCloud, STOPWORDS
            import matplotlib.pyplot as plt

            # Stopwords ampliadas en español
            stopwords_es = STOPWORDS.union({
                "de", "la", "el", "los", "las", "en", "que", "por", "con",
                "una", "un", "del", "y", "o", "al", "se", "a", "es", "como",
                "su", "sus", "sobre", "para", "más", "menos", "ya", "no",
                "sí", "lo", "le", "les", "un", "una", "unos", "unas"
            })

            # Filtrar stopwords antes de generar el texto
            clean_keywords = [w for w in keywords if w.lower() not in stopwords_es]

            # Crear texto repetido para dar peso visual (más repeticiones = más tamaño)
            weighted_text = " ".join(clean_keywords * 5)

            # Generar nube de palabras
            wc = WordCloud(
                width=800,
                height=400,
                background_color="white",
                colormap="Dark2",
                collocations=False,
                stopwords=stopwords_es
            ).generate(weighted_text)

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig)
    except Exception as e:
        st.warning(f"No pude generar la nube de palabras: {e}")


  # ➜ Guarda el tema dominante para usarlo en Cuestionario 2
    st.session_state["dominant_theme"] = dom

    # ➜ Botón para ir a "Cuestionario 2"
    st.markdown("---")
    if st.button("👉 Vamos al siguiente punto", type="primary", use_container_width=True):
        st.session_state.selected_page = "Cuestionario 2"
        st.rerun()

def render_form2_page():
    """Cuestionario 2 — QR y botón para pasar a noticias."""
    st.header("📲 Cuestionario 2 — reacciones ante noticias")

    FORM2_URL = _read_secrets("FORM2_URL", "")
    if FORM2_URL:
        qr = _qr_image_for(FORM2_URL)
        if qr:
            st.image(qr, caption="Escanea para abrir Cuestionario 2", width=220)
        st.link_button("📝 Abrir Cuestionario 2", FORM2_URL, use_container_width=True)
    else:
        st.warning("Configura FORM2_URL en secrets para mostrar el QR y el enlace.")

    st.markdown("---")
    dom = st.session_state.get("dominant_theme")
    if not dom:
        st.warning("Primero identifica el tema dominante en ‘Análisis y tema dominante’.")
        if st.button("Ir a ‘Análisis y tema dominante’", use_container_width=True):
            st.session_state.selected_page = "Análisis y tema dominante (Form 1)"
            st.rerun()
        return

    # ✅ Este bloque debe estar dentro de la función
    if st.button("🔎 Mostrar noticias sobre este tema", type="primary", use_container_width=True):
        try:
            client = _openai_client()
            dom = st.session_state.get("dominant_theme", "inseguridad")
            st.info(f"Generando noticias simuladas basadas en el tema dominante: **{dom}**")

            prompts = [
            # 🧩 Prompt 1 — Desconfianza y responsabilización de actores
            f"""
    Contexto general:
    Previamente se realizó un ejercicio en donde se identificaron los tópicos  dominantes y emociones asociadas que causan inseguridad según las respuestas del [formulario 1] y se generó una nube de palabras con los tópicos y la emociones dominantes.
    Rol: 
    Tienes un rol simulado de ser una persona que busca  socavar la confianza en las instituciones públicas, los procesos democráticos y la información objetiva.
    
    Instrucciones:
    Usa el tema dominante identificado en el formulario 1 ({dom}) referentes a los eventos que más han generado sensación de inseguridad y las emociones asociadas y generar una noticia compartida en WhatsApp (máximo 200 palabras), aplicando el encuadre narrativo de desconfianza y responsabilización de actores
    
    Descripción del encuadre de desconfianza y responsabilización de actores:
    Cuestiona la legitimidad institucional o mediática, generando incertidumbre y cinismo ciudadano.
    Atribuye causas o soluciones a actores específicos (individuos, instituciones, grupos). Influye en la percepción pública sobre quién tiene la culpa o el mérito. 

    Elementos del encuadre:
    Atribuye la responsabilidad a ciertos actores, culpando y/o exigiendo.
    Usa un lenguaje causal  (“por”, “debido a”, “por culpa de”).
    Orienta desconfianza institucional.
    Puede reforzar la rendición de cuentas o culpabilización
    Duda sobre la imparcialidad o transparencia institucional.
    Utiliza un lenguaje de reclamo generalizado (“todos son corruptos”, “nunca dicen la verdad”, “siempre han sido ladrones”, “siempre lucran con nuestra confianza”).
    Usa referencias a traición, manipulación o colusión.
    Suele deslegitimar fuentes oficiales o periodísticas, justificando que estas están cooptadas y manipuladas.
    Suele tener presencia de emojis con expresión escéptica o de advertencia (🤔 😒 ⚠️ 👀).
    Usa signos como “¿?”, “…” y “—” para enfatizar la sospecha o ironía.
    Incorpora mayúsculas parciales o exclamaciones para representar tono de hartazgo y desconfianza.
    
    Ejemplos de noticias con Encuadre de Desconfianza Institucional:
    Ya ni la hacen. A vecinos de la 14 Sur les vaciaron la casa ayer a plena luz del día… ¡Y NI UNA PATRULLA LLEGÓ!. Dicen que los ladrones ya habían sido denunciados, pero la policía “no tenía pruebas”🤔. ¿De qué sirve reportar si al final son los mismos policías los que les dan el pitazo para que roben?😒 Todo es un teatro, por culpa de la autoridad los ciudadanos terminamos despojados de nuestro patrimonio y con miedo a las represalias si denunciamos. Es mentira que los índices delictivos han bajado, ⚠️ no creas en fuentes oficiales, mantente vigilante y no confíes ni en la autoridad ⚠️ .

    ⚠️ Entérate ⚠️. 
    Detuvieron a unos del cártel en la carretera, pero al día siguiente… ¡ya estaban libres! Siempre es igual, los gobernantes dicen que combaten el narco, pero seguro alguien les pagó y los dejaron libres. Las autoridades solo hacen operativos para la foto 😒, mientras los verdaderos jefes siguen mandando. ¿Y así quieren que sigamos creyendo en ellos? Ya no vamos a confiar en los traidores, siempre lucran con nuestra confianza, entregan a los buenos y consienten a los malos. Debemos buscar un cambio, ya no confiar en los de siempre, que vean que ellos no son los que mandan, el pueblo manda y podemos quitar a cualquier autoridad que no atienda lo que el pueblo exige. 
    
    Limitaciones:
    No generes nada que pueda vulnerar o promover discriminación.
    Evita reproducir estigmas, lenguaje violento o discriminatorio.
    Limítate a que el mensaje se enmarque en el tono descrito en el encuadre, no cierres con un mensaje optimista o feliz. 
    """,

                # 🧩 Prompt 2 — Polarización social y exclusión
                f"""
    Previamente se realizó un ejercicio en donde se identificaron los tópicos  dominantes y emociones asociadas que causan inseguridad según las respuestas del [formulario 1] y se generó una nube de palabras con los tópicos y la emociones dominantes.
    Rol: 
    Tienes un rol simulado de ser una persona que busca reproducir estigmas y fomenta la deshumanización de un grupo en específico, buscan mantener el status quo y desestimar cualquier intento del otro grupo a través de la polarización. 
    
    Instrucciones:
    Usa el tema dominante identificado en el formulario 1 ({dom}) referentes a los eventos que más han generado sensación de inseguridad y las emociones asociadas  y generar una noticia compartida en WhatsApp (máximo 200 palabras), aplicando el encuadre narrativo de  polarización social y exclusión

    Descripción del encuadre de  polarización social y exclusión:
    Amplifica divisiones sociales y políticas mediante la apelación a emociones intensas (miedo, ira, resentimiento). Favorece el enfrentamiento simbólico y la construcción de “enemigos”. Atribuye la causa de los problemas a ciertos grupos o sectores sociales sin evidencia. 

    Elementos clave del mensaje whatsapp:
    Lenguaje emocional o alarmista.
    Contraposición de grupos (ellos/nosotros).
    Reforzamiento de prejuicios o resentimientos.
    Búsqueda de validación emocional.
    Culpabilización generalizada (“los jóvenes”, “los migrantes”, etc.).
    Emojis de conflicto o ira (😡 😤 🔥 ⚔️ 💣 🚫).
    Mayúsculas parciales y exclamaciones para enfatizar antagonismo.

    Ejemplo de estilo (NO copiar literalmente):**
        🔥 ¡OTRA VEZ! Robaron una casa en la 14 Sur… 😡 Y claro, fueron esos tipos que andan de vagos todo el día, los mismos de siempre. Nosotros, los que trabajamos, los que nos levantamos temprano, los que luchamos por salir adelante… ¿Y ellos? Viendo a quién quitarle lo poco que tenemos. 😤 ¡YA BASTA!
    🚫 Nadie dice nada, porque “pobrecitos”… que son gente sin oportunidades que hay que tenerles compasión… ¡Siempre hay una excusa para justificar lo injustificable! Mientras tanto, NOSOTROS seguimos perdiendo. 💣
    ¿Hasta cuándo vamos a seguir permitiendo esto? ¿Hasta cuándo van a seguir tapando a esa gente que solo trae problemas? 🔥 Cada semana es lo mismo: robo, violencia, miedo… y siempre los mismos rostros, los mismos grupos. ¡Ellos destruyen, nosotros reconstruimos! ⚔️
    💥 ¡Ya no es coincidencia, es una estrategia! Nos están dejando sin seguridad, sin paz, sin dignidad. Y todo por proteger a quienes no respetan nada. ¡NO MÁS SILENCIO! ¡NO MÁS COMPLICIDAD!


    😡 ¡YA NO HAY QUE PERMITIRLES LA ENTRADA! 😡
    La gente de fuera está ARRUINANDO TODO. Nosotros, los de aquí, los que queremos vivir en paz, los que respetamos… y ellos, con sus camionetas de lujo, su prepotencia, su dinero sucio, comprando voluntades, corrompiendo a medio mundo. 🔥 ¡Nos están invadiendo! 💣
    ⚠️ Vienen con sonrisas, pero detrás traen destrucción. Pervierten a nuestros jóvenes, los seducen con promesas falsas, los meten en sus negocios turbios… ¡Y los matan! 😤 ¿Dónde quedó la tranquilidad del barrio? ¿Dónde están los valores que nos enseñaron?
    Y lo peor… ¡todavía hay quienes los defienden! Como si fueran héroes, como si trajeran progreso. 🚫 ¡NO! Lo único que traen es decadencia, violencia, desorden. Por su culpa, los jóvenes ya no quieren estudiar, ya no sueñan con ser doctores o maestros… ahora solo quieren ser como ellos: sin valores, sin moral, peligrosos. ⚔️
    💥 ¡Nos están robando el futuro! Y mientras tanto, los que deberían protegernos miran para otro lado. ¡BASTA YA! 😡🔥


    Limitaciones
    No generes nada que pueda vulnerar o promover discriminación.
    Evita reproducir estigmas, lenguaje violento o discriminatorio.
    Limítate a que el mensaje se enmarque en el tono descrito en el encuadre, no cierres con un mensaje optimista o feliz.
    """,

                # 🧩 Prompt 3 — Miedo y control
                f"""
    Contexto general:
    Previamente se realizó un ejercicio en donde se identificaron los tópicos  dominantes y emociones asociadas que causan inseguridad según las respuestas del [formulario 1] y se generó una nube de palabras con los tópicos y la emociones dominantes.
   
    Rol: 
    Tienes un rol simulado de ser una persona que usa el miedo como herramienta de persuasión y parálisis.

    Instrucciones:
    Usa el tema dominante identificado en el formulario 1 ({dom}) referentes a los eventos que más han generado sensación de inseguridad y las emociones asociadas  y generar una noticia compartida en WhatsApp (máximo 200 palabras), aplicando el encuadre narrativo de miedo y control  

    Descripción de encuadre de miedo y control:
    Exagera el peligro o amenaza para justificar medidas extremas, autoritarias o de control. 

    Elementos clave del encuadre:
    - Lenguaje apocalíptico o totalizador (“todos”, “nunca”).
    - Ausencia de datos verificables.
    - Justificación del control o vigilancia.
    - Signos de urgencia: “‼️”, “❗❗❗”, “…”, “!!!”.
    - Emojis de alarma: 😱 😨 💀 🚨 💣 🔒 📹 🔔.
    - Mayúsculas parciales para enfatizar tono de alarma.

    Ejemplo de estilo (NO copiar literalmente):**
    🚨 Anoche hubo una balacera, dicen que nadie puede salir.  
    Esto ya se salió de control. Mejor cuídense y no abran a nadie.  
    😨 Nadie está a salvo, esto apenas empieza…

    Limitaciones
    No generes nada que pueda vulnerar o promover discriminación.
    Evita reproducir estigmas, lenguaje violento o discriminatorio.
    Limítate a que el mensaje se enmarque en el tono descrito en el encuadre, no cierres con un mensaje optimista o feliz.
    """
        ]

            generated_blocks = []
            for idx, ptext in enumerate(prompts, start=1):
                with st.spinner(f"🧩 Generando Noticia {idx}…"):
                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        temperature=0.55,
                        messages=[
                            {"role": "system", "content": "Asistente educativo experto en comunicación social y desinformación."},
                            {"role": "user", "content": ptext},
                        ],
                        )
                    result = resp.choices[0].message.content.strip()
                    generated_blocks.append(f"Encuadre {idx}:\n{result}")
                    st.success(f"✅ Noticia {idx} lista.")

            # 🔗 Guarda los tres bloques concatenados y pasa a Noticias del taller (después de generar las 3)
            st.session_state.generated_news_raw = "\n\n---\n\n".join(generated_blocks)
            st.session_state.news_index = 0
            st.session_state.selected_page = "Noticias del taller"
            st.rerun()
        except Exception as e:
            st.error(f"Error generando noticias: {e}")


def _find_matching_image(tags: list[str], folder="images"):
    """Busca en /images una imagen cuyo nombre contenga alguno de los tags indicados."""
    import os
    if not os.path.isdir(folder):
        return None

    valid_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    files = [f for f in os.listdir(folder) if f.lower().endswith(valid_exts)]

    if not files or not tags:
        return None

    # Normaliza
    tags_lower = [t.strip().lower() for t in tags]
    scores = []
    for f in files:
        name = f.lower()
        match_score = max([difflib.SequenceMatcher(None, name, t).ratio() for t in tags_lower])
        scores.append((match_score, f))
    scores.sort(reverse=True)
    best_match = scores[0][1] if scores and scores[0][0] > 0.3 else None
    if best_match:
        return os.path.join(folder, best_match)
    return None

def _parse_news_blocks(raw: str):
    """Extrae hasta 3 bloques de noticias y vincula imagen local según tags."""
    import re, os

    if not isinstance(raw, str) or not raw.strip():
        return []

    parts = re.split(r'^\s*[-—]{3,}\s*$|\n{2,}', raw, flags=re.MULTILINE)
    cleaned = []

    for p in parts:
        t = (p or "").strip()
        if not t or re.fullmatch(r'[-—\s]+', t):
            continue

        # Detectar tags sugeridos
        img_tags_match = re.search(r'(?i)imagen\s+sugerida\s*\(.*?tags.*?\)\s*:\s*(.*)', t)
        img_tags = []
        if img_tags_match:
            tag_str = img_tags_match.group(1)
            img_tags = [w.strip() for w in re.split(r'[;,]', tag_str) if w.strip()]
            # Elimina la sección desde "Imagen sugerida" hacia abajo del texto principal
            t = re.split(r'(?i)imagen\s+sugerida', t)[0].strip()

        # Limpiar encabezados y numeraciones al inicio
        t = re.sub(r'\*{1,2}(?!\S)|(?<!\S)\*{1,2}', '', t)
        t = re.sub(r'(?i)^\*\*noticia compartida en whatsapp\*\*\s*:?', '', t).strip()
        # Eliminar encabezado tipo "Encuadre X:"
        t = re.sub(r'(?i)^encuadre\s*\d+\s*:?', '', t).strip()  # elimina "Encuadre 1:", "Encuadre 2:", etc.    

        
        # Eliminar líneas que son solo hashtags o encabezados markdown
        lines = [ln for ln in t.splitlines() if ln.strip()]
        cleaned_lines = []
        for ln in lines:
            s = ln.strip()
            if re.fullmatch(r'(?:#\w+\s*){1,}', s):
                continue
            if re.match(r'^#{1,6}\s+', s):
                continue
            cleaned_lines.append(ln)
        t = "\n".join(cleaned_lines).strip()

        # Buscar imagen local si hay tags
        image_path = _find_matching_image(img_tags) if img_tags else None
        cleaned.append({
            "text": t,
            "image": image_path
        })
    for i, item in enumerate(cleaned):
            fixed_image = f"images/taller{i+1}.jpeg"
            if os.path.isfile(fixed_image):
                item["image"] = fixed_image
    return cleaned[:3]


def render_news_flow_page():
    """Muestra 3 noticias tipo WhatsApp, con navegación y botón final a Análisis."""
    st.header("💬 Noticias del taller")

    # Mostrar subtítulo con el enfoque actual
    encuadres = [
        "Desconfianza y responsabilización de actores",
        "Polarización social y exclusión",
        "Miedo y control",
    ]
    idx = int(st.session_state.get("news_index", 0))
    if idx < len(encuadres):
        st.markdown(f"### 🗞️ Encuadre {idx+1}: {encuadres[idx]}")
    else:
        st.info("No hay noticias disponibles.")
        return

    raw = st.session_state.get("generated_news_raw")
    if not raw:
        st.info("Genera primero desde 'Análisis y tema dominante' (o vuelve si ya generaste).")
        return

    stories = _parse_news_blocks(raw)
    if not stories:
        st.warning("No se pudieron interpretar noticias desde el texto generado.")
        st.code(raw)
        return

    idx = int(st.session_state.get("news_index", 0))
    if idx >= len(stories):
        idx = 0
        st.session_state.news_index = 0

    # Render del mensaje actual (con imagen de prueba si existe)
    story = stories[idx]

    _typing_then_bubble(
        message_text=story.get("text", ""),
        image_path=story.get("image"),
        encuadre=story.get("encuadre")
    )
    # Navegación
    left, right = st.columns(2)
    with left:
        if st.button("⬅️ Anterior", disabled=(idx==0), use_container_width=True):
            st.session_state.news_index = idx - 1
            st.rerun()
    with right:
        if idx < len(stories) - 1:
            if st.button("➡️ Siguiente", use_container_width=True):
                st.session_state.news_index = idx + 1
                st.rerun()
        else:
            if st.button("📘 Explicación del taller", type="primary", use_container_width=True):
                st.session_state.selected_page = "Explicación del taller"
                st.rerun()

    # Contador (opcional) cuando estás en la última noticia
    if idx == len(stories) - 1:
        st.markdown("---")
        st.subheader("📊 Participación del grupo (respuestas finales)")
        FORMS_SHEET_ID = _forms_sheet_id()
        FORM2_TAB = _read_secrets("FORM2_TAB", "")
        if FORMS_SHEET_ID and FORM2_TAB:
            try:
                df2 = _sheet_to_df(FORMS_SHEET_ID, FORM2_TAB)
                # Filtrar por fecha del taller seleccionada
                workshop_date = st.session_state.get("selected_workshop_date")
                if workshop_date:
                    df2 = _filter_df_by_date(df2, workshop_date)
                    st.info(f"📅 Respuestas del taller del {workshop_date}")
                st.metric("Respuestas finales del taller", len(df2))
            except Exception as e:
                st.error(f"Error al contar respuestas finales: {e}")

def render_explanation_page():
    """📘 Página intermedia entre Noticias y Análisis final."""
    st.header("📘 Explicación del Taller")

    st.markdown("""
    En esta sección puedes revisar el contexto general del taller antes de pasar al análisis final.
    """)

    st.subheader("📰 Descripción de las noticias")
    st.text_area("descripcion_noticias", "Aquí puedes incluir una descripción general de las noticias presentadas.", height=150)

    st.subheader("🧩 Descripción de los encuadres")
    st.text_area("descripcion_encuadres", "Aquí puedes incluir una breve explicación sobre los encuadres utilizados (desconfianza, polarización, miedo).", height=150)

    st.subheader("🧠 TBD")
    st.text_area("descripcion_tbd", "Contenido pendiente o personalizado según el grupo participante.", height=150)

    st.markdown("---")

    st.subheader("📊 Preparar datos para el análisis final")

    if st.button("🚀 Vamos a los análisis finales del taller", type="primary", use_container_width=True):
        try:
            FORMS_SHEET_ID = _forms_sheet_id()
            FORM1_TAB = _read_secrets("FORM1_TAB", "")
            FORM2_TAB = _read_secrets("FORM2_TAB", "")
            workshop_date = st.session_state.get("selected_workshop_date", "T_001")

            if not (FORM1_TAB and FORM2_TAB):
                st.error("⚠️ Faltan configuraciones de Form1_TAB o Form2_TAB en secrets.")
                return

            with st.spinner("📥 Cargando datos de Form1 y Form2..."):
                form1 = _sheet_to_df(FORMS_SHEET_ID, FORM1_TAB)
                form2 = _sheet_to_df(FORMS_SHEET_ID, FORM2_TAB)

            if form1.empty or form2.empty:
                st.warning("⚠️ Form1 o Form2 están vacíos. Verifica que haya datos.")
                return

            with st.spinner("🔄 Transformando datos a formato normalizado..."):
                df_normalized = _normalize_form_data(form1, form2, workshop_date)

            if df_normalized.empty:
                st.warning("⚠️ No se encontraron datos para normalizar. Verifica columnas o estructura.")
                return

            with st.spinner("📤 Guardando datos centralizados en Google Sheets..."):
                _write_df_to_sheet(
                    FORMS_SHEET_ID,
                    "Datos Centralizados Form2",
                    df_normalized,
                    clear_existing=True
                )

            st.success("✅ Datos guardados en 'Datos Centralizados Form2'. ¡Listos para Looker!")

            # Ir a análisis final
            st.session_state.selected_page = "Análisis final del taller"
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error procesando datos: {e}")
            import traceback
            with st.expander("Detalles del error"):
                st.code(traceback.format_exc())


def render_workshop_insights_page():
    """Dashboard + (debajo) síntesis automática con datos reales (Form 0/1/2/3/4 si están conectados)."""
    st.header("📊 Análisis final del taller")

    # --- Dashboard (estático) ---
    st.subheader("Dashboard (Looker Studio)")
    try:
        import streamlit.components.v1 as components
        components.html(
            """
           <iframe width="600" height="450" src="https://lookerstudio.google.com/embed/reporting/cba53d78-d687-4929-aed6-dfb683841f06/page/p_cbx8w44sxd" frameborder="0" style="border:0" allowfullscreen sandbox="allow-storage-access-by-user-activation allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe>
            """,
            height=640
        )
    except Exception:
        st.info("Agrega aquí el embed público de tu reporte de Looker Studio.")

    st.markdown("---")

    # --- Síntesis automática con IA (usa datos reales combinados) ---
    st.subheader("🧠 Interpretación automática de resultados")
    st.caption("Se combinan respuestas de Cuestionario 0/1/2/3/4 (si están configurados) y se genera una síntesis para facilitar el debate.")
    
    # Mostrar información sobre el taller seleccionado
    workshop_date = st.session_state.get("selected_workshop_date")
    if workshop_date:
        st.info(f"📅 Analizando respuestas del taller del {workshop_date}")
    else:
        st.warning("⚠️ No hay taller seleccionado. Ve a 'Cuestionario para formador' para seleccionar una fecha.")

    if st.button("🔎 Analizar respuestas", type="primary", use_container_width=True):
        # 1) Lee datos combinados
        try:
            df_all_key = _load_joined_responses()
            # Compat: tu helper puede devolver (df_all, key) o solo df. Normalicemos:
            if isinstance(df_all_key, tuple):
                df_all, join_key = df_all_key
            else:
                df_all, join_key = df_all_key, None
        except Exception as e:
            st.error(f"No pude cargar datos combinados: {e}")
            return

        if isinstance(df_all, pd.DataFrame) and df_all.empty:
            st.warning("No hay respuestas combinadas aún para analizar para este taller.")
            return

        # 2) Muestra un vistazo mínimo (opcional)
        with st.expander("👀 Muestra de datos combinados utilizados (primeras 10 filas)"):
            st.dataframe(df_all.head(50), use_container_width=True)
        

        
        # 4) Prepara muestra textual (capada) para el prompt
        sample_records = df_all.head(220).to_dict(orient="records")
        sample_txt = "\n".join([f"{i+1}) {row}" for i, row in enumerate(sample_records)])

        # 5) Prompt unificado (hallazgos + patrones + preguntas de debate)
        prompt = f"""
    Eres un analista de datos especializado en percepción social y comunicación.

    Contexto:
    Se realizó un taller donde se generaron tres noticias diferentes sobre un mismo evento,
    cada una con un encuadre narrativo distinto. Los participantes respondieron un formulario
    indicando, para cada noticia: las emociones que sintieron, el grado de confiabilidad percibido,
    y los elementos clave que les llamaron la atención.

    Datos combinados (formularios 1 y 2) disponibles a continuación:
    {sample_txt}

    Tu tarea es elaborar un informe interpretativo estructurado en las siguientes secciones:

    ### 1 Cruce de datos
    - Une respuestas con el mismo número de tarjeta (misma persona).
    - Asegúrate de mantener coherencia de género, emociones, encuadre percibido, y nivel de confianza.

    ### 2 Análisis por encuadre narrativo
    Objetivo: observar cómo varían las emociones, la confianza y los componentes clave según el encuadre.
    Incluye en texto (no gráfico):
    - Principales diferencias de emociones por encuadre.
    - Diferencias en el nivel de confianza.
    - Elementos clave más frecuentes por encuadre.
    - Relacion entre genero y encuadre y emociones generadas
    - Breve texto explicativo (3–5 líneas) que destaque hallazgos notables.

    ### 3 Análisis por género–reacción emocional
    Objetivo: detectar diferencias de percepción y reacción emocional según género.
    Incluye:
    - Comparación de emociones predominantes por género.
    - Niveles de confianza promedio por género.
    - Texto explicativo (3–5 líneas) con diferencias relevantes.
    - 2 preguntas que fomenten reflexión (por ejemplo: ¿Cómo influye el género en la validación emocional o racional del mensaje?).


    Reglas:
    - Usa únicamente información derivada de los datos provistos.
    - Tono analítico y educativo, claro y sintético.
    - Responde en Markdown estructurado.
    """


        try:
            client = _openai_client()
            with st.spinner("Procesando respuestas y generando interpretación…"):
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.4,
                    max_tokens=1300,
                    messages=[
                        {"role": "system",
                         "content": "Eres un facilitador pedagógico. Estructuras ideas con claridad y neutralidad."},
                        {"role": "user", "content": prompt},
                    ],
                )
            st.markdown(resp.choices[0].message.content.strip())
        except Exception as e:
            st.error(f"Error generando interpretación automática: {e}")
    navigation_buttons(current_page="Análisis final del taller", page_order=list(ROUTES.keys()))


# ---------- ROUTER (etiquetas/orden solicitados) ----------
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
