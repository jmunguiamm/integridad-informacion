# app.py — Taller Integridad de la Información (Streamlit router and layout only)

import json
import re
import time
import os
import pandas as pd
import streamlit as st

# ---------- IMPORTS FROM MODULES ----------
from config.secrets import read_secrets, forms_sheet_id
from data.sheets import get_gspread_client, sheet_to_df, write_df_to_sheet
from data.cleaning import normalize_form_data, filter_df_by_date
from data.utils import get_date_column_name, normalize_date, get_available_workshop_dates, load_joined_responses
from components.whatsapp_bubble import typing_then_bubble, find_image_by_prefix, find_matching_image
from components.qr_utils import qr_image_for
from components.navigation import navigation_buttons
from components.utils import autorefresh_toggle
from services.ai_analysis import get_openai_client, analyze_reactions, analyze_trends
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
    parts = re.split(r'^\s*[-—]{3,}\s*$|\n{2,}', raw, flags=re.MULTILINE)
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

        # --- Siguiente paso del taller (en la página principal) ---
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 🚀 Si has configurado tu taller, estas listo para continuar")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Empezamos", use_container_width=True, type="primary"):
            st.session_state.current_page = "Configuraciones"
            st.rerun()


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

        # 🧠 Mostrar información de depuración (solo visible al formador)
    dominant_theme = st.session_state.get("dominant_theme", "(no definido)")
    st.info(f"Tema dominante actual: **{dominant_theme}**")

    # Debug visual opcional: listar imágenes detectadas para este tema
    from components.image_repo import get_images_for_dominant_theme
    theme_images = get_images_for_dominant_theme(dominant_theme)

    if theme_images:
        with st.expander("🖼️ Ver imágenes detectadas para este tema"):
            st.markdown("Estas son las imágenes asociadas al tema dominante en `/images/`:")
            cols = st.columns(min(len(theme_images), 3))
            for i, img in enumerate(theme_images):
                with cols[i % len(cols)]:
                    st.image(img, caption=os.path.basename(img), use_container_width=True)
    else:
        st.warning("⚠️ No se encontraron imágenes asociadas a este tema dominante en `/images/`.")
    
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

    # 🧩 Mostrar qué imagen se usó para esta noticia (debug)
    used_image = story.get("image")
    if used_image:
        st.caption(f"🖼️ Imagen utilizada: `{os.path.basename(used_image)}`")
    else:
        st.caption("⚠️ No se asignó imagen específica (usando fallback o nula).")

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

    st.subheader("📰 Hilo Conductor")
    st.text_area("Lo que acabamos de ver", "Por ejemplo, los mensajes que vimos corresponden a un mismo evento pero con encuadres narrativos distintos.", height=150)

    st.subheader("🧩 Descripción de que es un encuadre")
    st.text_area("descripcion_encuadres", "Un encuadre narrativo es la técnica de enmarcar o delimitar la porción de realidad que se va a presentar en una historia, ya sea escrita o visual, influyendo en cómo el espectador o lector interpreta los eventos y emociones" , height=150)

    st.subheader("Encuadres de la noticia")
    st.text_area("descripcion_encuadres_usado", " Descripción del encuadre de desconfianza y responsabilización de actores. Cuestiona la legitimidad institucional o mediática, generando incertidumbre y cinismo ciudadano. Atribuye causas o soluciones a actores específicos (individuos, instituciones, grupos). Influye en la percepción pública sobre quién tiene la culpa o el mérito. Descripción del encuadre de  polarización social y exclusión. Amplifica divisiones sociales y políticas mediante la apelación a emociones intensas (miedo, ira, resentimiento). Favorece el enfrentamiento simbólico y la construcción de 'enemigos'. Atribuye la causa de los problemas a ciertos grupos o sectores sociales sin evidencia.", height=150)

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
    Contexto:
    Se ha realizado un ejercicio donde se generaron tres noticias diferentes sobre un mismo evento, cada una con un encuadre narrativo distinto. Los participantes completaron un formulario indicando, para cada noticia:
    Emociones que sienten al leerla.
    Grado de confiabilidad que perciben en la información.
    Elementos clave que les llamaron la atención.
    
    Rol:
    Eres un experto analista y data vizualization master, y tienes que presentar los hallazgos y informaciones mas relevantes segun la tabla de datos cruzados (por numero de tarjeta) que has construido entre form1 y form2 y usando contexto del form0.
    Objetivo: analiza los siguientes puntos:
    1- cómo varían las emociones, el nivel de confianza y los componentes clave según el tipo de encuadre narrativo.
    2- que diferencias de percepción y reacción emocional a las noticias hay según el género.
    3- patrones emergentes y relaciones significativas entre variables  y en función de las respuestas identifica algunos sesgos que puedan estar asociados que no se hayan abordado  en los análisis por encuadre y por género.
    
    Formato:
    Genera por cada analisis un texto y un grafico explicativo
    
    Ejemplo:
    Mapa de calor (heatmap) que muestre intensidad emocional por género
    Boxplot o gráfico de violín para visualizar la dispersión del nivel de confianza por cada encuadre.
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
    "Configuraciones": render_setup_trainer_page,      
    "Introducción al taller": render_introduction_page,           
    "Cuestionario 1": render_form1_page,                          
    "Análisis y tema dominante": render_analysis_trends_page,   
    "Cuestionario 2": render_form2_page,                          
    "Noticias del taller": render_news_flow_page,
    "Explicacion del taller": render_explanation_page,                
    "Análisis final del taller": render_workshop_insights_page,   
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

    # --- SIDEBAR PERSONALIZADO ---
    with st.sidebar:
        st.markdown("""
        <style>
        /* Sidebar background and layout */
        [data-testid="stSidebar"] {
            background-color: #f6f7f9 !important;
            border-right: 1px solid #e0e0e0;
            padding: 1.5rem 1rem 1rem 1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between; /* pushes content and logo apart */
        }

        /* Buttons */
        [data-testid="stSidebar"] button {
            border-radius: 10px !important;
            font-weight: 500 !important;
            margin-bottom: 0.4rem !important;
            border: 1px solid #d8dee4 !important;
            background-color: #ffffff !important;
            color: #004b8d !important;
        }
        [data-testid="stSidebar"] button:hover {
            background-color: #eaf2f8 !important;
            border-color: #004b8d !important;
        }

        /* Current page text */
        .sidebar-current {
            text-align: center;
            color: #555;
            font-size: 14px;
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
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

        
        # --- Botón "Siguiente paso del taller" ---
        try:
            page_keys = list(ROUTES.keys())
            current_idx = page_keys.index(st.session_state.current_page)
            if current_idx < len(page_keys) - 1:
                next_page = page_keys[current_idx + 1]
                
                if st.button("➡️ Siguiente paso del taller", use_container_width=True, type="primary"):
                    st.session_state.current_page = next_page
                    st.rerun()
        except ValueError:
            st.warning("Página actual fuera del flujo del taller.")

        st.markdown("---")

        # Logo PNUD centrado
        logo_path = "images/logo_pnud.jpeg"
        if os.path.isfile(logo_path):
            with open(logo_path, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f"""
                <div class="sidebar-logo">
                    <img src="data:image/jpeg;base64,{logo_b64}" alt="Logo PNUD">
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
