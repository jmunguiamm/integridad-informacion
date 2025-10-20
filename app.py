"""
Streamlit App - Information Integrity Workshop (full version)
Includes full Workshop pages and navigation via sidebar.
"""

import os
import json
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import streamlit as st

# Your custom sidebar module (must exist in ./components/sidebar.py)
from components.sidebar import render_sidebar


# ----------------------------- App Config & Style -----------------------------
st.set_page_config(
    page_title="Information Integrity Workshop",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Basic styles used by the app
st.markdown(
    """
    <style>
      .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Show path of the running file (useful when multiple copies exist)
st.sidebar.caption(f"Running file: {Path(__file__).resolve()}")


# ----------------------------- Defaults & Config ------------------------------
DEFAULT_WORKSHEET_TITLE = os.environ.get("WORKSHEET_TITLE", "Formulario 1")
# 👇 Change to your real column header in the sheet
DEFAULT_TEXT_COLUMN = os.environ.get("TEXT_COLUMN", "columna_x")

# --- Google Form URL (QR target) ---
def _get_google_form_url():
    # Prefer Streamlit secrets; fallback to env var
    try:
        url = st.secrets.get("GOOGLE_FORM_URL")
    except Exception:
        url = None
    if not url:
        url = os.environ.get("GOOGLE_FORM_URL")
    return (url or "").strip()

# --- Load config for Sheets + OpenAI (one Service Account for both) ---
DEFAULT_WORKSHEET_TITLE = os.environ.get("WORKSHEET_TITLE", "Formulario 1")
DEFAULT_TEXT_COLUMN = os.environ.get("TEXT_COLUMN", "columna_x")  # <— set to your real header

def _get_workshop_config():
    sheet_id = os.environ.get("SHEET_ID") or (st.secrets.get("SHEET_ID") if hasattr(st, "secrets") else None)
    openai_api_key = os.environ.get("OPENAI_API_KEY") or (st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None)
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT") or (st.secrets.get("GOOGLE_SERVICE_ACCOUNT") if hasattr(st, "secrets") else None)

    worksheet_title = os.environ.get("WORKSHEET_TITLE") or (st.secrets.get("WORKSHEET_TITLE", DEFAULT_WORKSHEET_TITLE) if hasattr(st, "secrets") else DEFAULT_WORKSHEET_TITLE)
    text_column = os.environ.get("TEXT_COLUMN") or (st.secrets.get("TEXT_COLUMN", DEFAULT_TEXT_COLUMN) if hasattr(st, "secrets") else DEFAULT_TEXT_COLUMN)

    contexto_general = os.environ.get("CONTEXTO_GENERAL") or (st.secrets.get("CONTEXTO_GENERAL", "") if hasattr(st, "secrets") else "")
    contexto_form0 = os.environ.get("CONTEXTO_FORM0") or (st.secrets.get("CONTEXTO_FORM0", "") if hasattr(st, "secrets") else "")

    return {
        "sheet_id": sheet_id,
        "openai_api_key": openai_api_key,
        "sa_json": sa_json,
        "worksheet_title": worksheet_title,
        "text_column": text_column,
        "contexto_general": (contexto_general or "").strip(),
        "contexto_form0": (contexto_form0 or "").strip(),
    }

# --- Cached loader for the Form responses sheet ---
@st.cache_data(ttl=30, show_spinner=False)
def _load_sheet_rows(sheet_id: str, worksheet_title: str, sa_json: str):
    from google.oauth2.service_account import Credentials
    import gspread, json as _json
    sa_info = _json.loads(sa_json)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(sheet_id).worksheet(worksheet_title)
    return ws.get_all_records()




# ----------------------------- Page Renderers ---------------------------------
def render_introduction_page():
    """Render the introduction page"""
    st.header("🏠 Welcome to the Information Integrity Workshop")

    st.markdown(
        """
This workshop is designed to help you understand and work with information integrity concepts.

### What you'll learn:
- How to identify narrative frames
- Data analysis techniques
- Form handling and validation
- AI-powered insights

### Getting Started:
1. Complete Form #1 to begin your journey
2. Explore narrative frames
3. Fill out Form #2 with your insights
4. Analyze your data
5. Ask AI for additional insights
"""
    )

    st.info("👆 Use the navigation menu on the left to explore different sections of the workshop.")

    # Centered CTA button (1/5 width, not full width)
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Start now"):
            st.session_state.selected_page = "Form #1"
            st.rerun()


def render_form1_page():
    """Form #1 page: QR code linking to the Google Form (no hard dependency on Sheet creds)."""
    import io, qrcode
    from PIL import Image
    from urllib.parse import urlparse

    st.header("📲 Form #1 — Escanea el QR para abrir el formulario")

    # 1) Read only the URL (required for this page)
    form_url = _get_google_form_url()

    # 2) Read sheet config OPTIONALLY (used for live counter if present)
    cfg = _get_workshop_config()  # expects keys but we'll treat them as optional here
    has_sheet = bool(cfg.get("sheet_id")) and bool(cfg.get("sa_json"))

    # ---- Health/status row (non-blocking)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Form URL", "OK" if form_url else "Falta")
    with c2:
        st.metric("Sheet ID", "OK" if has_sheet else "Opcional")
    with c3:
        st.metric("Worksheet", cfg.get("worksheet_title") or "—")

    # ---- If the URL is missing, guide and exit early
    if not form_url:
        st.error("Configura `GOOGLE_FORM_URL` en `.streamlit/secrets.toml` o variable de entorno.")
        st.info('Ejemplo: GOOGLE_FORM_URL = "https://docs.google.com/forms/d/XXXXXXXXXXXX/viewform"')
        return

    # ---- Tiny “link sanity” section: parse URL & show a Form ID-ish
    try:
        parsed = urlparse(form_url)
        path_bits = [p for p in parsed.path.split("/") if p]
        # typical: /forms/d/<FORM_ID>/viewform
        form_id = path_bits[path_bits.index("d") + 1] if "forms" in path_bits and "d" in path_bits else "desconocido"
        with st.expander("🔎 Verificar enlace del formulario", expanded=False):
            st.write("Dominio:", parsed.netloc)
            st.write("Ruta:", parsed.path)
            st.write("Form ID detectado:", form_id)
            st.code(form_url, language="text")
    except Exception:
        pass

    # ---- Build & show QR (the only real requirement on this page)
    @st.cache_data(show_spinner=False)
    def _qr_png(url: str, box_size: int = 14, border: int = 4) -> bytes:
        qr = qrcode.QRCode(
            version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size, border=border
        )
        qr.add_data(url); qr.make(fit=True)
        img: Image.Image = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return buf.getvalue()

    png_bytes = _qr_png(form_url)
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.image(png_bytes, caption="Escanéame para abrir el Formulario 1", use_container_width=True)
        st.link_button("📝 Abrir formulario", form_url, use_container_width=True)
        st.download_button("⬇️ Descargar QR (PNG)", data=png_bytes, file_name="form1_qr.png",
                           mime="image/png", use_container_width=True)

    # ---- Optional live counter from the linked Sheet (only if creds exist)
    st.markdown("---")
    st.subheader("📥 Respuestas recibidas (opcional)")
    if not has_sheet:
        st.info("Conecta el Google Sheet para mostrar el conteo en vivo (configura `SHEET_ID` y `GOOGLE_SERVICE_ACCOUNT`).")
        return

    # Only run if we have both sheet_id and service account
    colA, colB = st.columns([1, 3])
    with colA:
        if st.button("🔄 Refrescar"):
            _load_sheet_rows.clear()  # clear cache

    try:
        rows = _load_sheet_rows(cfg["sheet_id"], cfg["worksheet_title"], cfg["sa_json"])
        st.metric("Total de respuestas", len(rows))
        if rows:
            df_preview = pd.DataFrame(rows)
            st.dataframe(df_preview.head(10), use_container_width=True)
    except Exception as e:
        st.warning(f"No se pudo leer la hoja conectada (opcional): {e}")

def _list_reference_images(folder_name: str = "2. Imágenes de referencia"):
    """Return a list of image filenames in the given folder (if present)."""
    try:
        if not os.path.isdir(folder_name):
            return []
        files = sorted([f for f in os.listdir(folder_name) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])
        return files
    except Exception:
        return []

def render_narrative_frames_page():
    """Render narrative frames page with fixed Google Sheet defaults and one-click generation."""
    st.header("📈 Encuadres Narrativos")
    st.subheader("📝 Generar texto desde Google Sheet + OpenAI (valores por defecto)")

    cfg = _get_workshop_config()

    # Status summary
    cols = st.columns(4)
    with cols[0]:
        st.metric("Sheet ID", "OK" if cfg["sheet_id"] else "Falta")
    with cols[1]:
        st.metric("Worksheet", cfg["worksheet_title"] or "—")
    with cols[2]:
        st.metric("Columna", cfg["text_column"] or "—")
    with cols[3]:
        st.metric("OpenAI", "Conectado" if cfg["openai_api_key"] else "No")

    if st.button("Generar", type="primary", use_container_width=True):
        # Validate required config
        if not cfg["sheet_id"]:
            st.error("❌ Falta `SHEET_ID` en secrets o env.")
            return
        if not cfg["sa_json"]:
            st.error("❌ Falta `GOOGLE_SERVICE_ACCOUNT` (JSON) en secrets o env.")
            return
        if not cfg["openai_api_key"]:
            st.error("❌ Falta `OPENAI_API_KEY` en secrets o env.")
            return

        # Read Google Sheet
        try:
            from google.oauth2.service_account import Credentials
            import gspread

            sa_info = json.loads(cfg["sa_json"])
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
            gc = gspread.authorize(creds)

            sh = gc.open_by_key(cfg["sheet_id"])
            ws = sh.worksheet(cfg["worksheet_title"])
            rows = ws.get_all_records()
            df_sheet = pd.DataFrame(rows)
        except Exception as e:
            st.error(f"❌ Error accediendo a Google Sheet: {e}")
            return

        text_col = cfg["text_column"]
        if text_col not in df_sheet.columns:
            st.error(f"❌ La columna '{text_col}' no existe. Columnas: {list(df_sheet.columns)}")
            return

        # Collect non-empty responses
        respuestas = [str(t).strip() for t in df_sheet[text_col].astype(str) if str(t).strip()]
        if not respuestas:
            st.warning("No se encontraron respuestas en la columna configurada.")
            return

        # Build Spanish prompt (as requested)
        respuestas_bullets = "\n".join(f"- {r}" for r in respuestas)
        contexto_general_block = f"[contexto general]:\n{cfg['contexto_general']}\n\n" if cfg["contexto_general"] else ""
        contexto_form0_block = f"[formulario 0]:\n{cfg['contexto_form0']}\n\n" if cfg["contexto_form0"] else ""

        # --- Build “Referencias” for the model ---
        # 1) Frames catalogue (Referencia 1.1 - Encuadres narrativos)
        referencia_frames = [
            {
                "nombre": "Económico",
                "descripcion": "Énfasis en costos, empleo, mercados, inversión, impacto en bolsillos y productividad.",
                "tono": "pragmático, cifras claras, impacto en el día a día."
            },
            {
                "nombre": "Social",
                "descripcion": "Énfasis en comunidad, convivencia, bienestar, tejido social, familias y barrios.",
                "tono": "cercano, empático, centrado en personas."
            },
            {
                "nombre": "Político",
                "descripcion": "Énfasis en decisiones públicas, responsabilidad institucional, regulaciones y gobernanza.",
                "tono": "analítico, institucional, orientado a consecuencias de política."
            },
            {
                "nombre": "Ambiental",
                "descripcion": "Énfasis en clima, contaminación, resiliencia, territorio y futuro sostenible.",
                "tono": "preventivo, factual, con llamados a acción responsable."
            },
            {
                "nombre": "Tecnológico",
                "descripcion": "Énfasis en IA, ciberseguridad, adopción digital, riesgos y oportunidades tecnológicas.",
                "tono": "explicativo, precavido, con alfabetización digital."
            },
        ]
        ref_11 = "\n".join([f"- {f['nombre']}: {f['descripcion']} (tono: {f['tono']})" for f in referencia_frames])

        # 2) Ejemplos mínimos (Referencia 1.2 - Ejemplos de mensajes)
        ref_12 = (
            "Ejemplos de formato WhatsApp (máx. ~100 palabras):\n"
            "- «[Texto breve, directo, oraciones cortas]. [Dato/Hecho]. [Consejo/llamado].»\n"
            "- «[Mensaje conversacional con emoji moderado]. [Hecho verificable]. [Enlace/acción opcional].»"
        )

        # 3) Imágenes de referencia (si existen)
        imagenes = _list_reference_images("2. Imágenes de referencia")
        imagenes_block = " | ".join(imagenes) if imagenes else "No se detectaron archivos en ‘2. Imágenes de referencia’."

        # --- Build the final prompt (Spanish) ---
        user_prompt = (
            "Analiza las respuestas del [formulario 1] listadas abajo y determina el **tipo de evento dominante** "
            "(p. ej., crimen organizado, economía, IA, clima, política, salud, educación, migración, conflictos, etc.).\n\n"
            f"{contexto_general_block}{contexto_form0_block}"
            "En base al tipo de evento dominante, **escribe tres versiones de una misma noticia** con **encuadres distintos** "
            "explicados en [Referencia 1.1 - Encuadres narrativos]. Los mensajes deben estar redactados como **mensajes de WhatsApp** "
            "y **no sobrepasar las 100 palabras**. **Añade una imagen** de las que están en la carpeta [2. Imágenes de referencia], "
            "la que más se adapte a la noticia, y **presenta las noticias una a la vez**.\n\n"
            "Por ejemplo, si en el [formulario 1] la mayoría de las respuestas hablan del crimen organizado, redacta tres mensajes "
            "sobre una **misma noticia de crimen organizado**, cada uno con la tonalidad de un encuadre distinto, guiándote con "
            "[Referencia 1.2 - Ejemplos de mensajes].\n\n"
            "Limitantes: Este es un ejercicio educativo; **no generes nada que pueda vulnerar o promover discriminación**.\n\n"
            "=== [Referencia 1.1 - Encuadres narrativos] ===\n"
            f"{ref_11}\n\n"
            "=== [Referencia 1.2 - Ejemplos de mensajes] ===\n"
            f"{ref_12}\n\n"
            "=== [2. Imágenes de referencia] ===\n"
            f"{imagenes_block}\n\n"
            "=== [Respuestas del formulario 1] ===\n"
            f"{respuestas_bullets}\n\n"
            "=== Requisitos de salida ===\n"
            "Devuelve **exactamente tres** bloques, en este formato:\n"
            "1) Encuadre: <nombre>\n"
            "   Texto (WhatsApp, ≤100 palabras): <mensaje>\n"
            "   Imagen sugerida: <archivo exacto de [2. Imágenes de referencia] o «(no disponible)»>\n"
            "---\n"
            "2) Encuadre: <nombre>\n"
            "   Texto (WhatsApp, ≤100 palabras): <mensaje>\n"
            "   Imagen sugerida: <archivo>\n"
            "---\n"
            "3) Encuadre: <nombre>\n"
            "   Texto (WhatsApp, ≤100 palabras): <mensaje>\n"
            "   Imagen sugerida: <archivo>\n"
        )

        # Call OpenAI
        try:
            from openai import OpenAI

            client = OpenAI(api_key=cfg["openai_api_key"])
            with st.spinner("Generando análisis con OpenAI…"):
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.7,
                    max_tokens=900,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Eres un asistente experto en análisis narrativo e integridad de la información. "
                                "Estructura tus respuestas con claridad y viñetas."
                            ),
                        },
                        {"role": "user", "content": user_prompt},
                    ],
                )
            generated = resp.choices[0].message.content.strip()
            st.success("✅ Generado")
            with st.expander("🧠 Prompt enviado (ver)", expanded=False):
                st.code(user_prompt)
            st.markdown("### 📤 Respuesta generada")
            st.markdown(generated)
        except Exception as e:
            st.error(f"❌ Error llamando a OpenAI: {e}")
            return

        st.markdown("---")
        st.caption(f"Vista previa de las primeras 10 respuestas de «{text_col}».")
        st.dataframe(df_sheet[[text_col]].head(10), use_container_width=True)

    # Educational content & simple frame tool (kept)
    st.markdown(
        """
## Understanding Narrative Frames
Narrative frames are the underlying structures that shape how information is presented and understood.
They influence how we interpret data and make decisions.
        """
    )



def render_form2_page():
    """Render Form #2 page"""
    st.header("📝 Form #2")

    with st.form("form2"):
        st.subheader("Follow-up Assessment")

        if "form1_submissions" not in st.session_state or not st.session_state.form1_submissions:
            st.warning("⚠️ Please complete Form #1 first before filling out Form #2.")
            st.stop()

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name *", placeholder="Enter your name")
            email = st.text_input("Email *", placeholder="Enter your email")
        with col2:
            workshop_date = st.date_input("Workshop Date", value=date.today())
            session_id = st.text_input("Session ID", placeholder="Optional session identifier")

        st.subheader("Learning Assessment")
        learning_goals = st.multiselect(
            "What did you hope to learn? (Select all that apply)",
            ["Data Analysis", "Narrative Frames", "AI Tools", "Research Methods", "Policy Development"],
        )
        knowledge_gained = st.slider("How much new knowledge did you gain? (1-10)", min_value=1, max_value=10, value=5)
        practical_applications = st.text_area(
            "How do you plan to apply what you learned?", placeholder="Describe your planned applications...", height=100
        )

        st.subheader("Feedback")
        overall_rating = st.slider("Overall workshop rating (1-10)", min_value=1, max_value=10, value=5)
        improvements = st.text_area("Suggestions for improvement", placeholder="What could be improved?", height=80)

        submitted = st.form_submit_button("Submit Form #2", use_container_width=True)
        if submitted:
            if name and email:
                form_data = {
                    "name": name,
                    "email": email,
                    "workshop_date": workshop_date.isoformat(),
                    "session_id": session_id,
                    "learning_goals": learning_goals,
                    "knowledge_gained": knowledge_gained,
                    "practical_applications": practical_applications,
                    "overall_rating": overall_rating,
                    "improvements": improvements,
                    "timestamp": datetime.now().isoformat(),
                }
                st.success("✅ Form #2 submitted successfully!")
                if "form2_submissions" not in st.session_state:
                    st.session_state.form2_submissions = []
                st.session_state.form2_submissions.append(form_data)
                st.json(form_data)
            else:
                st.error("❌ Please fill in all required fields (*)")


def render_data_analysis_page():
    """Data analysis page with embedded dashboard"""
    st.header("📊 Data Analysis")

    # Embedded Looker Studio Dashboard
    st.subheader("📈 Interactive Dashboard")
    try:
        import streamlit.components.v1 as components

        components.html(
            """
            <iframe width="100%" height="600"
                    src="https://lookerstudio.google.com/embed/reporting/0e3af8a0-b777-4572-bc3c-04a5b5b6abc3/page/qgR"
                    frameborder="0" style="border:0" allowfullscreen
                    sandbox="allow-storage-access-by-user-activation allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe>
            """,
            height=620,
            scrolling=True,
        )
    except Exception:
        st.warning("⚠️ Dashboard no se puede mostrar en localhost. Ve a la versión en vivo.")
        st.markdown(
            """
            ### 📊 Accede al Dashboard
            [Abrir Dashboard de Looker Studio](https://lookerstudio.google.com/embed/reporting/0e3af8a0-b777-4572-bc3c-04a5b5b6abc3/page/qgR)
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # File upload section
    st.subheader("📁 Upload Your Data")
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ File uploaded successfully! Shape: {df.shape}")
            st.subheader("📋 Data Preview")
            st.dataframe(df.head(), use_container_width=True)
            st.subheader("📊 Basic Statistics")
            st.dataframe(df.describe(), use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
    else:
        st.info("👆 Please upload a CSV file to start analysis")


def render_ask_ai_page():
    """Render Ask AI page"""
    st.header("🤖 Ask AI")
    st.markdown(
        """
## AI-Powered Insights
Use this section to get AI-powered insights about your data and workshop experience.
"""
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # OpenAI integration (prefer env var; fall back to secrets if available)
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        try:
            openai_api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            openai_api_key = None

    # Status indicator
    status_col1, status_col2 = st.columns([1, 4])
    with status_col1:
        if openai_api_key:
            st.success("OpenAI: Connected")
        else:
            st.warning("OpenAI: Not detected")

    if prompt := st.chat_input("Ask AI about your data or workshop experience..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if not openai_api_key:
            with st.chat_message("assistant"):
                st.warning("OPENAI_API_KEY not set. Add it in Streamlit Secrets or env.")
                fallback = f"I understand you're asking about: '{prompt}'. This is a simulated AI response."
                st.markdown(fallback)
                st.session_state.messages.append({"role": "assistant", "content": fallback})
        else:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=openai_api_key)
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                    if m["role"] in ("user", "assistant")
                ]
                chat = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.4,
                    max_tokens=500,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful analyst assisting with information integrity workshops, data analysis, and narrative frames.",
                        }
                    ]
                    + history,
                )
                reply = chat.choices[0].message.content.strip()
                with st.chat_message("assistant"):
                    st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                with st.chat_message("assistant"):
                    err = f"Error calling OpenAI: {str(e)}"
                    st.error(err)
                    fallback = f"I understand you're asking about: '{prompt}'. This is a simulated AI response."
                    st.markdown(fallback)
                    st.session_state.messages.append({"role": "assistant", "content": fallback})


# ----------------------------------- Main -------------------------------------
def main():
    st.markdown('<h1 class="main-header">🧭 Information Integrity Workshop</h1>', unsafe_allow_html=True)

    page = render_sidebar()

    ROUTES = {
        "Introduction": render_introduction_page,
        "Form #1": render_form1_page,
        "Encuadres narrativos": render_narrative_frames_page,
        "Form #2": render_form2_page,
        "Data Analysis": render_data_analysis_page,
        "Ask AI": render_ask_ai_page,
    }

    ROUTES.get(page, lambda: st.info("Select a page from the sidebar."))()


if __name__ == "__main__":
    main()
