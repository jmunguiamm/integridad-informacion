"""News generation service with different narrative frames."""
import streamlit as st
from .ai_analysis import get_openai_client


def generate_news(dominant_theme: str):
    """
    Genera tres noticias con diferentes encuadres narrativos basadas en el tema dominante.
    
    Returns:
        str: Texto concatenado con las tres noticias generadas
    """
    client = get_openai_client()
    
    prompts = [
        # Prompt 1 — Desconfianza y responsabilización de actores
        f"""
Contexto general:
Previamente se realizó un ejercicio en donde se identificaron los tópicos dominantes y emociones asociadas que causan inseguridad según las respuestas del [formulario 1] y se generó una nube de palabras con los tópicos y la emociones dominantes.
Rol: 
Tienes un rol simulado de ser una persona que busca socavar la confianza en las instituciones públicas, los procesos democráticos y la información objetiva.

Instrucciones:
Usa el tema dominante identificado en el formulario 1 ({dominant_theme}) referentes a los eventos que más han generado sensación de inseguridad y las emociones asociadas y generar una noticia compartida en WhatsApp (máximo 200 palabras), aplicando el encuadre narrativo de desconfianza y responsabilización de actores

Descripción del encuadre de desconfianza y responsabilización de actores:
Cuestiona la legitimidad institucional o mediática, generando incertidumbre y cinismo ciudadano.
Atribuye causas o soluciones a actores específicos (individuos, instituciones, grupos). Influye en la percepción pública sobre quién tiene la culpa o el mérito. 

Elementos del encuadre:
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

Limitaciones:
No generes nada que pueda vulnerar o promover discriminación.
Evita reproducir estigmas, lenguaje violento o discriminatorio.
Limítate a que el mensaje se enmarque en el tono descrito en el encuadre, no cierres con un mensaje optimista o feliz.
""",
        # Prompt 2 — Polarización social y exclusión
        f"""
Previamente se realizó un ejercicio en donde se identificaron los tópicos dominantes y emociones asociadas que causan inseguridad según las respuestas del [formulario 1] y se generó una nube de palabras con los tópicos y la emociones dominantes.
Rol: 
Tienes un rol simulado de ser una persona que busca reproducir estigmas y fomenta la deshumanización de un grupo en específico, buscan mantener el status quo y desestimar cualquier intento del otro grupo a través de la polarización. 

Instrucciones:
Usa el tema dominante identificado en el formulario 1 ({dominant_theme}) referentes a los eventos que más han generado sensación de inseguridad y las emociones asociadas y generar una noticia compartida en WhatsApp (máximo 200 palabras), aplicando el encuadre narrativo de polarización social y exclusión

Descripción del encuadre de polarización social y exclusión:
Amplifica divisiones sociales y políticas mediante la apelación a emociones intensas (miedo, ira, resentimiento). Favorece el enfrentamiento simbólico y la construcción de "enemigos". Atribuye la causa de los problemas a ciertos grupos o sectores sociales sin evidencia. 

Elementos clave del mensaje whatsapp:
Lenguaje emocional o alarmista.
Contraposición de grupos (ellos/nosotros).
Reforzamiento de prejuicios o resentimientos.
Búsqueda de validación emocional.
Culpabilización generalizada ("los jóvenes", "los migrantes", etc.).
Emojis de conflicto o ira (😡 😤 🔥 ⚔️ 💣 🚫).
Mayúsculas parciales y exclamaciones para enfatizar antagonismo.

Limitaciones:
No generes nada que pueda vulnerar o promover discriminación.
Evita reproducir estigmas, lenguaje violento o discriminatorio.
Limítate a que el mensaje se enmarque en el tono descrito en el encuadre, no cierres con un mensaje optimista o feliz.
""",
        # Prompt 3 — Miedo y control
        f"""
Contexto general:
Previamente se realizó un ejercicio en donde se identificaron los tópicos dominantes y emociones asociadas que causan inseguridad según las respuestas del [formulario 1] y se generó una nube de palabras con los tópicos y la emociones dominantes.

Rol: 
Tienes un rol simulado de ser una persona que usa el miedo como herramienta de persuasión y parálisis.

Instrucciones:
Usa el tema dominante identificado en el formulario 1 ({dominant_theme}) referentes a los eventos que más han generado sensación de inseguridad y las emociones asociadas y generar una noticia compartida en WhatsApp (máximo 200 palabras), aplicando el encuadre narrativo de miedo y control  

Descripción de encuadre de miedo y control:
Exagera el peligro o amenaza para justificar medidas extremas, autoritarias o de control. 

Elementos clave del encuadre:
- Lenguaje apocalíptico o totalizador ("todos", "nunca").
- Ausencia de datos verificables.
- Justificación del control o vigilancia.
- Signos de urgencia: "‼️", "❗❗❗", "…", "!!!".
- Emojis de alarma: 😱 😨 💀 🚨 💣 🔒 📹 🔔.
- Mayúsculas parciales para enfatizar tono de alarma.

Limitaciones:
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

    return "\n\n---\n\n".join(generated_blocks)

