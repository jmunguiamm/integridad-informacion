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
    Eres un analista de talleres educativos sobre información errónea.

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


def analyze_trends(form1_df, form0_df, *, max_form1_rows: int = 100, max_form0_rows: int = 30):
    """Analiza Form 0 + Form 1 y devuelve el JSON con el tema dominante."""
    import json
    import re

    if form1_df is None or form1_df.empty:
        raise ValueError("Form 1 está vacío; no se puede analizar.")

    def _rows_to_text(df, limit):
        return "\n".join(
            f"{i+1}) " + " | ".join(f"{k}={v}" for k, v in row.items())
            for i, row in enumerate(df.to_dict("records")[:limit])
        ) or "(vacío)"

    sample_form1 = _rows_to_text(form1_df, max_form1_rows)
    context_form0 = (
        _rows_to_text(form0_df, max_form0_rows)
        if form0_df is not None and not form0_df.empty
        else "(vacío)"
    )

    analysis_prompt = f"""
    Actúa como un **analista de datos cualitativos experto en comunicación social, seguridad y percepción pública**. 
    Tu tarea es interpretar información proveniente de talleres educativos sobre integridad de la información, desinformación y emociones sociales.

    Dispones de dos fuentes de entrada:

    [Formulario 0 – Contexto del grupo y del entorno local]
    {context_form0}

    [Formulario 1 – Percepciones de inseguridad y consumo informativo]
    {sample_form1}

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
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No se pudo extraer JSON del análisis de tema dominante:\n{text[:400]}...")
    return json.loads(match.group(0))

def analyze_final_report(
    df_long_normalized,        # DataFrame largo: Taller, Marca temporal, Encuadre, Número de tarjeta, Género, Pregunta, Valor
    dominant_theme: str,       # st.session_state["dominant_theme"]
    news_blocks: list[dict],   # [{'encuadre': '...', 'text': '...'}, ...] (3 items)
    form0_context_text: str = ""  # (opcional) contexto de Form 0 en crudo o resumido
    ) -> str:
    """
    Genera el informe final (texto + instrucciones de gráficos) usando IA,
    con contexto del tema dominante, textos y encuadres de las noticias y
    respuestas del Form 2 normalizadas (cruzadas con Form 1/0).
    Devuelve Markdown estructurado.
    """
    import pandas as pd
    import textwrap

    # 1) Compactar tablas a un muestreo legible para el prompt
    #    (evita toquetazos enormes; priorizamos filas recientes o primeras N)
    if isinstance(df_long_normalized, pd.DataFrame) and not df_long_normalized.empty:
        # Reducir a ~250 filas máximo para mantener prompt controlado
        df_sample = df_long_normalized.head(250).copy()
        # Exportar a CSV inline (más legible que JSON para ojos humanos del modelo)
        csv_preview = df_sample.to_csv(index=False)
    else:
        csv_preview = "(sin datos normalizados)"

    # 2) Estructurar bloque de noticias (encuadre + texto)
    news_summaries = []
    for i, nb in enumerate(news_blocks, start=1):
        enc = (nb.get("encuadre") or f"Noticia {i}").strip()
        txt = (nb.get("text") or "").strip()
        # Truncar cada noticia a ~900 caracteres por seguridad
        if len(txt) > 900:
            txt = txt[:900] + "…"
        news_summaries.append(f"- {enc}:\n{txt}")

    news_block_txt = "\n\n".join(news_summaries) if news_summaries else "(no hay noticias generadas)"

    # 3) Construir prompt 
    prompt = f"""
    Contexto:
        Se ha realizado un ejercicio donde se generaron tres noticias diferentes sobre un mismo evento,
    cada una con un encuadre narrativo distinto. Los participantes completaron un formulario indicando,
    para cada noticia: (a) emociones que sienten al leerla, (b) grado de confiabilidad percibida y
    (c) elementos clave que llamaron su atención.

    Rol:
    Eres un analista senior en ciencia de datos y visualización. Debes construir un informe profundo y accionable
    por cada taller registrado, articulando los hallazgos con el tema dominante y el contexto narrativo de las noticias generadas.

    Insumos clave del taller:
    - Tema dominante (derivado del análisis previo): "{dominant_theme}"
    - Contexto Form 0 (resumen/fragmento): "{(form0_context_text or '').strip()}"
    - Noticias generadas (encuadre + texto):
    {news_block_txt}
    "
    - Datos normalizados de respuestas (CSV; columnas: Taller, Marca temporal, Encuadre, Número de tarjeta, Género, Pregunta, Valor):
    {csv_preview}

    Metodología de análisis requerida:
    1) Trabaja taller por taller: identifica cada valor único de "Taller" y sintetiza las particularidades del grupo.
    2) Describe cómo las emociones, la confianza y los elementos clave varían según encuadre dentro de cada taller.
    3) Relaciona explícitamente los resultados con el tema dominante y con los fragmentos narrativos de las noticias; menciona coincidencias y tensiones.
    4) Analiza diferencias relevantes por género dentro de cada taller y compara entre talleres si emergen contrastes significativos.
    5) Destaca patrones transversales, correlaciones o sesgos latentes que surjan al cruzar las variables (incluyendo género, encuadre y valores reportados), señalando posibles riesgos o oportunidades del taller.
    6) Si los datos de un taller o variable son insuficientes, indícalo antes de extraer conclusiones.

    Objetivo del análisis (entregar texto + un gráfico explicativo por cada punto):
    1) Cómo varían las emociones, el nivel de confianza y los componentes clave según el tipo de encuadre narrativo.
    2) Diferencias de percepción y reacción emocional a las noticias según el género.
    3) Patrones emergentes y relaciones significativas entre variables; a partir de ellos, identifica sesgos posibles que no se hayan abordado en los análisis por encuadre y por género.

    Formato de salida:
    Devuelve **Markdown estructurado**, con secciones claras. Dentro de cada sección, menciona explícitamente los aprendizajes por taller (usa subtítulos o párrafos separados para cada taller cuando corresponda):
    ## Variación por encuadre
    - Texto analítico sintético (2–4 párrafos).
    ## Diferencias por género
    - Texto analítico sintético (2–3 párrafos).
    ## Patrones y sesgos emergentes
    - Texto analítico (2–4 párrafos), señalando relaciones y sesgos potenciales derivados de las respuestas.

    Reglas de estilo tipográfico (alineadas con la interfaz):
    - Usa encabezados y subtítulos siguiendo la jerarquía Markdown indicada.
    - Redacta los párrafos en un tono analítico, con frases completas y claras.
    - Formatea listas con guiones simples (`-`). Evita listas numeradas salvo que aporten claridad.
    - Resalta conceptos clave con **negritas** cuando sea necesario, sin abusar del formato.
    - Mantén la longitud de los párrafos entre 2 y 4 oraciones para facilitar la lectura.

    Reglas:
    - Usa únicamente información derivada de los datos provistos (no inventes).
    - Tono analítico y educativo, claro y sintético.
    - No incluyas código en la respuesta; solo recomendaciones de visualización y narrativa.
    - Si un análisis no es concluyente por falta de datos, indícalo explícitamente.
    """

    client = get_openai_client()
    with st.spinner("📊 Generando análisis final con IA…"):
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.35,
            max_tokens=1400,
            messages=[
                {"role": "system", "content": "Eres un analista senior en ciencia de datos y visualización."},
                {"role": "user", "content": textwrap.dedent(prompt).strip()},
            ],
        )
    return resp.choices[0].message.content.strip()


import json
import re
import streamlit as st
from .ai_analysis import get_openai_client


def _get_generated_news_text() -> str:
    raw = st.session_state.get("generated_news_raw")
    if raw:
        return raw
    return "(no hay noticias generadas)"


def analyze_emotions_json(df_all, dominant_theme: str, form0_context_text: str):
    """Analiza variaciones emocionales por encuadre dentro de cada taller."""
    client = get_openai_client()
    sample = df_all.head(200).to_dict(orient="records")
    sample_txt = "\n".join([f"{i+1}) {row}" for i, row in enumerate(sample)])

    news_block_txt = _get_generated_news_text()

    workshop_code = st.session_state.get("selected_workshop_code", "sin_codigo")

    workshop_code = st.session_state.get("selected_workshop_code", "sin_codigo")

    prompt = f"""
Contexto:
Dentro del taller de integridad de la información se ha realizado un ejercicio donde se generaron tres noticias diferentes sobre un mismo evento, cada una con un encuadre narrativo distinto. 
Los participantes completaron un formulario indicando, para cada noticia: (a) emociones que sienten al leerla, (b) grado de confiabilidad percibida y (c) elementos clave que llamaron su atención.
Rol:
Eres un analista en ciencia de datos que trabaja con los datos para generar preguntas que provoquen una conversación en torno a las emociones y los encuadres narrativos.

Insumos clave del taller:
- Tema dominante (derivado del análisis previo): "{dominant_theme}"
- Contexto Form 0 (resumen/fragmento): "{(form0_context_text or '').strip()}"
- Número del taller (código único): "{workshop_code}"
- Noticias generadas (encuadre + texto): {news_block_txt}
- Tipos de encuadre narrativo: 
- Encuadres narrativos: "Encuadre de desconfianza y responsabilización de actores:
    Cuestiona la legitimidad institucional o mediática, genera incertidumbre y cinismo ciudadano, e influye en la percepción pública sobre quién tiene la culpa o el mérito, atribuyendo causas o soluciones a actores específicos (individuos, instituciones, grupos). Utiliza lenguaje causal (“por”, “debido a”, “por culpa de”) para responsabilizar, culpar o exigir, orientando la desconfianza hacia instituciones cuya imparcialidad o transparencia se pone en duda. Recurre a reclamos generalizados como “todos son corruptos”, “nunca dicen la verdad”, “siempre lucran con nuestra confianza”, y a referencias de traición. Suele deslegitimar fuentes oficiales o periodísticas, justificando que están cooptadas o manipuladas, y emplea recursos gráficos como emojis escépticos o de advertencia (🤔 😒 ⚠️ 👀), signos de sospecha o ironía (“¿?”, “…” y “—”), además de mayúsculas parciales o exclamaciones para expresar hartazgo y desconfianza. También puede reforzar la rendición de cuentas o la culpabilización.
    Encuadre de polarización social y exclusión:
    Amplifica divisiones sociales y políticas apelando a emociones intensas como miedo, ira y resentimiento, favoreciendo el enfrentamiento simbólico y la construcción de “enemigos” mediante la atribución de problemas a ciertos grupos o sectores sin evidencia. Utiliza lenguaje emocional y alarmista, acentúa la contraposición entre “ellos” y “nosotros”, refuerza prejuicios y resentimientos, y busca validación emocional más que racional. Se caracteriza por culpabilización generalizada (“los migrantes”, “los jóvenes”, “las mujeres”), ausencia de pluralidad de voces, juicios sin pruebas, asociaciones repetitivas entre grupo y problema, y recursos gráficos como signos de exclamación, mayúsculas parciales, puntos suspensivos (…) y emojis de conflicto (😡 😤 🔥 ⚔️ 💣 🚫) que evidencian la carga emocional y el antagonismo. 
    Encuadre de miedo y control:
    Exagera el peligro o la amenaza para justificar medidas extremas, autoritarias o de control, utilizando un lenguaje apocalíptico, urgente y totalizador, acompañado de imágenes impactantes o repetitivas de violencia y ausencia de datos verificables. Recurre a la justificación del control o vigilancia, limita la libertad mediante recomendaciones alarmistas, y enfatiza la desesperación con signos de puntuación exagerados (‼️, ❗❗❗, …, ???, !!! →), emojis de alerta o terror (😱 😨 😰 💀 🔥 ⚠️ 🚨 💣 👁️‍🗨️ 🔒 📹 🔔 🧟), uso de mayúsculas parciales y repeticiones dramáticas como “Ya es tarde… demasiado tarde… 😨”, todo ello para generar una atmósfera de miedo, urgencia y control."
- Datos de entrada:
{sample_txt}

---

🎯 Objetivo:
Identificar cómo las **emociones** varían según el encuadre narrativo dentro de cada taller.

Metodología de análisis requerida:
1)Une las respuestas completas de cada persona relacionando los resultados de los formularios a través del código personal que permite identificar todas las respuestas de una misma persona.
2)Identifica cómo las emociones varían según el encuadre.
3)Genera dos preguntas  (hasta 20 palabras) que permitan al grupo discutir sobre los hallazgos sobre las emociones presentadas en cada encuadre.Ejemplos: ¿Cómo influyeron los diferentes encuadres en la percepción emocional del grupo?

Reglas:
- Usa únicamente información derivada de los datos provistos (no inventes).
- Tono analítico y educativo, claro y sintético.
- Si un análisis no es concluyente por falta de datos, indícalo explícitamente.
- No generalices ni produzcas estigmatizaciones, presenta los resultados como exclusivos del grupo

    ---

    📄 Formato JSON:
    {{
      "workshops": [
        {{
          "taller": "{workshop_code}",
          "emociones_por_encuadre": {{
            "Desconfianza y responsabilización de actores": ["emocion1", "emocion2"],
            "Polarización social y exclusión": ["emocion1", "emocion2"],
            "Miedo y control": ["emocion1", "emocion2"]
          }},
          "resumen": "<síntesis breve del patrón emocional (2–3 frases)>",
          "preguntas_discusion": ["<pregunta 1>", "<pregunta 2>"]
        }}
      ]
    }}

    Devuelve únicamente el JSON anterior sin texto adicional.
    """

    with st.spinner("Analizando emociones por encuadre..."):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )

    text = resp.choices[0].message.content.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(
            "No se pudo extraer JSON del análisis de emociones. Respuesta del modelo:\n"
            f"{text[:400]}..."
        )
    data = json.loads(match.group(0))
    return data


def analyze_gender_impacts_json(df_all, dominant_theme: str, form0_context_text: str):
    """Analiza impactos diferenciados por género y encuadre."""
    client = get_openai_client()
    sample = df_all.head(200).to_dict(orient="records")
    sample_txt = "\n".join([f"{i+1}) {row}" for i, row in enumerate(sample)])

    news_block_txt = _get_generated_news_text()

    workshop_code = st.session_state.get("selected_workshop_code", "sin_codigo")

    prompt = f"""
Contexto:
Dentro del taller de integridad de la información se ha realizado un ejercicio donde se generaron tres noticias diferentes sobre un mismo evento, cada una con un encuadre narrativo distinto. 
Los participantes completaron un formulario indicando, para cada noticia: (a) emociones que sienten al leerla, (b) grado de confiabilidad percibida y (c) elementos clave que llamaron su atención.

Rol:
Eres un analista en ciencia de datos que trabaja con los datos para generar análisis interseccionales sobre la integridad de la información y el impacto diferenciado en el género

Insumos clave del taller:
- Tema dominante: "{dominant_theme}"
- Contexto Form 0: "{(form0_context_text or '').strip()}"
- Número del taller (código único): "{workshop_code}"
- Tipos de encuadre narrativo: 
- Encuadres narrativos: "Encuadre de desconfianza y responsabilización de actores:
    Cuestiona la legitimidad institucional o mediática, genera incertidumbre y cinismo ciudadano, e influye en la percepción pública sobre quién tiene la culpa o el mérito, atribuyendo causas o soluciones a actores específicos (individuos, instituciones, grupos). Utiliza lenguaje causal (“por”, “debido a”, “por culpa de”) para responsabilizar, culpar o exigir, orientando la desconfianza hacia instituciones cuya imparcialidad o transparencia se pone en duda. Recurre a reclamos generalizados como “todos son corruptos”, “nunca dicen la verdad”, “siempre lucran con nuestra confianza”, y a referencias de traición. Suele deslegitimar fuentes oficiales o periodísticas, justificando que están cooptadas o manipuladas, y emplea recursos gráficos como emojis escépticos o de advertencia (🤔 😒 ⚠️ 👀), signos de sospecha o ironía (“¿?”, “…” y “—”), además de mayúsculas parciales o exclamaciones para expresar hartazgo y desconfianza. También puede reforzar la rendición de cuentas o la culpabilización.
    Encuadre de polarización social y exclusión:
    Amplifica divisiones sociales y políticas apelando a emociones intensas como miedo, ira y resentimiento, favoreciendo el enfrentamiento simbólico y la construcción de “enemigos” mediante la atribución de problemas a ciertos grupos o sectores sin evidencia. Utiliza lenguaje emocional y alarmista, acentúa la contraposición entre “ellos” y “nosotros”, refuerza prejuicios y resentimientos, y busca validación emocional más que racional. Se caracteriza por culpabilización generalizada (“los migrantes”, “los jóvenes”, “las mujeres”), ausencia de pluralidad de voces, juicios sin pruebas, asociaciones repetitivas entre grupo y problema, y recursos gráficos como signos de exclamación, mayúsculas parciales, puntos suspensivos (…) y emojis de conflicto (😡 😤 🔥 ⚔️ 💣 🚫) que evidencian la carga emocional y el antagonismo. 
    Encuadre de miedo y control:
    Exagera el peligro o la amenaza para justificar medidas extremas, autoritarias o de control, utilizando un lenguaje apocalíptico, urgente y totalizador, acompañado de imágenes impactantes o repetitivas de violencia y ausencia de datos verificables. Recurre a la justificación del control o vigilancia, limita la libertad mediante recomendaciones alarmistas, y enfatiza la desesperación con signos de puntuación exagerados (‼️, ❗❗❗, …, ???, !!! →), emojis de alerta o terror (😱 😨 😰 💀 🔥 ⚠️ 🚨 💣 👁️‍🗨️ 🔒 📹 🔔 🧟), uso de mayúsculas parciales y repeticiones dramáticas como “Ya es tarde… demasiado tarde… 😨”, todo ello para generar una atmósfera de miedo, urgencia y control."
- Datos combinados:
{sample_txt}

---
Metodología de análisis requerida:
2) Une las respuestas completas de cada persona relacionando los resultados de los formularios a través del código personal que permite identificar todas las respuestas de una misma persona.
3)Identifica los patrones y hallazgos relevantes de las respuestas e identifica contrastes significativos.
5) Destaca patrones transversales y correlaciones latentes que surjan al cruzar las variables del género con los encuadres narrativos y niveles de confianza.
6) En no más de dos párrafos de 4 líneas describe los hallazgos principales de estos cruces. Ejemplo: “Las mujeres mostraron una mayor sensibilidad emocional  a la noticia con el encuadre de polarización y su nivel de confianza en la credibilidad de la noticia fue mayor que los otros géneros, mientras que los hombres tendieron a reaccionar más y confiar más en las noticias con los mensajes del encuadre de responsabilización institucional.”
7) Genera dos preguntas (hasta 20 palabras) que permitan al grupo discutir sobre los hallazgos. Ejemplo: ¿Qué relación podría haber entre el género y la percepción del las emociones? ¿Cómo podrían influir estas diferencias en la forma en la que reaccionamos a las noticias?¿Qué rol juegan las emociones en el nivel de confianza que se le otorgó a los difenrentes encuadres? 
---

 Reglas:
- Usa únicamente información derivada de los datos provistos (no inventes).
- Tono analítico y educativo, claro y sintético.
- Si los datos de un taller o variable son insuficientes, indícalo antes de extraer conclusiones.
    - No generalices ni produzcas estigmatizaciones, presenta los resultados como exclusivos del grupo

    ---

    📄 Formato JSON:
    {{
      "analisis_genero": [
        {{
          "taller": "{workshop_code}",
          "patrones_por_genero": {{
            "Femenino": "<síntesis de emociones y confianza>",
            "Masculino": "<síntesis de emociones y confianza>",
            "Otro/No binario": "<síntesis si aplica>"
          }},
          "hallazgos_transversales": "<resumen general de diferencias detectadas>",
          "preguntas_discusion": ["<pregunta 1>", "<pregunta 2>"]
        }}
      ]
    }}

    Devuelve únicamente el JSON anterior sin texto adicional.
    """

    with st.spinner("Analizando impactos diferenciados por género..."):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.35,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )

    text = resp.choices[0].message.content.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(
            "No se pudo extraer JSON del análisis de género. Respuesta del modelo:\n"
            f"{text[:400]}..."
        )
    data = json.loads(match.group(0))
    return data


def analyze_general_json(df_all, dominant_theme: str, form0_context_text: str):
    """Análisis general interseccional de emociones, confianza y sesgos cognitivos."""
    client = get_openai_client()
    sample = df_all.head(200).to_dict(orient="records")
    sample_txt = "\n".join([f"{i+1}) {row}" for i, row in enumerate(sample)])

    news_block_txt = _get_generated_news_text()
    workshop_code = st.session_state.get("selected_workshop_code", "sin_codigo")

    prompt = f"""
Contexto:
Dentro del taller de integridad de la información se ha realizado un ejercicio donde se generaron tres noticias diferentes sobre un mismo evento, cada una con un encuadre narrativo distinto. 
Los participantes completaron un formulario indicando, para cada noticia: (a) emociones que sienten al leerla, (b) grado de confiabilidad percibida y (c) elementos clave que llamaron su atención.

Rol:
Eres un analista en ciencia de datos que trabaja con los datos para generar análisis interseccionales sobre la integridad de la información

Insumos clave del taller:
- Tema dominante (derivado del análisis previo): "{dominant_theme}"
- Contexto Form 0 (resumen/fragmento): "{(form0_context_text or '').strip()}"
- Noticias generadas (encuadre + texto): {news_block_txt}
- Número del taller (código único): "{workshop_code}"
- Tipos de encuadre narrativo: 
Encuadre de desconfianza y responsabilización de actores:
Cuestiona la legitimidad institucional o mediática, genera incertidumbre y cinismo ciudadano, e influye en la percepción pública sobre quién tiene la culpa o el mérito, atribuyendo causas o soluciones a actores específicos (individuos, instituciones, grupos). Utiliza lenguaje causal (“por”, “debido a”, “por culpa de”) para responsabilizar, culpar o exigir, orientando la desconfianza hacia instituciones cuya imparcialidad o transparencia se pone en duda. Recurre a reclamos generalizados como “todos son corruptos”, “nunca dicen la verdad”, “siempre lucran con nuestra confianza”, y a referencias de traición. Suele deslegitimar fuentes oficiales o periodísticas, justificando que están cooptadas o manipuladas, y emplea recursos gráficos como emojis escépticos o de advertencia (🤔 😒 ⚠️ 👀), signos de sospecha o ironía (“¿?”, “…” y “—”), además de mayúsculas parciales o exclamaciones para expresar hartazgo y desconfianza. También puede reforzar la rendición de cuentas o la culpabilización.
Encuadre de polarización social y exclusión:
Amplifica divisiones sociales y políticas apelando a emociones intensas como miedo, ira y resentimiento, favoreciendo el enfrentamiento simbólico y la construcción de “enemigos” mediante la atribución de problemas a ciertos grupos o sectores sin evidencia. Utiliza lenguaje emocional y alarmista, acentúa la contraposición entre “ellos” y “nosotros”, refuerza prejuicios y resentimientos, y busca validación emocional más que racional. Se caracteriza por culpabilización generalizada (“los migrantes”, “los jóvenes”, “las mujeres”), ausencia de pluralidad de voces, juicios sin pruebas, asociaciones repetitivas entre grupo y problema, y recursos gráficos como signos de exclamación, mayúsculas parciales, puntos suspensivos (…) y emojis de conflicto (😡 😤 🔥 ⚔️ 💣 🚫) que evidencian la carga emocional y el antagonismo.
Encuadre de miedo y control:
Exagera el peligro o la amenaza para justificar medidas extremas, autoritarias o de control, utilizando un lenguaje apocalíptico, urgente y totalizador, acompañado de imágenes impactantes o repetitivas de violencia y ausencia de datos verificables. Recurre a la justificación del control o vigilancia, limita la libertad mediante recomendaciones alarmistas, y enfatiza la desesperación con signos de puntuación exagerados (‼️, ❗❗❗, …, ???, !!! →), emojis de alerta o terror (😱 😨 😰 💀 🔥 ⚠️ 🚨 💣 👁️‍🗨️ 🔒 📹 🔔 🧟), uso de mayúsculas parciales y repeticiones dramáticas como “Ya es tarde… demasiado tarde… 😨”, todo ello para generar una atmósfera de miedo, urgencia y control.
- Contexto Form 1  
- Contexto Form 2
Datos de entrada:
{sample_txt}

---

🎯 Objetivo:
Detectar patrones transversales entre emociones, confianza, encuadres y sesgos cognitivos percibidos.

Metodología de análisis requerida:
2) Une las respuestas completas de cada persona relacionando los resultados de los formularios a través del código personal que permite identificar todas las respuestas de una misma persona.
3)Identifica los patrones y hallazgos relevantes de las respuestas y compara entre sí emergen contrastes significativos.
5) Destaca patrones transversales y correlaciones latentes que surjan al cruzar las variables de los formularios, y la información de los tipos de encuadres y  los tipos de sesgos cognitivos.
6) En función de las respuestas identifica algunos sesgos que puedan estar asociados. 
7)En no más de dos párrafos de 4 líneas describe los hallazgos principales y las conclusiones de los hallazgos.

---
Reglas:
- Usa únicamente información derivada de los datos provistos (no inventes).
- Tono analítico y educativo, claro y sintético.
- Si los datos de un taller o variable son insuficientes, indícalo antes de extraer conclusiones.
- No generalices ni produzcas estigmatizaciones, presenta los resultados como exclusivos del grupo
    - Formatea listas con guiones simples (`-`). Evita listas numeradas salvo que aporten claridad.
    - Resalta conceptos clave con **negritas** cuando sea necesario, sin abusar del formato.
    - Mantén la longitud de los párrafos entre 2 y 4 oraciones para facilitar la lectura.

    ---

    📄 Formato JSON:
    {{
      "resumen_general": {{
        "taller": "{workshop_code}",
        "patrones_transversales": "<síntesis en 3–5 oraciones>",
        "sesgos_identificados": ["<sesgo1>", "<sesgo2>"],
        "hallazgos_clave": "<resumen de 4 líneas>"
      }}
    }}

    Devuelve únicamente el JSON anterior sin texto adicional.
    """

    with st.spinner("Generando análisis general del taller..."):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.35,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )

    text = resp.choices[0].message.content.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(
            "No se pudo extraer JSON del análisis general. Respuesta del modelo:\n"
            f"{text[:400]}..."
        )
    data = json.loads(match.group(0))
    return data
