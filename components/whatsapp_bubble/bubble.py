"""WhatsApp-style message bubble component."""
import html
import re
import time
import os
import streamlit as st
import difflib


def find_image_by_prefix(prefix: str, folder="images"):
    """Busca una imagen local que empiece con el prefijo indicado (ej. 'taller1')."""
    valid_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    if not os.path.isdir(folder):
        return None
    for f in os.listdir(folder):
        if f.lower().startswith(prefix.lower()) and f.lower().endswith(valid_exts):
            return os.path.join(folder, f)
    return None


def find_matching_image(tags: list[str], folder="images"):
    """Busca en /images una imagen cuyo nombre contenga alguno de los tags indicados."""
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


def typing_then_bubble(
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
    # Animación 'escribiendo...' (si existe el GIF)
    if os.path.isfile(typing_path):
        holder = st.empty()
        with holder.container():
            st.image(typing_path, width=60)
            time.sleep(1.1)
        holder.empty()

    # Sanitizar texto y evitar inyección de HTML peligroso
    message_text = re.sub(r'<(script|iframe).*?>.*?</\1>', '', message_text, flags=re.I | re.S)
    embedded_html = ""
    html_match = re.search(r"(<div[^>]*?>[\s\S]*?</div>)", message_text, flags=re.I)
    if html_match:
        embedded_html = html_match.group(1)
        message_text = message_text.replace(embedded_html, "")

    safe_msg = html.escape(message_text, quote=False).replace("\n", "<br>")
    # Reconvert bold markers **text** to HTML strong
    safe_msg = re.sub(r"\*\*(.+?)\*\*", r"<strong>\\1</strong>", safe_msg)

    # Cajita del encuadre (si aplica)
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
 
    # Imagen tipo 'card' dentro del mensaje
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

    # Burbuja verde tipo WhatsApp
    html_block = f"""
    <div style="display:flex; justify-content:flex-end; margin:10px 0;">
    <div class="whatsapp-bubble">
        <div style="color:#777;font-size:12px;margin-bottom:4px;">↪︎↪︎ Reenviado muchas veces</div>
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
        .whatsapp-bubble {{
            background-color:#dcf8c6;
            border-radius:18px 18px 4px 18px;
            padding:12px 16px;
            width: min(430px, 85vw);
            font-family:'Roboto', system-ui, -apple-system, sans-serif;
            font-size:15px;
            color:#111;
            line-height:1.5;
            box-shadow:0 2px 4px rgba(0,0,0,0.2);
            animation: fadeIn 0.4s ease-out;
        }}
        .whatsapp-bubble img {{
            max-height:260px;
            width:100%;
            object-fit:cover;
        }}
        </style>
        """
    
    try:
        import streamlit.components.v1 as components
        estimated_height = 1150 if img_html else 700
        components.html(html_block, height=estimated_height)
    except Exception:
        st.markdown(html_block, unsafe_allow_html=True)

