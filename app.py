# app.py — Taller Integridad de la Información (versión con mejoras de navegación/QR/UX)

import os, json, re, time
from io import BytesIO
import pandas as pd
import streamlit as st

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

def _typing_then_bubble(message_text: str, image_path: str = None, typing_path: str = "images/typing.gif"):
    """
    Muestra un mensaje tipo WhatsApp enviado (alineado a la derecha).
    - Mantiene emojis, saltos de línea y formato limpio.
    - Evita mostrar etiquetas HTML crudas como <div> en el texto.
    - Estilo igual al mensaje reenviado en WhatsApp.
    """
    import html, re, time, os

    # --- Animación de "escribiendo..." (opcional) ---
    if os.path.isfile(typing_path):
        holder = st.empty()
        with holder.container():
            st.image(typing_path, width=60)
            time.sleep(1.1)
        holder.empty()

    # --- Sanitizar: eliminar tags peligrosos pero permitir estilo seguro ---
    safe_msg = re.sub(r'<(script|iframe).*?>.*?</\1>', '', message_text, flags=re.I | re.S)
    safe_msg = html.escape(safe_msg)  # escapa cualquier HTML para no mostrarlo literal
    safe_msg = safe_msg.replace("\n", "<br>")

    # --- Imagen opcional ---
    img_html = ""
    if image_path and os.path.isfile(image_path):
        img_html = f"<br><img src='{image_path}' style='width:100%;margin-top:8px;border-radius:12px;'/>"

     # --- Burbuja alineada a la derecha ---
    html_block = f"""
    <div style="display:flex; justify-content:flex-end; margin:10px 0;">
      <div style="
        background-color:#dcf8c6;
        border-radius:18px 18px 4px 18px;
        padding:12px 16px;
        max-width:75%;
        font-family:'Segoe UI', system-ui, -apple-system, sans-serif;
        font-size:15px;
        color:#111;
        line-height:1.5;
        box-shadow:0 2px 4px rgba(0,0,0,0.2);
        animation: fadeIn 0.4s ease-out;
      ">
        <div style="color:#777;font-size:12px;margin-bottom:4px;">↪︎↪︎ Reenviado muchas veces</div>
        {safe_msg}
        {img_html}
      </div>
    </div>
    <style>
      @keyframes fadeIn {{
        from {{opacity:0; transform:translateY(8px);}}
        to {{opacity:1; transform:translateY(0);}}
      }}
    </style>
    """
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
    """Introducción — siempre muestra texto, e intenta slider si hay imágenes."""
    import os
    st.header("🌎 Introducción al Taller de Integridad de la Información")

    # Carrusel simple si existen imágenes
    images = [
        "images/taller1.jpeg",
        "images/taller2.jpeg",
        "images/taller3.jpeg",
    ]
    valid_images = [p for p in images if os.path.isfile(p)]

    if valid_images:
        idx = st.slider("🖼️ Desliza para explorar", 0, len(valid_images) - 1, 0)
        st.image(valid_images[idx], use_container_width=True, caption="Imágenes del taller")
    else:
        st.info("ℹ️ No se encontraron imágenes aún. Puedes agregarlas en la carpeta `/images`.")

    # Texto principal (no se oculta aunque no haya imágenes)
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
    Actúa como un **analista de datos cualitativos experto en percepción pública y comunicación social**. 
    Tu tarea es interpretar información de talleres educativos sobre integridad de la información y desinformación.

    Dispones de dos fuentes de entrada:

    [Formulario 0 – Contexto de participantes]
    {context_text or "(vacío)"}

    [Formulario 1 – Percepciones de inseguridad y consumo informativo]
    {sample}

    ---

    🎯 **Objetivo del análisis:**
    Identifica el **tema o patrón dominante** en las respuestas del [Formulario 1], 
    enfocándote en los eventos o situaciones que generan **sensación de inseguridad** entre las personas participantes. 
    Integra también cualquier información contextual del [Formulario 0] que te ayude a entender mejor el entorno o perfil del grupo.
    No cuenta como tema dominantes la emocion generada o asociada, el tema es un fenomenon como "crisis climatica" o "bullying" y no las reacciones asociadas.
    🧩 **Tareas específicas:**
    1️⃣ Analiza ambas fuentes para determinar el **tema principal o evento recurrente** (ej. crimen organizado, violencia de género, pobreza, desconfianza institucional, etc.).  
    2️⃣ Describe las **emociones predominantes** (ej. miedo, enojo, desconfianza, resignación).  
    3️⃣ Resume los **patrones y causas** más mencionados, así como los **actores involucrados** (si aplica).  
    4️⃣ Sugiere hasta **10 palabras clave** relevantes que puedan usarse para una nube de palabras.  
    5️⃣ Incluye **2 respuestas representativas** que ilustren el patrón identificado.

    ---

    📄 **Formato de salida (JSON válido y estructurado):**
    {{
    "dominant_theme": "<tema o patrón dominante, frase corta>",
    "rationale": "<explicación breve en 2–4 oraciones, tono analítico y pedagógico>",
    "emotional_tone": "<emociones predominantes>",
    "top_keywords": ["<palabra1>", "<palabra2>", "<palabra3>", ...],
    "representative_answers": ["<cita1>", "<cita2>"]
    }}

    ---

    🧠 **Reglas:**
    - No inventes información que no esté en los datos.  
    - Mantén tono neutro, analítico y educativo.  
    - Usa español mexicano natural.  
    - No devuelvas texto adicional fuera del JSON.
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
    st.subheader("☁️ Nube de palabras — temas que causan inseguridad")

    try:
        # Ajusta aquí el nombre exacto de la columna donde está la descripción de la noticia
        target_col_candidates = [
            "Identifica una noticia que te haya provocado inseguridad o un sentir negativo este año y descríbela.",
            "¿Qué noticia te ha hecho sentir mayor inseguridad este año?",
        ]
        target_col = None
        for c in target_col_candidates:
            if c in df.columns:
                target_col = c
                break
        if target_col is None:
            st.warning("No encontré la columna de descripciones para la nube de palabras.")
        else:
            from wordcloud import WordCloud, STOPWORDS
            import matplotlib.pyplot as plt
            text_wc = " ".join(df[target_col].dropna().astype(str))
            wc = WordCloud(
                width=800,
                height=400,
                background_color="white",
                stopwords=STOPWORDS.union({"que","del","por","con","los","las","una","uno","como"}),
                collocations=False,
                regexp=r'\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{3,}\b',
            ).generate(text_wc)
            fig, ax = plt.subplots(figsize=(10, 5))
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
    # 🚀 Recuperar el tema ya calculado (sin volver a llamar a OpenAI)
    dom = st.session_state.get("dominant_theme")
    if not dom:
        st.warning("Primero identifica el tema dominante en ‘Análisis y tema dominante’.")
        if st.button("Ir a ‘Análisis y tema dominante’", use_container_width=True):
            st.session_state.selected_page = "Análisis y tema dominante (Form 1)"
            st.rerun()
        return
        
    # ÚNICO botón: generar 3 noticias y continuar a 'Noticias del taller'
    if st.button("🔎 Buscamos noticias online sobre este tema", type="primary", use_container_width=True):
        ref = """
1) Desconfianza y responsabilización de actores
2) Polarización social y exclusión
3) Miedo y control
4) Historias personales
"""
        prompt2 = f"""
Asume el rol de una persona que busca aumentar su influencia en redes sociales
mediante la creación de mensajes sobre temas de inseguridad, con alto impacto emocional.

Redacta exactamente 3 mensajes tipo WhatsApp (≤100 palabras), uno por encuadre narrativo.
Usa el tema dominante ya identificado: {dom}.

Cada mensaje debe:
- Tener tono y estilo del encuadre correspondiente.
- Emplear emojis y puntuación natural (como en chats reales).
- Incluir uno de los siguientes contextos, pero sin mencionarlos literalmente:
  * Reenviado varias veces
  * Compartido en chat vecinal
  * Difundido en grupo escolar
  * Mensaje anónimo reenviado
- No escribir literalmente frases como “Imagen sugerida” o “Este mensaje ha sido reenviado...”.
- Mantener lenguaje respetuoso, sin promover discriminación o violencia.

Formato de salida:
1) Encuadre: <nombre del encuadre>
   Mensaje: <texto estilo WhatsApp>
---
2) Encuadre: <nombre del encuadre>
   Mensaje: <texto estilo WhatsApp>
---
3) Encuadre: <nombre del encuadre>
   Mensaje: <texto estilo WhatsApp>

Referencias disponibles:
[1.1] Tipos de encuadres narrativos y sus tonos.
[1.2] Ejemplos de redacción breve en formato WhatsApp.

Escribe en español mexicano, con naturalidad y realismo.
"""
        try:
            client = _openai_client()
            with st.spinner("🔎 📑 Buscando las noticias…"):
                resp2 = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.55,
                    messages=[
                        {"role":"system","content":"Asistente educativo en narrativas."},
                        {"role":"user","content":prompt2},
                    ],
                )
            gen_text = resp2.choices[0].message.content.strip()
            st.session_state.current_page = "Noticias del taller"
            st.session_state.selected_page = "Noticias del taller"
            st.session_state.news_index = 0
            st.session_state.generated_news_raw = gen_text
            st.rerun()
        except Exception as e:
            st.error(f"Error generando noticias: {e}")


def _parse_news_blocks(raw: str):
    """Extrae y limpia hasta 3 bloques de noticias desde el texto generado por OpenAI."""
    if not isinstance(raw, str) or not raw.strip():
        return []

    # Divide por líneas de separación (--- o saltos dobles)
    parts = re.split(r'^\s*[-—]{3,}\s*$|\n{2,}', raw, flags=re.MULTILINE)
    cleaned = []

    for p in parts:
        t = (p or "").strip()
        if not t or re.fullmatch(r'[-—\s]+', t):
            continue
        # Borra líneas "Imagen sugerida ..." si el modelo las puso
        t = re.sub(r'(?i)^\s*imagen\s+(sugerida|de\s+referencia)\s*:\s*.*$', '', t, flags=re.MULTILINE)
        # Si existe etiqueta Mensaje:, extrae solo el contenido tras ella
        m = re.search(r'(?i)\bmensaje\s*:\s*(.+)', t, re.DOTALL)
        cleaned.append(m.group(1).strip() if m else t)

    # Limita a 3 noticias
    return cleaned[:3]


def render_news_flow_page():
    """Muestra 3 noticias tipo WhatsApp, con navegación y botón final a Análisis."""
    st.header("💬 Noticias del taller")
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
    message = stories[idx]
    test_image = "images/test_news.jpg" if os.path.isfile("images/test_news.jpg") else None
    _typing_then_bubble(message, image_path=test_image)

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


# ---------- ROUTER (etiquetas/orden solicitados) ----------
ROUTES = {
    "Cuestionario para formador": render_setup_trainer_page,      # antes: Setup sesión (formador)
    "Introducción al taller": render_introduction_page,           # antes: Introducción
    "Cuestionario 1": render_form1_page,                          # antes: Form #1
    "Análisis y tema dominante": render_analysis_trends_page,     # antes: Análisis y tendencias (Form 1)
    "Cuestionario 2": render_form2_page,                          # NUEVA PÁGINA con QR
    "Noticias del taller": render_news_flow_page,                 # antes: Noticias
    "Análisis final del taller": render_workshop_insights_page,   # antes: Análisis del taller     # opcional
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
