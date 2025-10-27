# app.py — Taller Integridad de la Información (versión limpia)

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

def _read_secrets(key: str, default: str = ""):
    """Lee secrets desde entorno o Streamlit Cloud."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

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

def _typing_then_bubble(message_text: str, typing_path="images/typing.gif"):
    """Simula el envío de un mensaje tipo WhatsApp con estilo realista mejorado."""
    import datetime, time, os

    if os.path.isfile(typing_path):
        holder = st.empty()
        with holder.container():
            st.image(typing_path, width=70)
            time.sleep(1.3)
        holder.empty()

    now = datetime.datetime.now().strftime("%-I:%M %p")

    st.markdown(
        f"""
        <div style="
            display: flex;
            justify-content: flex-end;
            margin: 10px 0;
            font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
        ">
            <div style="
                background-color: #DCF8C6;
                border-radius: 14px;
                padding: 10px 14px 6px 14px;
                max-width: 75%;
                box-shadow: 0 1px 2px rgba(0,0,0,0.2);
                position: relative;
                word-wrap: break-word;
                line-height: 1.45;
            ">
                <div style="
                    font-size: 12.5px;
                    color: #667781;
                    margin-bottom: 5px;
                    display: flex;
                    align-items: center;
                ">
                    <span style="font-size: 13px; margin-right: 5px;">↪↪</span> Forwarded many times
                </div>
                <div style="
                    font-size: 15.5px;
                    color: #111;
                    text-align: left;
                    margin-bottom: 6px;
                    white-space: pre-wrap;
                ">
                    {message_text}
                </div>
                <div style="
                    font-size: 11px;
                    color: #667781;
                    text-align: right;
                ">
                    {now}&nbsp;<span style="color:#34B7F1;">✓✓</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _qr_image_for(url: str):
    """Genera QR PNG de un link."""
    try:
        import qrcode
        buf = BytesIO()
        qrcode.make(url).save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None

def _openai_client():
    """Devuelve cliente OpenAI."""
    from openai import OpenAI
    api_key = _read_secrets("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY.")
    return OpenAI(api_key=api_key)

def _load_joined_responses():
    forms = []
    for form in [("FORM0_SHEET_ID","FORM0_TAB"),
                 ("FORM1_SHEET_ID","FORM1_TAB"),
                 ("FORM2_SHEET_ID","FORM2_TAB")]:
        sid = _read_secrets(form[0],"")
        tab = _read_secrets(form[1],"")
        if not sid or not tab: continue
        try:
            df = _sheet_to_df(sid, tab)
            df.columns = [c.strip() for c in df.columns]
            df["source_form"] = form[0][:6]  # F0/F1/F2
            forms.append(df)
        except Exception as e:
            st.warning(f"No pude leer {form}: {e}")
    if not forms:
        return pd.DataFrame()
    df_all = pd.concat(forms, ignore_index=True)
    # unify join key
    key_candidates = [c for c in df_all.columns if "tarjeta" in c.lower()]
    if key_candidates:
        key = key_candidates[0]
        df_all[key] = df_all[key].astype(str).str.strip()
    else:
        key = None
    return df_all, key

def _load_joined_responses():
    """Reads Form0, Form1, Form2 and joins on 'número de tarjeta'."""
    forms = []
    for form in [("FORM0_SHEET_ID","FORM0_TAB"),
                 ("FORM1_SHEET_ID","FORM1_TAB"),
                 ("FORM2_SHEET_ID","FORM2_TAB")]:
        sid = _read_secrets(form[0],"")
        tab = _read_secrets(form[1],"")
        if not sid or not tab: continue
        try:
            df = _sheet_to_df(sid, tab)
            df.columns = [c.strip() for c in df.columns]
            df["source_form"] = form[0][:6]  # F0/F1/F2
            forms.append(df)
        except Exception as e:
            st.warning(f"No pude leer {form}: {e}")
    if not forms:
        return pd.DataFrame()
    df_all = pd.concat(forms, ignore_index=True)
    # unify join key
    key_candidates = [c for c in df_all.columns if "tarjeta" in c.lower()]
    if key_candidates:
        key = key_candidates[0]
        df_all[key] = df_all[key].astype(str).str.strip()
    else:
        key = None
    return df_all, key

def _analyze_reactions(df_all, key):
    """Analyze reactions and patterns across Form 0–2."""
    sample = df_all.head(200).to_dict(orient="records")
    sample_txt = "\n".join([f"{i+1}) {row}" for i, row in enumerate(sample)])

    prompt = f"""
Eres un analista de talleres educativos sobre desinformación.

Tienes datos combinados de tres formularios:
- [Form 0] Contexto del grupo y del docente.
- [Form 1] Percepciones de inseguridad y emociones previas.
- [Form 2] Reacciones ante las noticias con diferentes encuadres narrativos.

Cada fila está vinculada por un número de tarjeta que representa a una persona.

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
    FORM0_SHEET_ID = _read_secrets("FORM0_SHEET_ID", "")
    FORM0_TAB = _read_secrets("FORM0_TAB", "")
    SA = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")

    cols = st.columns(4)
    with cols[0]: st.metric("Form 0 URL", "OK" if FORM0_URL else "Falta")
    with cols[1]: st.metric("Sheet ID", "OK" if FORM0_SHEET_ID else "Falta")
    with cols[2]: st.metric("Worksheet", FORM0_TAB or "—")
    with cols[3]: st.metric("ServiceAccount", "OK" if SA else "Falta")

    if FORM0_URL:
        qr = _qr_image_for(FORM0_URL)
        if qr:
            st.image(qr, caption="Escanea para abrir Form 0", width=220)
        st.link_button("📝 Abrir Form 0", FORM0_URL, use_container_width=True)

def render_introduction_page():
    st.header("🏠 Introducción")
    st.markdown(
        """
**Objetivo del taller**  
Explorar cómo distintas **narrativas** cambian la **percepción** de una misma noticia y cómo responder de forma crítica.

**Flujo general**  
1️⃣ Cuestionario – percepciones ante noticias.  
2️⃣ Análisis – identificar tema dominante en la sala.  
3️⃣ Noticias – reacciones y sensaciones tras leer noticias en vivo.  
4️⃣ Cuestionario – reacciones por noticia.  
5️⃣ Análisis final – dashboard y conclusiones.
"""
    )

def render_form1_page():
    """Formulario 1 – QR y conteo."""
    st.header("📋 Form #1 (audiencia)")
    FORM1_URL = _read_secrets("FORM1_URL", "")
    FORM1_SHEET_ID = _read_secrets("FORM1_SHEET_ID", "")
    FORM1_TAB = _read_secrets("FORM1_TAB", "")
    SA = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")

    if FORM1_URL:
        qr = _qr_image_for(FORM1_URL)
        st.image(qr, caption="Escanea para abrir Form 1", width=220)
        st.link_button("📝 Abrir Form 1", FORM1_URL, use_container_width=True)

    _autorefresh_toggle("form1_autorefresh")

    if not (FORM1_SHEET_ID and FORM1_TAB and SA):
        st.info("Configura credenciales para ver conteo.")
        return

    try:
        df = _sheet_to_df(FORM1_SHEET_ID, FORM1_TAB)
        st.metric("Respuestas totales", len(df))
        if not df.empty:
            st.dataframe(df.tail(10), use_container_width=True)
    except Exception as e:
        st.error(f"Error leyendo Form 1: {e}")

def render_analysis_trends_page():
    """Analiza Form 1 completo → tema dominante → genera 3 noticias."""
    st.header("📈 Análisis y tendencias (Form 1)")

    FORM1_SHEET_ID = _read_secrets("FORM1_SHEET_ID", "")
    FORM1_TAB = _read_secrets("FORM1_TAB", "")
    SA = _read_secrets("GOOGLE_SERVICE_ACCOUNT", "")
    OPENAI = _read_secrets("OPENAI_API_KEY", "")
    if not (FORM1_SHEET_ID and FORM1_TAB and SA and OPENAI):
        st.error("Faltan credenciales (Form 1/OpenAI/SA).")
        return

    try:
        df = _sheet_to_df(FORM1_SHEET_ID, FORM1_TAB)
    except Exception as e:
        st.error(f"Error leyendo Form 1: {e}")
        return
    if df.empty:
        st.info("Sin respuestas aún.")
        return

    # ---- OpenAI: análisis de tema dominante + WordCloud ----

    from wordcloud import WordCloud, STOPWORDS
    import matplotlib.pyplot as plt

    # --- Form 0 (contexto general) ---
    try:
        FORM0_SHEET_ID = _read_secrets("FORM0_SHEET_ID", "")
        FORM0_TAB = _read_secrets("FORM0_TAB", "")
        df0 = _sheet_to_df(FORM0_SHEET_ID, FORM0_TAB) if (FORM0_SHEET_ID and FORM0_TAB) else pd.DataFrame()
    except Exception:
        df0 = pd.DataFrame()

    context_text = ""
    if not df0.empty:
        context_text = "\n".join([
            f"{i+1}) " + " | ".join([f"{k}={v}" for k, v in row.items()])
            for i, row in enumerate(df0.to_dict('records')[:30])
        ])

    # --- Form 1 (respuestas principales) ---
    sample = "\n".join([
        f"{i+1}) " + " | ".join([f"{k}={v}" for k, v in row.items()])
        for i, row in enumerate(df.to_dict('records')[:100])
    ])

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

    # ---- Mostrar resultados ----
    dom = data.get("dominant_theme", "N/A")
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

    text = " ".join(df["Identifica una noticia que te haya provocado inseguridad o un sentir negativo este año y descríbela."].dropna().astype(str))
    wc = WordCloud(
        width=800,
        height=400,
        background_color="white",
        stopwords=STOPWORDS.union({"que", "del", "por", "con", "los", "las", "una", "uno", "como"}),
        collocations=False,
        regexp=r'\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{3,}\b',  # ✅ only words 3+ letters
        ).generate(text)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.pyplot(fig)



    # ---- Generar noticias ----
    if st.button("📰 Generar 3 noticias y continuar", type="primary"):
        ref = """
1) Desconfianza y responsabilización de actores
2) Polarización social y exclusión
3) Miedo y control
4) Historias personales
"""
        prompt2 = f"""
Actúa como un **asistente pedagógico** dentro de un taller sobre integridad de la información 
organizado por el Gobierno de Zacatecas y el Programa de las Naciones Unidas para el Desarrollo (PNUD).

🎭 **Rol simulado:**
Adopta el rol de una persona que busca ganar influencia en redes sociales 
mediante la creación de mensajes y “noticias” sobre temas de inseguridad.
⚠️ Es un rol controlado y educativo: **no generes desinformación real**.
Tu objetivo es ilustrar cómo los diferentes encuadres narrativos modifican la percepción de un mismo hecho.

---

📚 **Contexto:**
Usa la información del **tema dominante previamente identificado** (`{dom}`), 
que proviene del análisis de las respuestas del [Formulario 1] 
(sobre las noticias que generaron sensación de inseguridad entre las personas participantes).  
No repitas el análisis: usa el resultado del modelo anterior como referencia base.

---

🧩 **Tarea de redacción:**
Redacta **exactamente tres mensajes tipo WhatsApp (≤100 palabras cada uno)**, 
cada uno representando **un encuadre narrativo distinto** de la lista [Referencia 1.1 – Tipos de encuadres narrativos].  
Integra un elemento de difusión o contexto social en cada mensaje, eligiendo uno de los siguientes:
- “Reenviado varias veces”
- “Compartido en chat vecinal”
- “Difundido en grupos de la escuela”
- “Mensaje compartido por un número anónimo”

Además, **añade una imagen sugerida** tomada de la carpeta [2. Imágenes de referencia].

---

🧱 **Formato de salida:**
1) Encuadre: <nombre del encuadre>
   Mensaje: <texto estilo WhatsApp, ≤100 palabras, tono y recursos coherentes con el encuadre>
   Imagen sugerida: <nombre o descripción breve>
---
2) Encuadre: <nombre del encuadre>
   Mensaje: <texto estilo WhatsApp, ≤100 palabras>
   Imagen sugerida: <nombre o descripción breve>
---
3) Encuadre: <nombre del encuadre>
   Mensaje: <texto estilo WhatsApp, ≤100 palabras>
   Imagen sugerida: <nombre o descripción breve>

---

📖 **Referencias disponibles:**
[Referencia 1.1 – Tipos de encuadres narrativos]: 
- Desconfianza y responsabilización de actores  
- Polarización social y exclusión  
- Miedo y control  
- Historias personales  

[Referencia 1.2 – Ejemplos de mensajes]: 
Ejemplos breves de redacción tipo WhatsApp, tono conversacional y verosímil.

---

🧠 **Reglas:**
- Mantén el tono y recursos propios de cada encuadre (uso moderado de emojis, signos, tono coloquial).  
- No generes nada que pueda vulnerar, estigmatizar o promover discriminación.  
- Evita sensacionalismo, lenguaje violento o desinformación.  
- Usa español mexicano natural y frases cortas típicas de chats.  
- No incluyas explicaciones ni comentarios fuera de los mensajes.
"""
        try:
            with st.spinner("✍️ Generando..."):
                resp2 = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.55,
                    messages=[{"role":"system","content":"Asistente educativo en narrativas."},
                              {"role":"user","content":prompt2}],
                )
            gen_text = resp2.choices[0].message.content.strip()
            st.session_state.generated_news_raw = gen_text
            st.session_state.news_index = 0
            st.session_state.selected_page = "Noticias"
            st.rerun()
        except Exception as e:
            st.error(f"Error generando noticias: {e}")

def _parse_news_blocks(raw: str):
    """Filtra noticias válidas (máx 3)."""
    parts = re.split(r'^\s*[-—]{3,}\s*$|\n{2,}', raw, flags=re.MULTILINE)
    cleaned = [p.strip() for p in parts if p.strip() and not re.fullmatch(r'[-—\s]+', p)]
    # preferimos los que contienen “Mensaje:”
    msgs = [p for p in cleaned if re.search(r"(?i)mensaje\s*:", p)]
    return msgs[:3] if msgs else cleaned[:3]

def render_news_flow_page():
    """Muestra 3 noticias tipo WhatsApp."""
    st.header("💬 Noticias generadas")
    raw = st.session_state.get("generated_news_raw")
    if not raw:
        st.info("Genera primero desde 'Análisis y tendencias'.")
        return

    stories = _parse_news_blocks(raw)
    idx = int(st.session_state.get("news_index", 0))
    if idx >= len(stories): idx = 0

    def extract(block): 
        m = re.search(r"(?i)mensaje\s*:\s*(.+)", block, re.DOTALL)
        return m.group(1).strip() if m else block

    msg = extract(stories[idx])
    _typing_then_bubble(msg, typing_path="images/typing.gif")

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
            if st.button("📊 Ir al análisis del taller", type="primary", use_container_width=True):
                st.session_state.selected_page = "Análisis del taller"
                st.rerun()

def render_workshop_insights_page():
    """Dashboard + conclusiones."""
    st.header("📊 Análisis del taller")
    st.subheader("Dashboard (Looker Studio)")
    try:
        import streamlit.components.v1 as components
        components.html(
            """
            <iframe width="100%" height="620"
                src="https://lookerstudio.google.com/embed/reporting/YOUR-REPORT-ID/page/xyz"
                frameborder="0" style="border:0" allowfullscreen></iframe>
            """, height=640)
    except Exception:
        st.info("Agrega embed de Looker Studio aquí.")

    st.markdown("---")
    if st.button("🧠 Generar conclusiones y debate", type="primary"):
        try:
            client = _openai_client()
            prompt = """
Resume los hallazgos de los formularios del taller en:
- 3–5 hallazgos clave
- 2 recomendaciones prácticas
- 1 pregunta abierta para debate grupal
"""
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.4,
                messages=[{"role":"system","content":"Facilitador pedagógico."},
                          {"role":"user","content":prompt}],
            )
            st.markdown(resp.choices[0].message.content.strip())
        except Exception as e:
            st.error(f"Error generando conclusiones: {e}")

def render_reaction_analysis_page():
    st.header("🧭 Análisis de reacciones (Form 2)")
    df_all, key = _load_joined_responses()
    if df_all.empty:
        st.warning("No hay respuestas combinadas aún.")
        return
    st.dataframe(df_all.head(10), use_container_width=True)
    if st.button("🧠 Analizar reacciones y patrones", type="primary"):
        report = _analyze_reactions(df_all, key)
        st.markdown(report)

# ---------- ROUTER ----------
ROUTES = {
    "Setup sesión (formador)": render_setup_trainer_page,
    "Introducción": render_introduction_page,
    "Form #1": render_form1_page,
    "Análisis y tendencias (Form 1)": render_analysis_trends_page,
    "Noticias": render_news_flow_page,
    "Análisis del taller": render_workshop_insights_page,
    "Análisis de reacciones": render_reaction_analysis_page,
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