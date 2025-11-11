"""News generation service with different narrative frames."""
import re
from datetime import datetime

import streamlit as st

from .ai_analysis import get_openai_client
from components.image_repo import select_image_for_story


def generate_news(dominant_theme: str, neutral_story: str | None = None):
    """
    Genera tres versiones de la noticia neutral aplicando diferentes encuadres narrativos.

    Args:
        dominant_theme: Tema principal identificado en el taller.
        neutral_story: Noticia neutral base en formato Markdown/texto.

    Returns:
        list[dict]: [{"encuadre": str, "text": str}, ...]
    """
    client = get_openai_client()

    base_story = (neutral_story or "(Sin noticia neutral generada; describe de forma objetiva el tema dominante)").strip()

    prompts = [
        (
            "Desconfianza y responsabilización de actores",
            f"""
Contexto:
Esta es la noticia neutral que debes reinterpretar:
---
{base_story}
---

Rol:
Redacta esta misma noticia como una persona que busca sembrar desconfianza y responsabilizar a actores específicos.

Instrucciones:
- Mantén los hechos principales sin inventar datos nuevos.
- Reescribe la narrativa enfatizando la desconfianza institucional y señalando culpables explícitos.
- Maximo 220 palabras. Evita listas.
- Usa estos elementos del encuadre:
Atribuye la responsabilidad a ciertos actores, culpando y/o exigiendo.
Usa un lenguaje causal ("por", "debido a", "por culpa de").
Orienta desconfianza institucional.
Puede reforzar la rendición de cuentas o culpabilización
Duda sobre la imparcialidad o transparencia institucional.
Utiliza un lenguaje de reclamo generalizado ("todos son corruptos", "nunca dicen la verdad", "siempre han sido ladrones", "siempre lucran con nuestra confianza").
Usa referencias a traición, manipulación o colusión.
Suele deslegitimar fuentes oficiales o periodísticas, justificando que estas están cooptadas y manipuladas.
Suele tener presencia de emojis con expresión escéptica o de advertencia (🤔 😒 ⚠️ 👀).
Usa signos como "¿?", "…" y "—" para enfatizar la sospecha o ironía.
Incorporar mayúsculas parciales o exclamaciones para representar tono de hartazgo y desconfianza.
""",
        ),
        (
            "Polarización social y exclusión",
            f"""
Contexto:
Esta es la noticia neutral que debes reinterpretar:
---
{base_story}
---

Rol:
Redacta esta noticia con un encuadre que polariza a dos grupos sociales, fomentando la exclusión del "otro".

Instrucciones:
- Conserva los hechos clave sin inventar nueva información.
- Usa lenguaje que contraste claramente “nosotros vs. ellos”, apelando a emociones intensas.
- Maximo 220 palabras. Evita listas.
- Usa estos elementos del encuadre:
Usa un lenguaje emocional y alarmista.
Acentúa la contraposición de grupos usando palabras como “ellos” vs ”nosotros”.
Refuerza prejuicios y resentimientos.
Busca una validación emocional más que racional.
Hace uso de la culpabilización generalizada (“los migrantes”, “los jóvenes”, “las mujeres”).
Hay una ausencia de pluralidad de voces, sólo se cuenta un lado de la historia.
Usa un lenguaje discriminatorio o juicios sin pruebas.
Contiene asociaciones repetitivas entre grupo y problema.
Usa signos de exclamación, mayúsculas parciales, puntos suspensivos (…) y emojis de conflicto (😡 😤 🔥 ⚔️ 💣 🚫) para evidenciar la carga emocional y el antagonismo.
""",
        ),
        (
            "Miedo y control",
            f"""
Contexto:
Esta es la noticia neutral que debes reinterpretar:
---
{base_story}
---

Rol:
Reescribe la noticia utilizando un encuadre que enfatice el miedo y la necesidad de control/medidas extremas.

Instrucciones:
- Mantén los hechos originales, pero magnifica las consecuencias negativas y la sensación de amenaza.
- Sugiere medidas de control o vigilancia como respuesta.
- Maximos 220 palabras. Evita listas.
- Usa estos elementos del encuadre:
usa un lenguaje apocalíptico de urgencia y totalizador.
Imágenes impactantes o repetición de violencia.
Ausencia de datos verificables.
Justificación del control o vigilancia.
Uso exagerado de signos de puntuación para remarcar desesperación o urgencia. (‼️, ❗❗❗, …, ???, !!! →)
Emojis que usa: 😱 😨 😰 💀 🔥 ⚠️ 🚨 💣 👁️‍🗨️ 🔒 📹 🔔 🧟
Usa mayúsculas parciales para enfatizar un tono de alarma.
Limita la libertad través de sugerencias y recomendaciones usando el peligro como justificación 
Usa la repetición de palabras o frases: “Ya es tarde… demasiado tarde… 😨”
""",
        ),
    ]

    generated_blocks = []
    used_images: set[str] = set()
    for idx, (encuadre, prompt_text) in enumerate(prompts, start=1):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.55,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en narrativa persuasiva. Adaptas historias manteniendo los hechos, cambiando sólo el enfoque emocional."
                },
                {"role": "user", "content": prompt_text},
            ],
        )
        result = resp.choices[0].message.content.strip()
        # Limpieza básica para eliminar encabezados tipo "1." o prefijos escapados
        result = re.sub(r"^(?:\s|\\|/|[\d.\-)])+","", result)
        debug_flag = bool(st.session_state.get("debug_image_scoring"))
        image_path = select_image_for_story(
            dominant_theme,
            result,
            encuadre,
            exclude_paths=used_images,
            debug=debug_flag,
        )
        if image_path:
            used_images.add(image_path)

        generated_blocks.append({"encuadre": encuadre, "text": result, "image": image_path})

    log_payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": "Noticias con encuadres generadas.",
        "level": "success",
        "context": "Noticias del taller",
        "data": {"encuadres": [block.get("encuadre") for block in generated_blocks]},
    }
    existing = st.session_state.setdefault("workflow_debug_messages", [])
    existing.append(log_payload)
    st.session_state["workflow_debug_messages"] = existing[-200:]

    return generated_blocks

