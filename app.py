# app.py — Taller Integridad de la Información (Streamlit router and layout only)

import json
import re
import time
import os
import difflib
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.express as px

# ---------- IMPORTS FROM MODULES ----------
from config.secrets import read_secrets, forms_sheet_id
from data.sheets import get_gspread_client, sheet_to_df, write_df_to_sheet, append_df_to_sheet
from data.cleaning import normalize_form_data, filter_df_by_date
from data.utils import get_date_column_name, normalize_date, get_available_workshop_dates, load_joined_responses
from components.whatsapp_bubble import typing_then_bubble, find_image_by_prefix, find_matching_image
from components.qr_utils import qr_image_for
from components.navigation import get_navigation_context
from components.utils import autorefresh_toggle
from services.ai_analysis import (
    get_openai_client,
    analyze_reactions,
    analyze_trends,
    analyze_emotions_json,
    analyze_gender_impacts_json,
    analyze_general_json
)

from services.news_generator import generate_news
from components.image_repo import get_images_for_dominant_theme


# ---------- CONFIG BÁSICA ----------
st.set_page_config(
    page_title="Taller • Integridad de la Información",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- ALIASES FOR BACKWARD COMPATIBILITY ----------
# These allow existing code to work while we migrate
_read_secrets = read_secrets
_forms_sheet_id = forms_sheet_id
_get_gspread_client = get_gspread_client
_sheet_to_df = sheet_to_df
_write_df_to_sheet = write_df_to_sheet
_append_df_to_sheet = append_df_to_sheet
_get_date_column_name = get_date_column_name
_normalize_date = normalize_date
_get_available_workshop_dates = get_available_workshop_dates
_filter_df_by_date = filter_df_by_date
_normalize_form_data = normalize_form_data
_load_joined_responses = load_joined_responses
_typing_then_bubble = typing_then_bubble
_find_image_by_prefix = find_image_by_prefix
_find_matching_image = find_matching_image
_qr_image_for = qr_image_for
_autorefresh_toggle = autorefresh_toggle
_openai_client = get_openai_client
_analyze_reactions = analyze_reactions


def _log_debug_message(message: str, *, level: str = "info", context: str | None = None, data: dict | None = None):
    """Registra mensajes de depuración para mostrarlos en la sección de Configuraciones."""
    if not message:
        return
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
        "level": level,
        "context": context,
    }
    if data is not None:
        entry["data"] = data
    logs = st.session_state.setdefault("workflow_debug_messages", [])
    logs.append(entry)
    st.session_state["workflow_debug_messages"] = logs[-200:]


def _format_emotions_json_to_markdown(data: dict) -> str:
    """Convierte el JSON de análisis de emociones a markdown con la tipografía del resto de la web."""
    if not data or "workshops" not in data:
        return "No hay datos disponibles."
    
    markdown_parts = []
    
    for workshop in data.get("workshops", []):
        taller_name = workshop.get("taller", "Taller")
        markdown_parts.append(f"## {taller_name}\n")
        
        emociones_por_encuadre = workshop.get("emociones_por_encuadre", {})
        if emociones_por_encuadre:
            markdown_parts.append("### Emociones por encuadre\n")
            
            for encuadre, emociones in emociones_por_encuadre.items():
                if emociones:
                    emociones_str = ", ".join(emociones)
                    markdown_parts.append(f"**{encuadre}:** {emociones_str}\n")
        
        resumen = workshop.get("resumen", "")
        if resumen:
            markdown_parts.append(f"\n### Resumen\n\n{resumen}\n")
        
        preguntas = workshop.get("preguntas_discusion", [])
        if preguntas:
            markdown_parts.append("\n### Preguntas para la discusión\n")
            for pregunta in preguntas:
                markdown_parts.append(f"- {pregunta}\n")
        
        markdown_parts.append("\n---\n")
    
    return "\n".join(markdown_parts)


def _format_gender_json_to_markdown(data: dict) -> str:
    """Convierte el JSON de análisis de género a markdown con la tipografía del resto de la web."""
    if not data or "analisis_genero" not in data:
        return "No hay datos disponibles."
    
    markdown_parts = []
    
    for analisis in data.get("analisis_genero", []):
        taller_name = analisis.get("taller", "Taller")
        markdown_parts.append(f"## {taller_name}\n")
        
        patrones = analisis.get("patrones_por_genero", {})
        if patrones:
            markdown_parts.append("### Patrones por género\n")
            for genero, sintesis in patrones.items():
                markdown_parts.append(f"**{genero}:**\n")
                markdown_parts.append(f"{sintesis}\n\n")
        
        hallazgos = analisis.get("hallazgos_transversales", "")
        if hallazgos:
            markdown_parts.append(f"### Hallazgos transversales\n\n{hallazgos}\n")
        
        preguntas = analisis.get("preguntas_discusion", [])
        if preguntas:
            markdown_parts.append("\n### Preguntas para la discusión\n")
            for pregunta in preguntas:
                markdown_parts.append(f"- {pregunta}\n")
        
        markdown_parts.append("\n---\n")
    
    return "\n".join(markdown_parts)


def _format_general_json_to_markdown(data: dict) -> str:
    """Convierte el JSON de análisis general a markdown con la tipografía del resto de la web."""
    if not data or "resumen_general" not in data:
        return "No hay datos disponibles."
    
    markdown_parts = []
    resumen = data.get("resumen_general", {})
    
    patrones = resumen.get("patrones_transversales", "")
    if patrones:
        markdown_parts.append("### Patrones transversales\n")
        markdown_parts.append(f"{patrones}\n")
    
    sesgos = resumen.get("sesgos_identificados", [])
    if sesgos:
        markdown_parts.append("\n### Sesgos identificados\n")
        for sesgo in sesgos:
            markdown_parts.append(f"- {sesgo}\n")
    
    hallazgos = resumen.get("hallazgos_clave", "")
    if hallazgos:
        markdown_parts.append(f"\n### Hallazgos clave\n\n{hallazgos}\n")
    
    return "\n".join(markdown_parts)


# ---------- HELPER FUNCTIONS (kept here for page-specific logic) ----------
def _parse_news_blocks(raw: str):
    """
    Extrae hasta 3 bloques de noticias y les asigna imágenes asociadas
    al tema dominante actual del taller.
    """
    import re, os
    import streamlit as st

    if not isinstance(raw, str) or not raw.strip():
        return []

    # 1️⃣ Separar el texto en bloques (cada noticia generada)
    parts = re.split(r'\n?\s*[-—]{3,}\s*\n?', raw)
    cleaned = []

    for p in parts:
        t = (p or "").strip()
        if not t or re.fullmatch(r'[-—\s]+', t):
            continue

        # Limpiar encabezados y basura de formato
        t = re.sub(r'\*{1,2}(?!\S)|(?<!\S)\*{1,2}', '', t)
        t = re.sub(r'(?i)^\*\*noticia compartida en whatsapp\*\*\s*:?', '', t).strip()
        t = re.sub(r'(?i)^encuadre\s*\d+\s*:?', '', t).strip()
        t = re.sub(r'(?i)imagen\s+sugerida.*', '', t).strip()

        # Eliminar hashtags o markdown
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

        cleaned.append({"text": t})

    # 2️⃣ Obtener tema dominante actual
    dominant_theme = st.session_state.get("dominant_theme", "").lower().strip()

    # 3️⃣ Obtener hasta 3 imágenes desde el repositorio
    theme_images = get_images_for_dominant_theme(dominant_theme)

    # 4️⃣ Asignar imágenes en orden
    for i, item in enumerate(cleaned):
        if i < len(theme_images):
            item["image"] = theme_images[i]
        else:
            # Fallback si hay más textos que imágenes
            fallback = f"images/taller{i+1}.jpeg"
            item["image"] = fallback if os.path.isfile(fallback) else None

    return cleaned[:3]

# ---------- PÁGINAS ----------

def render_setup_trainer_page():
    """Setup del formador (Form 0)."""
    st.markdown("""
    <style>
        .setup-header {
        text-align: center;
            font-size: 28px;
            font-weight: 600;
            color: #004b8d;
            margin-bottom: 0.2rem;
        }
        .setup-sub {
            text-align: center;
            color: #777;
        margin-bottom: 2rem;
            font-size: 16px;
        }
        .metric-row {
            display: flex;
            justify-content: space-around;
        text-align: center;
        margin-bottom: 2rem;
      }
        .metric-row .metric {
            background-color: #f0f4f8;
            padding: 1rem;
            border-radius: 10px;
            flex: 1;
            margin: 0 0.3rem;
      }
    </style>
    <div class="setup-header">⚙️ Configuración del Taller</div>
    <div class="setup-sub">Completa esta información antes de iniciar el taller.</div>
    """, unsafe_allow_html=True)

    if st.button("🏠 Volver a la introducción", use_container_width=True):
        st.session_state.current_page = "Introducción al taller"
        st.rerun()

    FORM0_URL = _read_secrets("FORM0_URL", "")
    FORMS_SHEET_ID = _forms_sheet_id()    
    FORM0_TAB = _read_secrets("FORM0_TAB", "")
    SA = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")
    
    
    if FORM0_URL:
        st.markdown("### 📝 Configuración: Paso 1 de 2 - Creación del taller")

        # --- Estilos para el contenedor ---
        st.markdown("""
        <style>
        .form-embed {
            border: 1px solid #ddd;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
            height: 900px;
        }
        .form-embed iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        </style>
        """, unsafe_allow_html=True)

        # --- Iframe embebido del Formulario 0 ---
        st.markdown(f"""
        <div class="form-embed">
            <iframe 
                src="{FORM0_URL}?embedded=true"
                frameborder="0" 
                marginheight="0" 
                marginwidth="0">
                Cargando…
            </iframe>
        </div>
        """, unsafe_allow_html=True)

        st.caption("Puedes completar el Formulario 0 directamente aquí, sin salir de la aplicación.")

    # Selector de fecha del taller
    st.markdown("---")
    st.subheader("📅 Configuración: Paso 2 de 2 - Seleccionar taller a analizar")
    
    if FORMS_SHEET_ID and FORM0_TAB and SA:
        try:
            available_dates = _get_available_workshop_dates()
            
            if available_dates:
                # Inicializar session_state si no existe
                if "selected_workshop_date" not in st.session_state:
                    # Por defecto, usar la fecha más reciente
                    st.session_state.selected_workshop_date = available_dates[0]
                
                # Selector de fecha
                display_dates = sorted(available_dates, reverse=True)

                cols = st.columns([4, 1])
                with cols[0]:
                    selected_date = st.selectbox(
                        "Selecciona la fecha del taller a analizar:",
                        options=display_dates,
                        index=0 if st.session_state.selected_workshop_date not in display_dates 
                               else display_dates.index(st.session_state.selected_workshop_date),
                        help="Las respuestas de Form 1 y Form 2 se filtrarán por esta fecha."
                    )
                with cols[1]:
                    if st.button("🔄", help="Actualizar lista de talleres"):
                        try:
                            st.cache_data.clear()
                            st.session_state.pop("available_dates_cache", None)
                            st.session_state.pop("selected_workshop_date", None)
                            st.success("Lista actualizada. Vuelve a seleccionar un taller.")
                            st.rerun()
                        except Exception as refresh_error:
                            st.error(f"No se pudo refrescar la lista: {refresh_error}")
                
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

    st.markdown("---")
    st.subheader("🛠️ Debug messages")
    debug_active = st.checkbox(
        "Activar y mostrar registros técnicos",
        value=bool(st.session_state.get("debug_image_scoring")),
        help="Incluye puntajes de imágenes y mensajes automáticos sobre la ejecución del taller.",
    )
    st.session_state["debug_image_scoring"] = debug_active

    if debug_active:
        col_hint, col_clear = st.columns([4, 1])
        with col_hint:
            st.caption("Revisa aquí los eventos internos. Los registros se conservan solo durante la sesión actual.")
        with col_clear:
            if st.button("Limpiar registros", key="clear_debug_logs"):
                st.session_state["image_scoring_debug"] = []
                st.session_state["workflow_debug_messages"] = []
                st.caption("Registros limpiados.")

        workflow_logs = st.session_state.get("workflow_debug_messages") or []
        if workflow_logs:
            st.markdown("**Mensajes del flujo del taller**")
            for idx, entry in enumerate(reversed(workflow_logs), start=1):
                title = f"[{entry.get('timestamp')}] {entry.get('context') or 'Sin contexto'} — {entry.get('level', 'info').upper()}"
                with st.expander(title, expanded=False):
                    st.markdown(entry.get("message", ""))
                    data = entry.get("data")
                    if data:
                        st.json(data)
        else:
            st.caption("Sin mensajes registrados del flujo.")

        image_entries = st.session_state.get("image_scoring_debug") or []
        if image_entries:
            st.markdown("**Selección de imágenes**")
            for idx, entry in enumerate(reversed(image_entries), start=1):
                title = f"Intento #{len(image_entries) - idx + 1} — {entry.get('encuadre') or 'Sin encuadre'}"
                with st.expander(title, expanded=False):
                    st.markdown(f"**Tema:** {entry.get('theme') or 'N/A'}")
                    st.markdown(f"**Seleccionada:** `{entry.get('selected') or 'Sin coincidencia'}`")
                    best = entry.get("best_score")
                    st.markdown(f"**Puntaje máximo:** {best if best is not None else 'N/D'}")
                    st.markdown(f"**Usó fallback:** {'Sí' if entry.get('used_fallback') else 'No'}")
                    candidates = entry.get("candidates")
                    if isinstance(candidates, list):
                        st.markdown("**Candidatos evaluados:**")
                        st.json(candidates)
                    else:
                        st.markdown(f"**Detalle:** {candidates}")
        else:
            st.caption("Sin registros de selección de imágenes.")


def render_introduction_page():
    """🌎 Página de introducción con presentación compacta."""
    import streamlit as st
    import streamlit.components.v1 as components

    # --- Apply tighter layout and reset top padding ---
    st.markdown("""
    <style>
    /* Container */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0rem !important;
        max-width: 900px !important;
    }

    /* Main title */
    .intro-header {
        text-align: center;
        font-size: 2rem;
        font-weight: 700;
        color: #004b8d;
        margin-top: 2rem;       /* slightly lower the title */
        margin-bottom: 0.5rem;
    }
    .intro-subtext {
        text-align: center;
        color: #333;
        font-size: 1.05rem;
        margin-bottom: 1.2rem;  /* reduced space under subtitle */
    }

    /* Presentation box */
    .presentation-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 0.3rem 0.3rem 0.8rem 0.3rem; /* less vertical padding */
        box-shadow: 0 4px 10px rgba(0,0,0,0.06);
        margin-bottom: 1rem; /* tighter spacing below */
    }
    .presentation-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #222;
        margin-bottom: 0.4rem;
    }

    /* Slides */
    .responsive-slides {
        position: relative;
        width: 100%;
        padding-top: 50%; /* slightly smaller height ratio */
        border-radius: 8px;
        overflow: hidden;
    }
    .responsive-slides iframe {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: none;
    }

    /* Section titles */
    h2 {
        color: #004b8d !important;
        margin-top: 0.8rem !important;
        margin-bottom: 0.4rem !important;
    }

    /* Paragraph text */
    p {
        font-size: 1.05rem;
        color: #333;
        line-height: 1.6;
    }

    /* Divider */
    hr {
        border: none;
        border-top: 1px solid #e0e0e0;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)


    # --- Header and intro text ---
    st.markdown("## 🌎 Introducción al Taller de Integridad de la Información")
    st.markdown(
        '<p style="font-size: 1.5rem; font-weight: 500;">Bienvenid@ al taller de <strong>Integridad de la Información</strong>.</p>',
        unsafe_allow_html=True
    )

    # --- Propósito section (kept close to the slides) ---
    st.markdown("""
    <style>
    .intro-content {
        font-size: 1.2rem;
        line-height: 1.8;
    }
    .intro-content h2 {
        font-size: 2rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .intro-content p {
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
    .intro-content ul, .intro-content ol {
        font-size: 1.2rem;
    }
    </style>
    <div class="intro-content">
    
    ## 💡 Propósito

    Este taller busca **entender cómo las narrativas cambian la forma en que percibimos las noticias**
    y desarrollar una mirada crítica frente a la desinformación y los sesgos informativos.

    ## 📋 Instrucciones para el formador del taller
    1️⃣ **Configura el taller** — Haz clic en el botón de configuración en el menú lateral y configura tu taller.  
    2️⃣ **Selecciona la fecha del taller** — Esto servirá para la etapa de análisis de datos.  
    3️⃣ **Reparte una tarjeta a cada participante** — El identificados de cada participante es el número asignado, así mantenemos los datos anonimizados.  
    4️⃣ **Comparte el propósito con la audiencia** — Mantén un alto nivel de interactividad durante el taller.  
    5️⃣ **Disfruta, aprende y comparte**

    ## 🧭 Estructura del taller
    1️⃣ **Cuestionario 1** — Percepciones de inseguridad y exposición a noticias.  
    2️⃣ **Análisis y tema dominante** — El modelo de IA identifica el patrón principal.  
    3️⃣ **Cuestionario 2** — Reacciones de la audiencia.  
    4️⃣ **Noticias del taller** — Tres versiones de una noticia (WhatsApp).  
    5️⃣ **Análisis final del taller** — Dashboard + conclusiones.
    </div>
    """, unsafe_allow_html=True)

 # --- Embedded Google Slides (responsive) ---
    components.html(
        """
        <style>
            .responsive-slides {
                position: relative;
                width: 100%;
                padding-bottom: 56.25%; /* 16:9 aspect ratio (9/16 = 0.5625) */
                height: 0;
                overflow: hidden;
            }
            .responsive-slides iframe {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                border: none;
            }
        </style>
        <div class="responsive-slides">
            <iframe src="https://docs.google.com/presentation/d/e/2PACX-1vSyG19Nv6Cl-8y3zFbaDpLxBlxA54lUWTQrLK5NTnp4Qh4CcJhB1J_peZIiF8GGYfu5XbL93RCMzhLZ/pubembed?start=false&loop=false&delayms=3000" 
                    allowfullscreen="true" 
                    mozallowfullscreen="true" 
                    webkitallowfullscreen="true">
            </iframe>
        </div>
        """,
        height=500,  # Altura del contenedor (el iframe se ajustará proporcionalmente)
    )
        # --- Siguiente paso del taller (en la página principal) ---
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 🚀 Si has configurado tu taller, estas listo para continuar")



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
            left, center, right = st.columns([1, 2, 1])
            with center:
                st.image(qr, caption="Escanea para abrir Cuestionario 1", width=360)
        st.link_button("📝 Abrir Cuestionario 1", FORM1_URL, use_container_width=True)

        if st.button("🔄 Actualizar respuestas", use_container_width=True):
            st.rerun()

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
            st.warning("⚠️ No hay taller seleccionado. Ve a 'Configuraciones' para seleccionar una fecha.")
        
        st.metric("Respuestas del taller", len(df))
        if not df.empty:
            st.dataframe(df.tail(10), use_container_width=True)
        else:
            st.warning("No hay respuestas para este taller en el rango de fechas.")
    except Exception as e:
        st.error(f"Error leyendo Cuestionario 1: {e}")


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
            st.warning("⚠️ No hay taller seleccionado. Ve a 'Configuraciones' para seleccionar una fecha.")
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
    
    context_text = ""
    if not df0.empty:
        context_text = "\n".join([
            f"{i+1}) " + " | ".join([f"{k}={v}" for k, v in row.items()])
            for i, row in enumerate(df0.to_dict('records')[:30])
        ])

    st.session_state["form0_context_text"] = context_text

  
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

    st.markdown("---")
    st.caption("Usa las flechas de la barra lateral para continuar con el siguiente paso del taller.")


def render_neutral_news_page():
    """Genera una noticia neutral basada en el tema dominante y el contexto del Form 0."""
    st.header("📰 Noticia neutral del taller")

    OPENAI = _read_secrets("OPENAI_API_KEY", "")
    if not OPENAI:
        st.error("Configura la clave OPENAI_API_KEY en secrets para generar la noticia.")
        return

    dominant_theme = st.session_state.get("dominant_theme")
    if not dominant_theme:
        st.warning("Primero identifica el tema dominante en ‘Análisis y tema dominante’.")
        st.caption("Usa la flecha izquierda en la barra lateral para regresar y obtener el tema.")
        return

    workshop_date = st.session_state.get("selected_workshop_date")
    form0_context = st.session_state.get("form0_context_text", "")

   # Cargar Form 0 para extraer fecha de implementación y municipio
    FORMS_SHEET_ID = _forms_sheet_id()
    FORM0_TAB = _read_secrets("FORM0_TAB", "")
    SA = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")
    
    fecha_implementacion = None
    municipio = None
    estado = None
    
    if FORMS_SHEET_ID and FORM0_TAB and SA and workshop_date:
        try:
            df0 = _sheet_to_df(FORMS_SHEET_ID, FORM0_TAB)
            if not df0.empty:
                df0 = _filter_df_by_date(df0, workshop_date)
                if not df0.empty:
                    fecha_cols = [col for col in df0.columns if 'fecha' in col.lower() and 'implementacion' in col.lower()]
                    municipio_cols = [col for col in df0.columns if 'municipio' in col.lower()]
                    
                    if fecha_cols:
                        fecha_implementacion = df0[fecha_cols[0]].iloc[0] if pd.notna(df0[fecha_cols[0]].iloc[0]) else None
                    if municipio_cols:
                        municipio = df0[municipio_cols[0]].iloc[0] if pd.notna(df0[municipio_cols[0]].iloc[0]) else None
                    estado_cols = [col for col in df0.columns if 'estado' in col.lower()]
                    if estado_cols:
                        estado = df0[estado_cols[0]].iloc[0] if pd.notna(df0[estado_cols[0]].iloc[0]) else None
        except Exception as e:
            st.caption(f"Nota: No se pudieron cargar datos del Form 0 para contexto adicional: {e}")

    st.markdown(f"**Tema dominante actual:** `{dominant_theme}`")
    if workshop_date:
        st.caption(f"Contextualizas esta noticia para el taller del {workshop_date}.")
    if municipio:
        st.caption(f"📍 Municipio: {municipio}")
    if estado:
        st.caption(f"🗺️ Estado: {estado}")
    if fecha_implementacion:
        st.caption(f"📅 Fecha de implementación: {fecha_implementacion}")

    neutral_news = st.session_state.get("neutral_news_text")
    if neutral_news:
        st.subheader("📄 Última noticia generada")
        st.markdown(neutral_news)

    st.markdown("---")

    if st.button("✍️ Mostrar noticia neutral", type="primary", use_container_width=True):
        # Preparar contexto de fecha y ubicación
        contexto_fecha = ""
        if fecha_implementacion:
            contexto_fecha = f"- El hecho debe haber ocurrido alrededor de la fecha de implementación del taller: {fecha_implementacion}."
        
        # Construir contexto de ubicación de forma flexible
        if municipio and estado:
            contexto_ubicacion = f"el municipio de {municipio}, {estado}"
        elif municipio:
            contexto_ubicacion = f"el municipio de {municipio}"
        elif estado:
            contexto_ubicacion = f"el estado de {estado}"
        else:
            contexto_ubicacion = "la región correspondiente"
        
        prompt = f"""
    Contexto general:
En un ejercicio previo, se identificaron los tópicos dominantes {dominant_theme} y las emociones asociadas que generan percepciones de inseguridad según las respuestas del [formulario 1]. Con base en esos hallazgos, se elaboró una nube de palabras que refleja los temas y emociones predominantes.

Rol:
Eres reportero de un medio independiente mexicano (por ejemplo, Animal Político, Aristegui Noticias, Proceso o Nexos). Debes redactar una **noticia breve, objetiva y verificable**, como si fuera una nota de crónica informativa publicada hoy.

Instrucción:
Redacta una **noticia factual** sobre un **hecho o suceso reciente** relacionado con el tema dominante {dominant_theme}.
El texto debe:

- Presentar un **hecho concreto y reciente** (por ejemplo, un incidente, operativo, declaración oficial o evento público).
{contexto_fecha}
- Estar contextualizado en {contexto_ubicacion}
- Mantener una **estructura noticiosa clásica**:
  - **Título factual y conciso.**
  - **Primer párrafo (lead):** qué ocurrió, dónde, cuándo y a quiénes involucró.
  - **Segundo párrafo:** detalles del hecho (acciones de autoridades, testigos, contexto inmediato).
  - **Tercer párrafo:** contexto breve (por qué es relevante o cómo se relaciona con el tema dominante).
- Evitar cualquier tono analítico, especulativo o explicativo.
- No usar expresiones como “según expertos”, “se ha observado”, o “el fenómeno refleja”.
- Permitir solo menciones genéricas a fuentes (“de acuerdo con reportes oficiales”, “autoridades locales informaron”).
- Utilizar oraciones cortas, lenguaje informativo y directo.

Estilo:
- Periodismo mexicano independiente, tono sobrio y neutral.
- Sin adjetivos, juicios, análisis ni interpretaciones.
- Prioriza la precisión y la claridad.
- Longitud aproximada: **100 a 150 palabras**.

Formato de salida esperado:
[Título de la noticia]
[Cuerpo de 1 a 2 párrafos breves, estilo nota informativa]
"""
        try:
            client = _openai_client()
            with st.spinner("🧠 Mostrando noticia neutral con IA…"):
                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                    temperature=0.35,
                    max_tokens=700,
                        messages=[
                        {
                            "role": "system",
                            "content": "Eres un periodista profesional. Escribes notas informativas con precisión y neutralidad." \
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
            news_text = resp.choices[0].message.content.strip()
            st.session_state["neutral_news_text"] = news_text
            _log_debug_message(
                "Noticia neutral generada correctamente.",
                level="success",
                context="Noticia neutral",
            )
            st.markdown(news_text)
        except Exception as e:
            st.error(f"No pude generar la noticia neutral automáticamente: {e}")

    st.caption("Puedes volver a generar la noticia si necesitas otra versión. Usa las flechas de la barra lateral para continuar.")


def render_form2_page():
    """Cuestionario 2 — QR y guía para continuar con noticias."""
    st.header("📲 Cuestionario 2 — reacciones ante noticias")

    FORM2_URL = _read_secrets("FORM2_URL", "")
    if FORM2_URL:
        qr = _qr_image_for(FORM2_URL)
        if qr:
            left, center, right = st.columns([1, 2, 1])
            with center:
                st.image(qr, caption="Escanea para abrir Cuestionario 2", width=360)
        st.link_button("📝 Abrir Cuestionario 2", FORM2_URL, use_container_width=True)
    else:
        st.warning("Configura FORM2_URL en secrets para mostrar el QR y el enlace.")
    st.markdown("---")
    dom = st.session_state.get("dominant_theme")
    if not dom:
        st.warning("Primero identifica el tema dominante en ‘Análisis y tema dominante’.")
        st.caption("Usa la flecha izquierda en la barra lateral para regresar a esa sección.")
        return

    st.caption("Averigue que todo el mundo tenga abierto este formulario. Luego, avanza con la flecha derecha de la barra lateral para ir a las noticias.")


def _find_matching_image(tags: list[str], folder="images"):
    """Busca en /images una imagen cuyo nombre contenga alguno de los tags indicados."""
    import os
    import difflib
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

    parts = re.split(r'\n?\s*[-—]{3,}\s*\n?', raw)
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
    """Muestra 3 noticias tipo WhatsApp y permite generarlas desde esta página."""
    st.header("💬 Noticias del taller")

    dominant_theme = st.session_state.get("dominant_theme")
    generate_disabled = dominant_theme is None

    neutral_story = st.session_state.get("neutral_news_text")
    if not neutral_story:
        st.warning("Genera primero la noticia neutral para poder crear las versiones con encuadres.")
        st.caption("Ve a ‘Noticia neutral del taller’, genere la nota base y vuelve aquí.")
        generate_disabled = True

    if st.button("🔎 Mostrar noticias sobre este tema", type="primary", use_container_width=True, disabled=generate_disabled):
        if generate_disabled:
            st.warning("Primero completa los pasos anteriores (tema dominante y noticia neutral).")
        else:
            try:
                with st.spinner("Mostrando noticias con los tres encuadres…"):
                    generated = generate_news(dominant_theme, neutral_story)
                    for i, block in enumerate(generated):
                        if not block.get("image"):
                            fallback = f"images/taller{i+1}.jpeg"
                            if os.path.isfile(fallback):
                                block["image"] = fallback
                st.session_state["generated_news_blocks"] = generated
                joined = "\n\n---\n\n".join([f"Encuadre {i+1}:\n{block['text']}" for i, block in enumerate(generated)])
                st.session_state["generated_news_raw"] = joined
                st.session_state.news_index = 0
                _log_debug_message(
                    "Noticias con encuadres generadas.",
                    level="success",
                    context="Noticias del taller",
                    data={"encuadres": [block.get("encuadre") for block in generated]},
                )
                st.caption("Noticias listas. Usa las flechas de la barra lateral para recorrerlas.")
            except Exception as e:
                st.error(f"Error generando noticias con encuadres: {e}")

    st.markdown("---")

    if not dominant_theme:
        st.warning("⚠️ Aún no se ha identificado el tema dominante. Regresa a ‘Análisis y tema dominante’.")
        return

    st.info(f"Tema dominante actual: **{dominant_theme}**")

    st.markdown("---")

    stories = st.session_state.get("generated_news_blocks")
    if not stories:
        raw = st.session_state.get("generated_news_raw")
        if raw:
            stories = _parse_news_blocks(raw)
        else:
            st.info("Haz clic en el botón superior para generar las noticias basadas en el tema dominante.")
        return

    if not stories:
        st.warning("No se pudieron interpretar noticias desde el texto generado.")
        return

    idx = int(st.session_state.get("news_index", 0))
    if idx >= len(stories):
        idx = 0
        st.session_state.news_index = 0

    encuadres = [story.get("encuadre") or f"Encuadre {i+1}" for i, story in enumerate(stories)]
    if idx < len(encuadres):
        st.caption(f"Encuadre: {encuadres[idx]}")

    story = stories[idx]
    story_dict = story if isinstance(story, dict) else {"text": story.get("text") if hasattr(story, "get") else story, "image": story.get("image") if hasattr(story, "get") else None, "encuadre": story.get("encuadre") if hasattr(story, "get") else None}

    _typing_then_bubble(
        message_text=story_dict.get("text", ""),
        image_path=story_dict.get("image"),
        encuadre=None,
    )

def render_news_comparison_page():
    """Visualiza las tres versiones de la noticia para comparar encuadres."""
    st.header("Noticias 1, 2 y 3")

    news_blocks = st.session_state.get("generated_news_blocks")
    if not news_blocks:
        st.warning("Aún no se han generado las noticias con encuadres. Ve a 'Noticias del taller' y créalas primero.")
        return

    st.caption("1. Observa cómo cambia la narrativa del mismo hecho según el encuadre.")
    st.caption("2. Utiliza esta comparativa para discutir tono, sesgos y emociones que provoca cada versión.")
    st.markdown("---")

    # Mostrar cada noticia en un desplegable
    for idx, block in enumerate(news_blocks, 1):
        with st.expander(f"📱 Noticia {idx}", expanded=False):
            _typing_then_bubble(
                message_text=block.get("text", "(sin contenido)"),
                image_path=block.get("image"),
                encuadre=None,
            )
    st.markdown("---")

def render_explanation_page():
    """📘 Página intermedia entre Noticias y Análisis final."""
    st.header("📘 Explicación del Taller")
    st.markdown("""
    En esta sección puedes revisar el contexto general del taller antes de pasar al análisis final.
    """)

    st.subheader("Hilo Conductor")
    st.text_area("Lo que acabamos de ver", "Por ejemplo, los mensajes que vimos corresponden a un mismo evento pero con encuadres narrativos distintos.", height=150)

    st.subheader("Descripción de que es un encuadre")
    st.text_area("descripcion_encuadres", "Un encuadre narrativo es la técnica de enmarcar o delimitar la porción de realidad que se va a presentar en una historia, ya sea escrita o visual, influyendo en cómo el espectador o lector interpreta los eventos y emociones" , height=150)

    st.subheader("Encuadres de la noticia")
    st.text_area("descripcion_encuadres_usado", " Descripción del encuadre de desconfianza y responsabilización de actores. Cuestiona la legitimidad institucional o mediática, generando incertidumbre y cinismo ciudadano. Atribuye causas o soluciones a actores específicos (individuos, instituciones, grupos). Influye en la percepción pública sobre quién tiene la culpa o el mérito. Descripción del encuadre de  polarización social y exclusión. Amplifica divisiones sociales y políticas mediante la apelación a emociones intensas (miedo, ira, resentimiento). Favorece el enfrentamiento simbólico y la construcción de 'enemigos'. Atribuye la causa de los problemas a ciertos grupos o sectores sociales sin evidencia.", height=150)

    st.markdown("---")


def render_conclusion_page():
    """Página de conclusión con gráficos de las últimas 3 preguntas de Form 2."""
    st.header("🎯 Conclusión")

    FORMS_SHEET_ID = _forms_sheet_id()
    FORM2_TAB = _read_secrets("FORM2_TAB", "")
    SA = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")
    workshop_date = st.session_state.get("selected_workshop_date")

    if not (FORMS_SHEET_ID and FORM2_TAB and SA):
        st.warning("⚠️ Configura las credenciales en 'Configuraciones' para ver los resultados.")
        return

    if not workshop_date:
        st.warning("⚠️ Selecciona una fecha de taller en 'Configuraciones'.")
        return

    try:
        with st.spinner("📥 Cargando datos de Form 2..."):
            df_form2 = _sheet_to_df(FORMS_SHEET_ID, FORM2_TAB)

        if df_form2.empty:
            st.warning("⚠️ No hay datos en Form 2.")
            return

        # Filtrar por fecha del taller
        df_form2 = _filter_df_by_date(df_form2, workshop_date)

        if df_form2.empty:
            st.warning(f"⚠️ No hay datos de Form 2 para el taller del {workshop_date}.")
            return

        metadata_cols = ["Marca temporal", "Ingresa el número asignado en la tarjeta que se te dio"]
        metadata_patterns = ["marca", "temporal", "tarjeta", "número", "numero", "number", "card"]

        question_cols = []
        for col in df_form2.columns:
            col_lower = col.lower().strip()
            if any(pattern in col_lower for pattern in metadata_patterns):
                continue
            if col in metadata_cols:
                continue
            question_cols.append(col)

        if len(question_cols) < 3:
            st.warning(f"⚠️ Se encontraron menos de 3 preguntas en Form 2. Columnas encontradas: {len(question_cols)}")
            st.caption(f"Columnas detectadas: {', '.join(question_cols[:10])}")
            return

        last_3_questions = question_cols[-3:]
        card_column_candidates = [col for col in df_form2.columns if "tarjeta" in col.lower()]
        card_column = card_column_candidates[0] if card_column_candidates else None

        st.markdown(
            "Gracias por completar juntos este taller! A continuación tienes un pequeño análisis final de "
            "vuestras respuestas de los 3 encuadres narrativos. Veamos cuáles son las respuestas correctas."
        )
        st.success(f"✅ Datos cargados: {len(df_form2)} respuestas del taller del {workshop_date}")
        st.markdown("---")

        encuadre_correcto_map = {
            1: "encuadre 1",
            2: "encuadre 2",
            3: "encuadre 3",
        }

        chart_columns = st.columns(3, gap="large")
        summary_details = []

        for idx, question_col in enumerate(last_3_questions, 1):
            column = chart_columns[idx - 1]
            with column:
                st.subheader(f"Noticia {idx}")
                st.caption(question_col)

                responses = df_form2[question_col].dropna()
                responses = responses.astype(str).str.strip()
                responses = responses[responses != ""]

                if responses.empty:
                    st.info("No hay respuestas para esta pregunta.")
                    summary_details.append(
                        {"idx": idx, "percentage": 0.0, "correct_label": encuadre_correcto_map.get(idx, "encuadre")}
                    )
                    continue

                value_counts = responses.value_counts()
                total = len(responses)
                chart_data = pd.DataFrame({
                    "Opción": value_counts.index,
                    "Cantidad": value_counts.values,
                    "Porcentaje": (value_counts / total * 100).round(1)
                })

                correct_label = encuadre_correcto_map.get(idx, "")
                chart_data["Es correcta"] = chart_data["Opción"].astype(str).str.lower().apply(
                    lambda option: correct_label in option if correct_label else False
                )

                fig = px.bar(
                    chart_data,
                    x="Opción",
                    y="Porcentaje",
                    text="Porcentaje",
                    labels={"Porcentaje": "Porcentaje (%)", "Opción": "Opción seleccionada"},
                    color="Es correcta",
                    color_discrete_map={True: "#2ecc71", False: "#7f7f7f"},
                    title=f"Encuadre de noticia {idx}",
                )
                fig.update_traces(texttemplate='%{text}%', textposition='outside', marker_line_width=0)
                fig.update_layout(
                    height=420,
                    xaxis_title="",
                    yaxis_title="Porcentaje (%)",
                    showlegend=False,
                    margin=dict(l=20, r=20, t=50, b=20)
                )

                st.plotly_chart(fig, use_container_width=True)

                correct_match = chart_data[
                    chart_data["Opción"].astype(str).str.lower().str.contains(correct_label)
                ]
                if not correct_match.empty:
                    correct_pct = float(correct_match["Porcentaje"].iloc[0])
                    option_label = correct_match["Opción"].iloc[0]
                else:
                    correct_pct = 0.0
                    option_label = correct_label

                summary_details.append({
                    "idx": idx,
                    "percentage": correct_pct,
                    "correct_label": correct_label or option_label,
                    "option_label": option_label,
                })

        summary_lines = []
        for info in summary_details:
            percentage_label = f"{info['percentage']:.1f}%"
            summary_lines.append(
                f"Noticia {info['idx']} : {percentage_label} : la respuesta correcta era {info['correct_label']}"
            )

        st.markdown("<br>".join(summary_lines), unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("Preguntas Generativa Fija")
        st.caption("Gap filler para cerrar el taller")

        with st.container():
            st.subheader("Lista de recomendaciones para actuar")
            st.text_area("Recomendaciones", "Escribe aquí los copies o acciones sugeridas 😊", height=200)

        material_assets = [
            {
                "label": "Resumen completo del taller",
                "file": "material/resumen_taller.pdf",
            },
            {
                "label": "Guía complementaria breve",
                "file": "material/guia_complementaria.pdf",
            },
        ]
        st.markdown("---")
        st.subheader("Descarga el taller en PDF")
        cols_qr = st.columns(len(material_assets))
        for col, asset in zip(cols_qr, material_assets):
            asset_url = (
                "https://raw.githubusercontent.com/"
                "MottumData/streamlit-information-integrity-workshop/main/"
                f"{asset['file']}"
            )
            qr_image = _qr_image_for(asset_url)
            with col:
                st.caption(asset["label"])
                if qr_image:
                    st.image(
                        qr_image,
                        width=200,
                        caption=f"Escanea para descargar {asset['label']}",
                    )
                st.markdown(f"[Descargar {asset['label']}]({asset_url})")

        tarjetas_acertadas = []
        if card_column:
            expected_labels = ["encuadre 1", "encuadre 2", "encuadre 3"]
            subset = df_form2[[card_column] + last_3_questions].dropna(subset=[card_column])
            for _, row in subset.iterrows():
                tarjeta = str(row[card_column]).strip()
                if not tarjeta:
                    continue

                acertadas = True
                for i, question_col in enumerate(last_3_questions, 1):
                    respuesta = str(row.get(question_col, "")).lower()
                    expected = expected_labels[i - 1]
                    if expected not in respuesta:
                        acertadas = False
                        break
                if acertadas and tarjeta not in tarjetas_acertadas:
                    tarjetas_acertadas.append(tarjeta)

        if tarjetas_acertadas:
            tarjeta_ganadora = tarjetas_acertadas[0]
            st.markdown(
                f"**Enhorabuena!! Tarjeta {tarjeta_ganadora} por identificar 3/3 encuadres narrativos correctos!**"
            )

    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {e}")
        import traceback
        with st.expander("Detalles del error"):
            st.code(traceback.format_exc())


def render_workshop_insights_page():
    """Dashboard + (debajo) síntesis automática con datos reales (Form 0/1/2/3/4 si están conectados)."""
    st.header("📊 Análisis final del taller")
    from services.ai_analysis import (
            analyze_emotions_json,
            analyze_gender_impacts_json,
            analyze_general_json
    )

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

            with st.spinner("📤 Actualizando datos centralizados en Google Sheets..."):
                _write_df_to_sheet(
                    FORMS_SHEET_ID,
                    "Datos Centralizados Form2",
                    df_normalized,
                    clear_existing=True,
                )
                appended = _append_df_to_sheet(
                    FORMS_SHEET_ID,
                    "Datos centralizados",
                    df_normalized,
                )

            _log_debug_message(
                "Datos centralizados actualizados en Google Sheets.",
                level="success",
                context="Preparación de análisis final",
                data={
                    "filas": int(len(df_normalized)),
                    "tablas": ["Datos Centralizados Form2", "Datos centralizados"],
                },
            )
            st.caption(
                "Se actualizó 'Datos Centralizados Form2' y se anexaron filas nuevas (si las hubo) en 'Datos centralizados'."
            )

            if not appended:
                st.warning(
                    "No se generaron filas nuevas para anexar en 'Datos centralizados'."
                )
        except Exception as e:
            st.error(f"❌ Error procesando datos: {e}")
            import traceback
            with st.expander("Detalles del error"):
                st.code(traceback.format_exc())

    st.markdown("---")

    st.subheader("Dashboard (Looker Studio)")
    import streamlit.components.v1 as components
    try:
        components.html(
            """
        <style>
            .responsive-report {
                position: relative;
                width: 100%;
                padding-bottom: 56.25%; /* 16:9 ratio */
                height: 0;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 10px rgba(0,0,0,0.06);
            }
            .responsive-report iframe {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                border: none;
            }
        </style>
        <div class="responsive-report">
            <iframe src="https://lookerstudio.google.com/embed/reporting/cba53d78-d687-4929-aed6-dfb683841f06/page/p_cbx8w44sxd"
                    allowfullscreen="true"
                    mozallowfullscreen="true"
                    webkitallowfullscreen="true">
            </iframe>
        </div>
            """,
            height=800
        )
    except Exception:
        st.info("Agrega aquí el embed público de tu reporte de Looker Studio.")

    st.markdown("---")

    # --- Cargar datos para análisis ---
    st.subheader("📊 Cargar datos para análisis")
    st.caption("Carga y prepara los datos combinados de los cuestionarios para los análisis generativos.")
    
    # Mostrar información sobre el taller seleccionado
    workshop_date = st.session_state.get("selected_workshop_date")
    if workshop_date:
        st.info(f"📅 Analizando respuestas del taller del {workshop_date}")
    else:
        st.warning("⚠️ No hay taller seleccionado. Ve a 'Configuraciones' para seleccionar una fecha.")

    if st.button("📥 Cargar datos combinados", type="primary", use_container_width=True):
        # 1) Lee datos combinados
        df_all = None
        join_key = None
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

        if df_all is None:
            st.warning("No se recibieron datos combinados para analizar.")
            return

        if isinstance(df_all, pd.DataFrame) and df_all.empty:
            st.warning("No hay respuestas combinadas aún para analizar para este taller.")
            return

        # 2) Muestra un vistazo mínimo (opcional)
        with st.expander("👀 Muestra de datos combinados utilizados (primeras 10 filas)"):
            df_preview = df_all
            if workshop_date:
                if "Taller" in df_all.columns:
                    df_preview = df_all[df_all["Taller"] == workshop_date]
                else:
                    date_col = _get_date_column_name(df_all)
                    if date_col:
                        df_dates = df_all.copy()
                        df_dates["_normalized_date"] = df_dates[date_col].apply(_normalize_date)
                        df_preview = df_dates[df_dates["_normalized_date"] == workshop_date]
                        if df_preview.empty:
                            df_preview = df_all
            st.dataframe(df_preview.head(50), use_container_width=True)

        # 3) Separar formularios para normalización y contexto
        def _extract_form(df_source, tag):
            if "source_form" not in df_source.columns:
                return pd.DataFrame()
            subset = df_source[df_source["source_form"] == tag].copy()
            if subset.empty:
                return pd.DataFrame()
            return subset.drop(columns=["source_form"], errors="ignore")

        df_form0 = _extract_form(df_all, "F0")
        df_form1 = _extract_form(df_all, "F1")
        df_form2 = _extract_form(df_all, "F2")

        if df_form1.empty or df_form2.empty:
            st.warning("No hay datos suficientes de Form1 o Form2 para generar el análisis.")
            return

        # 4) Contexto del Form 0 en caso de que no esté disponible en sesión
        form0_context_text = st.session_state.get("form0_context_text", "")
        if not form0_context_text and not df_form0.empty:
            form0_context_text = "\n".join([
                f"{i+1}) " + " | ".join([f"{k}={v}" for k, v in row.items() if pd.notna(v)])
                for i, row in enumerate(df_form0.to_dict('records')[:30])
            ])

        # 5) Normalizar datos para el análisis final
        try:
            df_normalized = _normalize_form_data(df_form1, df_form2, workshop_date)
        except Exception as e:
            st.error(f"No se pudieron normalizar los datos: {e}")
            return

        if isinstance(df_normalized, pd.DataFrame) and df_normalized.empty:
            st.warning("La normalización devolvió un conjunto vacío. Revisa que Form1/Form2 tengan respuestas válidas.")
            return

        # Persistir datos para los análisis adicionales
        st.session_state["analysis_df_all"] = df_all
        st.session_state["analysis_df_normalized"] = df_normalized
        st.session_state["analysis_form0_context"] = form0_context_text
        st.session_state["analysis_df_form0"] = df_form0
        st.session_state["analysis_df_form1"] = df_form1
        
        st.success("✅ Datos cargados y preparados. Ahora puedes ejecutar los análisis generativos.")

    df_all_cached = st.session_state.get("analysis_df_all")
    form0_context_cached = st.session_state.get("analysis_form0_context", "")
    dominant_theme_cached = st.session_state.get("dominant_theme", "")

    st.markdown("### Analizar emociones por encuadre")
    with st.expander("¿Qué calcula este análisis?"):
        st.markdown(
            "Explora cómo varían las emociones reportadas por las y los participantes según el encuadre de cada noticia. "
            "Sirve para debatir qué narrativas despiertan mayor empatía, temor o rechazo."
        )
    if st.button("➕ Agregar análisis generativo", key="btn_emociones"):
        if df_all_cached is None or not isinstance(df_all_cached, pd.DataFrame) or df_all_cached.empty:
            st.warning("Primero ejecuta '📥 Cargar datos combinados' para preparar los datos.")
        else:
            data = analyze_emotions_json(df_all_cached, dominant_theme_cached, form0_context_cached)
            markdown_output = _format_emotions_json_to_markdown(data)
            st.markdown(markdown_output)


    st.markdown("### Analizar impactos por género")
    with st.expander("¿Qué revisa este bloque?"):
        st.markdown(
            "Compara percepciones y emociones diferenciadas por género para identificar brechas o sensibilidades específicas. "
            "Útil para ajustar la conversación y asegurar voces diversas en el taller."
        )
    if st.button("➕ Agregar análisis generativo", key="btn_genero"):
        if df_all_cached is None or not isinstance(df_all_cached, pd.DataFrame) or df_all_cached.empty:
            st.warning("Primero ejecuta '📥 Cargar datos combinados' para preparar los datos.")
        else:
            data = analyze_gender_impacts_json(df_all_cached, dominant_theme_cached, form0_context_cached)
            markdown_output = _format_gender_json_to_markdown(data)
            st.markdown(markdown_output)


    st.markdown("### Análisis general del taller")
    with st.expander("¿Qué integra este resumen?"):
        st.markdown(
            "Genera una síntesis transversal con los hallazgos principales del taller: emociones dominantes, confianza, "
            "elementos clave y posibles sesgos a profundizar en la discusión final."
        )
    if st.button("➕ Agregar análisis generativo", key="btn_general"):
        if df_all_cached is None or not isinstance(df_all_cached, pd.DataFrame) or df_all_cached.empty:
            st.warning("Primero ejecuta '📥 Cargar datos combinados' para preparar los datos.")
        else:
            data = analyze_general_json(df_all_cached, dominant_theme_cached, form0_context_cached)
            markdown_output = _format_general_json_to_markdown(data)
            st.markdown(markdown_output)
            st.session_state["analysis_final_markdown"] = markdown_output


# ---------- ROUTER (etiquetas/orden solicitados) ----------
ROUTES = {
    "Configuraciones": render_setup_trainer_page,      
    "Introducción al taller": render_introduction_page,           
    "Cuestionario 1": render_form1_page,                          
    "Análisis y tema dominante": render_analysis_trends_page,   
    "Noticia neutral del taller": render_neutral_news_page,
    "Cuestionario 2": render_form2_page,                          
    "Noticias del taller": render_news_flow_page,
    "Noticias 1, 2 y 3": render_news_comparison_page,
    "Explicacion del taller": render_explanation_page,                
    "Análisis final del taller": render_workshop_insights_page,
    "Conclusión": render_conclusion_page,   
}

def main():
    import base64
    import os

    # --- Estado inicial: abrir en Introducción ---
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Introducción al taller"

    # --- ESTILOS GLOBALES PARA BOTONES (fondo rojo y texto blanco) ---
    st.markdown("""
    <style>
    /* Estilos globales para botones primarios */
    .stButton > button[kind="primary"] {
        background-color: #dc3545 !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        border-radius: 0.5rem !important;
        transition: background-color 0.3s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #c82333 !important;
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- TIPOGRAFÍA GLOBAL (alineada con la introducción) ---
    st.markdown("""
    <style>
    body, p, li {
        font-family: "Inter", "Helvetica Neue", Arial, sans-serif !important;
        font-size: 1.2rem !important;
        line-height: 1.8 !important;
        color: #333333 !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: "Inter", "Helvetica Neue", Arial, sans-serif !important;
        color: #004b8d !important;
        font-weight: 600 !important;
        margin-top: 1.2rem !important;
        margin-bottom: 0.6rem !important;
    }
    h1 { font-size: 2.4rem !important; }
    h2 { font-size: 2rem !important; }
    h3 { font-size: 1.6rem !important; }

    ul, ol {
        margin-left: 1.5rem !important;
        font-size: 1.2rem !important;
        line-height: 1.8 !important;
    }
    a {
        color: #004b8d !important;
        text-decoration: none !important;
    }
    strong {
        color: #1f2a44 !important;
    }
    [data-testid="stMarkdownContainer"] code {
        font-size: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- SIDEBAR PERSONALIZADO ---
    with st.sidebar:
        st.markdown("""
        <style>
        /* Sidebar background and layout */
        [data-testid="stSidebar"] {
            background-color: #f6f7f9 !important;
            border-right: 1px solid #e0e0e0;
            padding: 1.2rem 1rem 1rem 1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between; /* pushes content and logo apart */
        }

        /* Buttons */
        [data-testid="stSidebar"] button {
            border-radius: 10px !important;
            font-weight: 500 !important;
            margin-bottom: 0.25rem !important;
            border: 1px solid #d8dee4 !important;
            background-color: #ffffff !important;
            color: #004b8d !important;
        }
        [data-testid="stSidebar"] button:disabled {
            background-color: #f2f3f5 !important;
            color: #9aa5b1 !important;
            border-color: #e0e6ee !important;
            cursor: not-allowed !important;
            opacity: 0.8 !important;
        }
        [data-testid="stSidebar"] button:hover {
            background-color: #eaf2f8 !important;
            border-color: #004b8d !important;
        }

        .sidebar-arrow-caption {
            font-size: 0.85rem;
            color: #4a5568;
            margin-top: 0.15rem;
            text-align: center;
        }
        /* Current page text */
        .sidebar-current {
            text-align: center;
            color: #555;
            font-size: 14px;
            margin-top: 0.4rem;
            margin-bottom: 0.4rem;
        }

        /* Logo perfectly anchored at bottom */
        .sidebar-logo {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: auto;        /* push logo to the bottom */
            padding-top: 1rem;
        }
        .sidebar-logo img {
            width: 100px;
            opacity: 0.9;
        }
        [data-testid="stSidebar"] button[kind="primary"] {
            background-color: #dc3545 !important;  /* Red background */
            color: #ffffff !important;             /* White text */
            border: none !important;
            font-weight: 600 !important;           /* Slightly bolder text */
            letter-spacing: 0.3px !important;
        }
        [data-testid="stSidebar"] button[kind="primary"]:hover {
            background-color: #c82333 !important;  /* Darker red on hover */
            color: #ffffff !important;             /* Keep white text */
        }

        </style>
        """, unsafe_allow_html=True)


        # --- Botones principales ---
        if st.button("🏠 Inicio", use_container_width=True):
            st.session_state.current_page = "Introducción al taller"
            st.rerun()

        if st.button("⚙️ Configuraciones", use_container_width=True):
            st.session_state.current_page = "Configuraciones"
            st.rerun()

        st.markdown("---")

        # Mostrar la página actual
        st.markdown(
            f"<div class='sidebar-current'>Página actual:<br><b>{st.session_state.current_page}</b></div>",
            unsafe_allow_html=True
        )

        st.markdown("---")

        page_keys = list(ROUTES.keys())
        try:
            nav_ctx = get_navigation_context(st.session_state.current_page, page_keys)
        except ValueError:
            nav_ctx = None

        if nav_ctx:
            current_page = st.session_state.current_page
            news_raw = st.session_state.get("generated_news_raw")
            news_blocks = _parse_news_blocks(news_raw) if (current_page == "Noticias del taller" and news_raw) else []
            news_index = int(st.session_state.get("news_index", 0))
            news_count = len(news_blocks)
            news_mode = current_page == "Noticias del taller" and news_count > 0

            has_prev_news = news_mode and news_index > 0
            has_next_news = news_mode and news_index < news_count - 1

            prev_disabled = not has_prev_news and not nav_ctx["previous"]
            next_disabled = not has_next_news and not nav_ctx["next"]

            nav_cols = st.columns(2, gap="small")
            with nav_cols[0]:
                if st.button("⬅️", use_container_width=True, disabled=prev_disabled, key="sidebar_prev"):
                    if has_prev_news:
                        st.session_state.news_index = news_index - 1
                    elif nav_ctx["previous"]:
                        st.session_state.current_page = nav_ctx["previous"]
                    st.rerun()
                st.markdown('<div class="sidebar-arrow-caption">Anterior</div>', unsafe_allow_html=True)

            with nav_cols[1]:
                if st.button("➡️", use_container_width=True, disabled=next_disabled, key="sidebar_next"):
                    if has_next_news:
                        st.session_state.news_index = news_index + 1
                    elif nav_ctx["next"]:
                        st.session_state.current_page = nav_ctx["next"]
                    st.rerun()
                st.markdown('<div class="sidebar-arrow-caption">Siguiente</div>', unsafe_allow_html=True)
            if current_page == "Conclusión":
                workshop_date = st.session_state.get("selected_workshop_date", "Sin fecha asignada")
                dominant_theme = st.session_state.get("dominant_theme", "Sin tema dominante")
                neutral_news = st.session_state.get("neutral_news_text", "No se ha generado una noticia neutral.")
                form0_df = st.session_state.get("analysis_df_form0")
                form1_df = st.session_state.get("analysis_df_form1")
                normalized_df = st.session_state.get("analysis_df_normalized")

                def _df_section(title, df):
                    if df is None or df.empty:
                        return f"{title}\nSin datos disponibles."
                    preview = df.head(20).astype(str)
                    csv_content = preview.to_csv(index=False)
                    return f"{title}\n{csv_content}"

                analysis_json_f1 = st.session_state.get("analysis_json_f1")
                analysis_text = (
                    json.dumps(analysis_json_f1, ensure_ascii=False, indent=2)
                    if analysis_json_f1
                    else "Aún no se ha generado el análisis del tema dominante."
                )

                analysis_final_markdown = st.session_state.get(
                    "analysis_final_markdown",
                    "Aún no se ha generado el análisis textual final del taller."
                )

                generated_blocks = st.session_state.get("generated_news_blocks") or []

                summary_parts = [
                    "Taller de Integridad de la Información",
                    f"Fecha del taller: {workshop_date}",
                    f"Tema dominante: {dominant_theme}",
                    "",
                    _df_section("Tabla de respuestas Form 0", form0_df),
                    "",
                    _df_section("Tabla de respuestas Form 1", form1_df),
                    "",
                    "Texto de análisis de tema dominante:",
                    analysis_text,
                    "",
                    "Noticia neutral base:",
                    neutral_news,
                ]

                for idx, block in enumerate(generated_blocks, 1):
                    summary_parts.append("")
                    summary_parts.append(f"Noticia {idx} ({block.get('encuadre', 'sin encuadre')}):")
                    summary_parts.append(block.get("text", "(sin contenido)"))

                summary_parts.extend([
                    "",
                    _df_section("Tabla procesada (Form 1 + Form 2)", normalized_df),
                    "",
                    "Análisis textual final del taller:",
                    analysis_final_markdown,
                ])

                summary_text = "\n\n".join(summary_parts)
                st.download_button(
                    "Descargate el Taller!",
                    data=summary_text.encode("utf-8"),
                    file_name="resumen_taller.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="download_taller_button",
                )
        else:
            st.warning("Página actual fuera del flujo del taller.")

        st.markdown("---")

        # Logo PNUD centrado
        logo_path = "images/PNUD_logo.png"
        if os.path.isfile(logo_path):
            with open(logo_path, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f"""
                <div class="sidebar-logo">
                    <img src="data:image/png;base64,{logo_b64}" alt="Logo PNUD">
                </div>
                """,
                unsafe_allow_html=True
            )

    # --- CONTENIDO PRINCIPAL ---
    if st.session_state.get("selected_page") in ROUTES:
        st.session_state.current_page = st.session_state.selected_page
        st.session_state.selected_page = None

    ROUTES.get(st.session_state.current_page, lambda: st.info("Selecciona una página."))()


if __name__ == "__main__":
    main()
