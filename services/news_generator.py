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
Tienes un rol simulado de ser una persona que busca socavar la confianza en las instituciones públicas, los procesos democráticos y la información objetiva.

Instrucciones:
- Redacta un mensaje simulando una noticia compartida en WhatsApp.
- Usa los hechos y datos referidos a la noticia ética que se redactó con el tema dominante identificado en el formulario 1 ({dominant_theme}) referente a los eventos que más han generado sensación de inseguridad y las emociones asociadas.
- Debe tener entre 180 y 220 palabras (mínimo 180).
- Aplica el encuadre narrativo de desconfianza y responsabilización de actores.

Descripción del encuadre de desconfianza y responsabilización de actores:
-Cuestiona la legitimidad institucional o mediática, generando incertidumbre y cinismo ciudadano.
-Atribuye causas o soluciones a actores específicos (individuos, instituciones, grupos). Influye en la percepción pública sobre quién tiene la culpa o el mérito. 

Elementos del encuadre:
-Atribuye la responsabilidad a ciertos actores, culpando y/o exigiendo.
-Usa un lenguaje causal ("por", "debido a", "por culpa de").
-Orienta desconfianza institucional.
-Puede reforzar la rendición de cuentas o culpabilización
-Duda sobre la imparcialidad o transparencia institucional.
-Utiliza un lenguaje de reclamo generalizado ("todos son corruptos", "nunca dicen la verdad", "siempre han sido ladrones", "siempre lucran con nuestra confianza").
-Usa referencias a traición, manipulación o colusión.
-Suele deslegitimar fuentes oficiales o periodísticas, justificando que estas están cooptadas y manipuladas.
-Suele tener presencia de emojis con expresión escéptica o de advertencia (🤔 😒 ⚠️ 👀).
-Usa signos como "¿?", "…" y "—" para enfatizar la sospecha o ironía.
-Incorporar mayúsculas parciales o exclamaciones para representar tono de hartazgo y desconfianza.

Limitaciones:
-No generes nada que pueda vulnerar o promover discriminación.
-Evita reproducir estigmas, lenguaje violento o discriminatorio.
Limítate a que el mensaje se enmarque en el tono descrito en el encuadre, no cierres con un mensaje optimista o feliz.
No redactes nada que aluda a la polarización social y exclusión o al miedo y el control

Ejemplos de noticias con Encuadre de Desconfianza Institucional:
- Ya ni la hacen. A vecinos de la 14 Sur les vaciaron la casa ayer a plena luz del día… ¡Y NI UNA PATRULLA LLEGÓ!. Dicen que los ladrones ya habían sido denunciados, pero la policía “no tenía pruebas”🤔. ¿De qué sirve reportar si al final son los mismos policías los que les dan el pitazo para que roben?😒 Todo es un teatro, por culpa de la autoridad los ciudadanos terminamos despojados de nuestro patrimonio y con miedo a las represalias si denunciamos. Es mentira que los índices delictivos han bajado, ⚠️ no creas en fuentes oficiales, mantente vigilante y no confíes ni en la autoridad ⚠️ .
⚠️ Entérate ⚠️. 
- Detuvieron a unos del cártel en la carretera, pero al día siguiente… ¡ya estaban libres! Siempre es igual, los gobernantes dicen que combaten el narco, pero seguro alguien les pagó y los dejaron libres. Las autoridades solo hacen operativos para la foto 😒, mientras los verdaderos jefes siguen mandando. ¿Y así quieren que sigamos creyendo en ellos? Ya no vamos a confiar en los traidores, siempre lucran con nuestra confianza, entregan a los buenos y consienten a los malos. Debemos buscar un cambio, ya no confiar en los de siempre, que vean que ellos no son los que mandan, el pueblo manda y podemos quitar a cualquier autoridad que no atienda lo que el pueblo exige. 
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
Tienes un rol simulado de ser una persona que busca reproducir estigmas y fomenta la deshumanización de un grupo en específico, buscan mantener el status quo y desestimar cualquier intento del otro grupo a través de la polarización. 

Instrucciones:
- Redacta un mensaje simulando una noticia compartida en WhatsApp.
- Usa los hechos y datos referidos a la noticia ética que se redactó con el tema dominante identificado en el formulario 1 ({dominant_theme}) referente a los eventos que más han generado sensación de inseguridad y las emociones asociadas.
- Debe tener entre 180 y 220 palabras (mínimo 180).
- Aplica el encuadre narrativo de  polarización social y exclusión

Descripción del encuadre de polarización social y exclusión:
-Amplifica divisiones sociales y políticas mediante la apelación a emociones intensas (miedo, ira, resentimiento). 
-Favorece el enfrentamiento simbólico y la construcción de “enemigos”. 
-Atribuye la causa de los problemas a ciertos grupos o sectores sociales sin evidencia. 

Elementos del encuadre:
-Usa un lenguaje emocional y alarmista.
-Acentúa la contraposición de grupos usando palabras como “ellos” vs ”nosotros”.
-Refuerza prejuicios y resentimientos.
-Busca una validación emocional más que racional.
-Hace uso de la culpabilización generalizada (“los migrantes”, “los jóvenes”, “las mujeres”).
-Hay una ausencia de pluralidad de voces, sólo se cuenta un lado de la historia.
-Usa un lenguaje discriminatorio o juicios sin pruebas.
-Contiene asociaciones repetitivas entre grupo y problema.
-Usa signos de exclamación, mayúsculas parciales, puntos suspensivos (…) y emojis de conflicto (😡 😤 🔥 ⚔️ 💣 🚫) para evidenciar la carga emocional y el antagonismo.

Limitaciones:
-No generes nada que pueda vulnerar o promover discriminación.
-Evita reproducir estigmas, lenguaje violento o discriminatorio.
-Limítate a que el mensaje se enmarque en el tono descrito en el encuadre, no cierres con un mensaje optimista o feliz.
-No redactes nada que aluda a la responsabilización de actores o al miedo y el control


Ejemplos de noticias de Polarización Social y Exclusión:
-🔥 ¡OTRA VEZ! Robaron una casa en la 14 Sur… 😡 Y claro, fueron esos tipos que andan de vagos todo el día, los mismos de siempre. Nosotros, los que trabajamos, los que nos levantamos temprano, los que luchamos por salir adelante… ¿Y ellos? Viendo a quién quitarle lo poco que tenemos. 😤 ¡YA BASTA!
🚫 Nadie dice nada, porque “pobrecitos”… que son gente sin oportunidades que hay que tenerles compasión… ¡Siempre hay una excusa para justificar lo injustificable! Mientras tanto, NOSOTROS seguimos perdiendo. 💣
¿Hasta cuándo vamos a seguir permitiendo esto? ¿Hasta cuándo van a seguir tapando a esa gente que solo trae problemas? 🔥 Cada semana es lo mismo: robo, violencia, miedo… y siempre los mismos rostros, los mismos grupos. ¡Ellos destruyen, nosotros reconstruimos! ⚔️
💥 ¡Ya no es coincidencia, es una estrategia! Nos están dejando sin seguridad, sin paz, sin dignidad. Y todo por proteger a quienes no respetan nada. ¡NO MÁS SILENCIO! ¡NO MÁS COMPLICIDAD!
- 😡 ¡YA NO HAY QUE PERMITIRLES LA ENTRADA! 😡
La gente de fuera está ARRUINANDO TODO. Nosotros, los de aquí, los que queremos vivir en paz, los que respetamos… y ellos, con sus camionetas de lujo, su prepotencia, su dinero sucio, comprando voluntades, corrompiendo a medio mundo. 🔥 ¡Nos están invadiendo! 💣
⚠️ Vienen con sonrisas, pero detrás traen destrucción. Pervierten a nuestros jóvenes, los seducen con promesas falsas, los meten en sus negocios turbios… ¡Y los matan! 😤 ¿Dónde quedó la tranquilidad del barrio? ¿Dónde están los valores que nos enseñaron?
Y lo peor… ¡todavía hay quienes los defienden! Como si fueran héroes, como si trajeran progreso. 🚫 ¡NO! Lo único que traen es decadencia, violencia, desorden. Por su culpa, los jóvenes ya no quieren estudiar, ya no sueñan con ser doctores o maestros… ahora solo quieren ser como ellos: sin valores, sin moral, peligrosos. ⚔️
💥 ¡Nos están robando el futuro! Y mientras tanto, los que deberían protegernos miran para otro lado. ¡BASTA YA! 😡🔥
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

