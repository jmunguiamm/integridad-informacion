# app.py — Taller Integridad de la Información (versión con mejoras de navegación/QR/UX)

import os, json, re, time
from io import BytesIO
import pandas as pd
import streamlit as st
import difflib


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
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
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
    """Lee Form0, Form1, Form2 del MISMO Sheet (FORMS_SHEET_ID) y une por 'tarjeta'."""
    FORMS_SHEET_ID = _forms_sheet_id()

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
    if FORMS_SHEET_ID and FORM0_TAB and SA:
        df0 = _sheet_to_df(FORMS_SHEET_ID, FORM0_TAB)
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


def render_introduction_page():
    """🌎 Página de introducción con carrusel automático de imágenes locales."""
    import os
    import streamlit as st

    st.header("🌎 Introducción al Taller de Integridad de la Información")
    st.markdown("Bienvenid@ al taller de **Integridad de la Información**. Desliza las imágenes para conocer el contexto del proyecto y los pasos del ejercicio.")

    # --- Buscar imágenes en carpeta /images ---
    img_folder = "images"
    supported_exts = (".jpg", ".jpeg", ".png", ".gif")
    if not os.path.isdir(img_folder):
        os.makedirs(img_folder, exist_ok=True)

    all_imgs = [os.path.join(img_folder, f) for f in os.listdir(img_folder) if f.lower().endswith(supported_exts)]
    all_imgs.sort()  # orden alfabético

    if all_imgs:
        st.markdown("### 📸 Galería del taller")
        idx = st.slider("Desliza para explorar", 0, len(all_imgs)-1, 0, key="intro_slider")
        caption = os.path.basename(all_imgs[idx]).replace("_", " ").replace("-", " ").rsplit(".", 1)[0].capitalize()
        st.image(all_imgs[idx], caption=caption, use_container_width=True)
    else:
        st.warning("⚠️ No se encontraron imágenes en la carpeta `/images`. Agrega archivos .jpg, .png o .gif para mostrarlas aquí.")

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
    df = _sheet_to_df(FORMS_SHEET_ID, FORM1_TAB)


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
        st.metric("Respuestas totales", len(df))
        if not df.empty:
            st.dataframe(df.tail(10), use_container_width=True)
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
        df  = _sheet_to_df(FORMS_SHEET_ID, FORM1_TAB)
        df0 = _sheet_to_df(FORMS_SHEET_ID, FORM0_TAB) if FORM0_TAB else pd.DataFrame()
    except Exception as e:
        st.error(f"Error leyendo Form 1: {e}")
        return

    if df.empty:
        st.info("Sin respuestas aún.")
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
    Eres un asistente pedagógico en un taller sobre integridad de la información y alfabetización mediática. 
    El taller se desarrolla en el marco de cooperación entre el Gobierno de Zacatecas y el Programa de las Naciones Unidas para el Desarrollo (PNUD), 
    con el objetivo de fomentar una mayor conciencia entre la población joven en el estado para interactuar de manera crítica con las noticias 
    y fortalecer sus habilidades para desempeñar un papel activo en la prevención de la dispersión e impacto de la información errónea.

    Bajo el enfoque del Prebunking, el taller busca educar sobre los encuadres narrativos y los patrones comunes de información errónea, 
    con el fin de construir una resistencia cognitiva que prevenga la formación de creencias falsas antes de que las personas estén expuestas a contenidos engañosos.

    Crea una noticia falsa breve para WhatsApp (max 100 palabras) sobre un tema determinado por el tema dominante identificado ({dom}) en el formulario 1, usando un encuadre narrativo de Desconfianza y responsabilización de actores. Este encuadre tiene esta Busca socavar la confianza en las instituciones públicas, los procesos democráticos y la información objetiva. Cuestiona la legitimidad institucional o mediática, generando incertidumbre y cinismo ciudadano. Atribuye causas o soluciones a actores específicos (individuos, instituciones, grupos). 

    Elementos clave del mensaje whatsapp:
    Identificación de responsables.
    Lenguaje causal (“por”, “debido a”).
    Dudas sobre la imparcialidad institucional.
    Frases generalizadoras (“todos son corruptos”).
    Deslegitimación de fuentes oficiales.
    Emojis escépticos o de advertencia (🤔 😒 ⚠️ 👀).
    Signos de ironía o sospecha: “¿?”, “…” “—”.
    Mayúsculas parciales para tono emocional.

    Ejemplo de estilo (NO copiar literalmente):
    Oye, ya ni la hacen. A los vecinos de la 14 Sur les vaciaron la casa ayer a plena luz del día, y ni una patrulla llegó.  
    ¿De qué sirve reportar si al final protegen a los mismos? Todo es un teatro, solo salen en fotos cuando hay elecciones.
    """,

                # 🧩 Prompt 2 — Polarización social y exclusión
                f"""
    Eres un asistente pedagógico en un taller sobre integridad de la información y alfabetización mediática. 
    El taller se desarrolla en el marco de cooperación entre el Gobierno de Zacatecas y el Programa de las Naciones Unidas para el Desarrollo (PNUD), 
    con el objetivo de fomentar una mayor conciencia entre la población joven en el estado para interactuar de manera crítica con las noticias 
    y fortalecer sus habilidades para desempeñar un papel activo en la prevención de la dispersión e impacto de la información errónea.

    Bajo el enfoque del Prebunking, el taller busca educar sobre los encuadres narrativos y los patrones comunes de información errónea, 
    con el fin de construir una resistencia cognitiva que prevenga la formación de creencias falsas antes de que las personas estén expuestas a contenidos engañosos.

    Usa el tema dominante identificado ({dom}) y genera una noticia simulada (máx. 100 palabras)** 
    que parezca compartida en WhatsApp, aplicando el siguiente encuadre narrativo:  
    ENCUADRE: Polarización social y exclusión. Amplifica divisiones sociales y políticas mediante la apelación a emociones intensas (miedo, ira, resentimiento). Favorece el enfrentamiento simbólico y la construcción de “enemigos”. Atribuye la causa de los problemas a ciertos grupos o sectores sociales sin evidencia.

    Elementos clave del mensaje whatsapp:
    Lenguaje emocional o alarmista.
    Contraposición de grupos (ellos/nosotros).
    Reforzamiento de prejuicios o resentimientos.
    Búsqueda de validación emocional.
    Culpabilización generalizada (“los jóvenes”, “los migrantes”, etc.).
    Emojis de conflicto o ira (😡 😤 🔥 ⚔️ 💣 🚫).
    Mayúsculas parciales y exclamaciones para enfatizar antagonismo.

    Ejemplo de estilo (NO copiar literalmente):**
    ⚠️Vecino, abre los ojos ⚠️  
    Otra vez robaron una casa, y claro, fueron esos que no trabajan y viven de lo ajeno.  
    Nosotros cuidamos y ellos destruyen todo. Ya basta.
    """,

                # 🧩 Prompt 3 — Miedo y control
                f"""
    Eres un asistente pedagógico en un taller sobre integridad de la información y alfabetización mediática. 
    El taller se desarrolla en el marco de cooperación entre el Gobierno de Zacatecas y el Programa de las Naciones Unidas para el Desarrollo (PNUD), 
    con el objetivo de fomentar una mayor conciencia entre la población joven en el estado para interactuar de manera crítica con las noticias 
    y fortalecer sus habilidades para desempeñar un papel activo en la prevención de la dispersión e impacto de la información errónea.

    Bajo el enfoque del *Prebunking*, el taller busca educar sobre los encuadres narrativos y los patrones comunes de información errónea, 
    con el fin de construir una resistencia cognitiva que prevenga la formación de creencias falsas antes de que las personas estén expuestas a contenidos engañosos.

    Usa el tema dominante identificado ({dom}) y genera una noticia simulada (máx. 100 palabras)
    que parezca compartida en WhatsApp, aplicando el siguiente encuadre narrativo:  
    _No generes nada que pueda vulnerar o promover discriminación._

    Descripción de encuadre: Miedo y control
    Exagera el peligro o amenaza para justificar medidas extremas o de control. 
    Usa el miedo como herramienta de persuasión y parálisis.

    Elementos clave del encuadre:**
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
            if st.button("📊 Ir al análisis final del taller", type="primary", use_container_width=True):
                st.session_state.selected_page = "Análisis final del taller"
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
                st.metric("Respuestas finales", len(df2))
            except Exception as e:
                st.error(f"Error al contar respuestas finales: {e}")


def render_workshop_insights_page():
    """Dashboard + (debajo) síntesis automática con datos reales (Form 0/1/2/3/4 si están conectados)."""
    st.header("📊 Análisis final del taller")

    # --- Dashboard (estático) ---
    st.subheader("Dashboard (Looker Studio)")
    try:
        import streamlit.components.v1 as components
        components.html(
            """
           <iframe width="600" height="450" src="https://lookerstudio.google.com/embed/reporting/01c498c0-a278-49c3-9e00-48c160b622c2/page/p_o6qxvxbkxd" frameborder="0" style="border:0" allowfullscreen sandbox="allow-storage-access-by-user-activation allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe>
            """,
            height=640
        )
    except Exception:
        st.info("Agrega aquí el embed público de tu reporte de Looker Studio.")

    st.markdown("---")

    # --- Síntesis automática con IA (usa datos reales combinados) ---
    st.subheader("🧠 Interpretación automática de resultados")
    st.caption("Se combinan respuestas de Cuestionario 0/1/2/3/4 (si están configurados) y se genera una síntesis para facilitar el debate.")

    if st.button("🔎 Analizar respuestas y generar conclusiones + debate", type="primary", use_container_width=True):
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
            st.warning("No hay respuestas combinadas aún para analizar.")
            return

        # 2) Muestra un vistazo mínimo (opcional)
        with st.expander("👀 Muestra de datos combinados utilizados (primeras 10 filas)"):
            st.dataframe(df_all.head(10), use_container_width=True)

        # 3) Prepara muestra textual (capada) para el prompt
        sample_records = df_all.head(220).to_dict(orient="records")
        sample_txt = "\n".join([f"{i+1}) {row}" for i, row in enumerate(sample_records)])

        # 4) Prompt unificado (hallazgos + patrones + preguntas de debate)
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

    ### 1️⃣ Cruce de datos
    - Une respuestas con el mismo número de tarjeta (misma persona).
    - Asegúrate de mantener coherencia de género, emociones, encuadre percibido, y nivel de confianza.
    - Describe de manera general la coherencia y calidad del cruce de datos.

    ### 2️⃣ Análisis por encuadre narrativo
    Objetivo: observar cómo varían las emociones, la confianza y los componentes clave según el encuadre.
    Incluye en texto (no gráfico):
    - Principales diferencias de emociones por encuadre.
    - Diferencias en el nivel de confianza.
    - Elementos clave más frecuentes por encuadre.
    - Breve texto explicativo (3–5 líneas) que destaque hallazgos notables.
    - Formula 2–3 preguntas reflexivas (por ejemplo: ¿Por qué ciertos encuadres generan más desconfianza o empatía?).

    ### 3️⃣ Análisis por género–reacción emocional
    Objetivo: detectar diferencias de percepción y reacción emocional según género.
    Incluye:
    - Comparación de emociones predominantes por género.
    - Niveles de confianza promedio por género.
    - Texto explicativo (3–5 líneas) con diferencias relevantes.
    - 2 preguntas que fomenten reflexión (por ejemplo: ¿Cómo influye el género en la validación emocional o racional del mensaje?).

    ### 4️⃣ Análisis de casos emergentes
    Objetivo: sintetizar patrones emergentes y sesgos potenciales no abordados antes.
    Incluye:
    - Patrones significativos entre emociones, confianza, encuadre y género.
    - Identificación de posibles sesgos cognitivos o de percepción.
    - Breve texto explicativo (3–5 líneas).
    - 2 preguntas de debate.

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
