"""OpenAI analysis services."""
import streamlit as st
from config.secrets import read_secrets


@st.cache_resource(show_spinner=False)
def get_openai_client():
    """Devuelve cliente OpenAI."""
    from openai import OpenAI
    api_key = read_secrets("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY.")
    return OpenAI(api_key=api_key)


def analyze_reactions(df_all, key):
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
    - "Principales patrones emocionales"
    - "Comparación entre encuadres"
    - "Factores del contexto que influyen"
    - "Recomendaciones pedagógicas para la siguiente sesión"
    5️⃣ Agrega un breve párrafo de síntesis general para el reporte final.

    Datos:
    {sample_txt}

    Responde en Markdown estructurado.
    """
    client = get_openai_client()
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


def analyze_trends(form1_sample, form0_context):
    """Analyze trends and dominant themes from Form 0 and Form 1."""
    import json
    import re
    
    context_text = form0_context or "(vacío)"
    sample = form1_sample or "(vacío)"

    analysis_prompt = f"""
    Actúa como un **analista de datos cualitativos experto en comunicación social, seguridad y percepción pública**. 
    Tu tarea es interpretar información proveniente de talleres educativos sobre integridad de la información, desinformación y emociones sociales.

    Dispones de dos fuentes de entrada:

    [Formulario 0 – Contexto del grupo y del entorno local]
    {context_text}

    [Formulario 1 – Percepciones de inseguridad y consumo informativo]
    {sample}

    ---

    🎯 **Objetivo del análisis:**
    Identificar el **tema o fenómeno dominante** que genera inseguridad entre las personas participantes, 
    entendiendo el **contexto y el tipo específico de problema** (no solo la categoría general).

    El tema dominante debe reflejar no solo "qué" tipo de fenómeno ocurre, 
    sino también "**en qué contexto o modalidad**" (por ejemplo: "violencia de género en espacios públicos", 
    "criminalidad asociada al narcotráfico", "corrupción institucional ligada a la seguridad", etc.).

    ---

    🧩 **Tareas específicas:**
    1️⃣ Analiza ambas fuentes para determinar el **tema o fenómeno dominante** con su contexto: tipo de hecho, actores, causas y entorno social o mediático.  
    2️⃣ Distingue las **subdimensiones o manifestaciones** del fenómeno (por ejemplo, "violencia" → "violencia de género" o "violencia digital").  
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
    - El tema debe ser **específico y contextual** (no solo "violencia" o "inseguridad"). Ejemplo: "violencia de género en espacios públicos", "corrupción policial asociada al narcotráfico", "desempleo juvenil y percepción de abandono institucional".  
    - Usa solo información que pueda inferirse de los datos.  
    - Mantén tono analítico, educativo y en español mexicano natural.  
    - Devuelve **únicamente JSON estructurado**.
    """
    
    client = get_openai_client()
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
    return data

