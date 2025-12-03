"""Data cleaning and normalization functions."""
import re
import unicodedata
import pandas as pd
import streamlit as st
from .utils import get_date_column_name, normalize_date, sanitize_workshop_code_value


def _normalize_column_name(text: str) -> str:
    if not isinstance(text, str):
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    return without_accents.lower().strip()


def _normalize_question_slug(text: str) -> str:
    """Return a stripped, alphanumeric-only slug to compare column names."""
    normalized = _normalize_column_name(text)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _find_workshop_code_column(df: pd.DataFrame) -> str | None:
    candidates: list[tuple[str, int, str]] = []
    for col in df.columns:
        normalized = _normalize_column_name(col)
        if "numero" in normalized and "taller" in normalized:
            non_null = df[col].notna().sum()
            candidates.append((col, non_null, normalized))
    if not candidates:
        return None

    def _priority(item: tuple[str, int, str]) -> tuple[int, int]:
        col, non_null, normalized = item
        has_ingresa = 1 if "ingresa" in normalized else 0
        return (non_null, has_ingresa)

    candidates.sort(key=_priority, reverse=True)
    return candidates[0][0]


def filter_df_by_date(df: pd.DataFrame, target_date: str = None, workshop_code: str | None = None) -> pd.DataFrame:
    """Filtra un DataFrame por fecha y (opcionalmente) por 'número de taller'."""
    if df.empty:
        return df

    workshop_code = sanitize_workshop_code_value(workshop_code)
    if not workshop_code:
        workshop_code = sanitize_workshop_code_value(st.session_state.get("selected_workshop_code"))

    result_df = df.copy()

    # --- Filtro por fecha ---
    if target_date:
        date_col = get_date_column_name(result_df)
        if not date_col and len(result_df.columns) > 0:
            date_col = result_df.columns[0]

        if date_col:
            try:
                result_df["_normalized_date"] = result_df[date_col].apply(normalize_date)
                result_df = result_df[result_df["_normalized_date"] == target_date]
                result_df = result_df.drop(columns=["_normalized_date"])
            except Exception:
                # Si hay error en el filtrado, regresar DataFrame original
                return df
        else:
            return df

        if result_df.empty:
            return result_df

    # --- Filtro por número de taller ---
    if workshop_code:
        code_col = _find_workshop_code_column(result_df)
        if code_col:
            code_series = result_df[code_col].astype(str).str.strip()
            code_series = code_series.str.replace(r"\.0+$", "", regex=True)
            target_code = str(workshop_code).strip()
            if target_code.endswith(".0"):
                target_code = target_code[:-2]
            result_df = result_df[code_series == target_code]

    return result_df


def normalize_form_data(
    form1: pd.DataFrame,
    form2: pd.DataFrame,
    workshop_date: str | None = None,
    workshop_code: str | None = None,
    show_debug: bool = False,
):
    """
    Transforma Form1 y Form2 en formato normalizado según el esquema especificado.
    
    Args:
        form1: DataFrame del Form1
        form2: DataFrame del Form2
        workshop_date: Fecha del taller para filtrar (opcional)
        show_debug: Si True, muestra información de debug en Streamlit
    
    Returns:
        Tupla (DataFrame normalizado, DataFrame largo intermedio) o DataFrame normalizado si show_debug=False
        DataFrame normalizado con columnas: Taller, Marca temporal, Encuadre, Número de tarjeta, Género, Pregunta, Valor
    """
    explicit_code = sanitize_workshop_code_value(workshop_code)
    selected_code = sanitize_workshop_code_value(st.session_state.get("selected_workshop_code"))
    fallback_code = sanitize_workshop_code_value(st.session_state.get("codigo_taller"))
    resolved_code = explicit_code or selected_code or fallback_code
    workshop_identifier = resolved_code or workshop_date or "T_001"

    # Filtrar por fecha si se especifica
    if workshop_date:
        form1 = filter_df_by_date(form1.copy(), workshop_date, resolved_code)
        form2 = filter_df_by_date(form2.copy(), workshop_date, resolved_code)
    else:
        form1 = filter_df_by_date(form1.copy(), None, resolved_code)
        form2 = filter_df_by_date(form2.copy(), None, resolved_code)
    
    # Verificar que los DataFrames no estén vacíos después del filtrado
    if form1.empty:
        if show_debug:
            st.error("❌ Form1 está vacío. No se puede procesar.")
        return (pd.DataFrame(), pd.DataFrame()) if show_debug else pd.DataFrame()
    
    if form2.empty:
        if show_debug:
            st.error("❌ Form2 está vacío. No se puede procesar.")
        return (pd.DataFrame(), pd.DataFrame()) if show_debug else pd.DataFrame()
    
    # === 1️⃣ Preparar Form1 base ===
    # Buscar columna de tarjeta
    tarjeta_col = None
    for col in form1.columns:
        col_lower = col.lower()
        if "tarjeta" in col_lower:
            tarjeta_col = col
            break
    
    # Si no encuentra, buscar por otros términos
    if not tarjeta_col:
        for key in ["número", "numero", "number", "card", "asignado"]:
            for col in form1.columns:
                col_lower = col.lower()
                if key in col_lower:
                    tarjeta_col = col
                    break
            if tarjeta_col:
                break
    
    # Buscar columna de género
    genero_col = None
    for col in form1.columns:
        col_lower = col.lower()
        if "género" in col_lower or "genero" in col_lower:
            genero_col = col
            break
    
    # Si no encuentra género, buscar por otros términos
    if not genero_col:
        for key in ["gender", "sexo", "identificas"]:
            for col in form1.columns:
                col_lower = col.lower()
                if key in col_lower:
                    genero_col = col
                    break
            if genero_col:
                break
    
    # Obtener columna de marca temporal
    marca_col = get_date_column_name(form1)
    
    if not tarjeta_col or not marca_col:
        error_msg = f"No se encontraron columnas necesarias en Form1. Tarjeta: {tarjeta_col}, Marca temporal: {marca_col}"
        raise ValueError(error_msg)
    
    # Preparar base de Form1
    form1_base_cols = [marca_col, tarjeta_col]
    if genero_col:
        form1_base_cols.append(genero_col)
    
    form1_base = form1[form1_base_cols].copy()
    form1_base.columns = ["marca_temporal", "tarjeta"] + (["genero"] if genero_col else [])
    form1_base["Taller"] = workshop_identifier or "T_001"
    
    # === 2️⃣ Mapeo de encuadres ===
    encuadre_map = {
        1: "Desconfianza y responsabilización de actores",
        2: "Polarización social y exclusión",
        3: "Miedo y control",
    }
    
    # === 3️⃣ Detectar columnas dinámicamente en Form2 ===
    def _find_form2_column(keywords: list[str]) -> str | None:
        for col in form2.columns:
            slug = _normalize_question_slug(col)
            if all(keyword in slug for keyword in keywords):
                return col
        return None
    
    # === 4️⃣ Transformar Form2 en formato largo ===
    rows = []
    
    # Buscar columna de tarjeta y marca temporal con nombres flexibles
    tarjeta_col_f2 = _find_form2_column(["numero", "tarjeta"]) or _find_form2_column(["tarjeta"])
    marca_col_f2 = _find_form2_column(["marca", "temporal"]) or get_date_column_name(form2)

    if not tarjeta_col_f2 or not marca_col_f2:
        if show_debug:
            st.error(
                "❌ No se encontraron las columnas de tarjeta o marca temporal en Form2."
            )
            st.write("📋 Columnas detectadas en Form2:")
            for col in form2.columns:
                st.write(f"  - {col}")
        return (pd.DataFrame(), pd.DataFrame()) if show_debug else pd.DataFrame()

    # Identificar columnas de preguntas (emociones, elementos, confianza) por noticia
    question_columns = []
    auto_counters = {"Emociones": 0, "Elementos": 0, "Confianza": 0}
    for col in form2.columns:
        slug = _normalize_question_slug(col)
        enc_id = None
        for n in ("1", "2", "3"):
            if f"noticia {n}" in slug or f"noticia{n}" in slug or slug.endswith(f" {n}"):
                enc_id = int(n)
                break

        question_type = None
        if "emocion" in slug:
            question_type = "Emociones"
        elif "elemento" in slug or "atencion" in slug:
            question_type = "Elementos"
        elif "confiabl" in slug or "confianza" in slug or "confiar" in slug:
            question_type = "Confianza"

        if question_type:
            if enc_id is None:
                auto_counters[question_type] += 1
                enc_id = auto_counters[question_type]
            question_columns.append(
                {"column": col, "enc_id": enc_id or 1, "question": question_type}
            )

    if not question_columns:
        if show_debug:
            st.warning("⚠️ No se identificaron preguntas válidas en Form2.")
            st.write("📋 Columnas disponibles:")
            for col in form2.columns:
                st.write(f"  - {col}")
        return (pd.DataFrame(), pd.DataFrame()) if show_debug else pd.DataFrame()
    
    # Iterar filas de Form2
    for _, row in form2.iterrows():
        tarjeta = str(row.get(tarjeta_col_f2, "")).strip()
        marca = row.get(marca_col_f2, None)
        
        if not tarjeta or pd.isna(marca):
            continue
        
        for match in question_columns:
            col_name = match["column"]
            if col_name not in row or pd.isna(row[col_name]):
                continue
            valor = str(row[col_name]).strip()
            if not valor:
                continue
            rows.append(
                {
                    "Taller": workshop_identifier,
                    "Marca temporal": marca,
                    "Encuadre": encuadre_map.get(match["enc_id"], match["enc_id"]),
                    "Número de tarjeta": tarjeta,
                    "Pregunta": match["question"],
                    "Valor": valor,
                }
            )
    
    if not rows:
        if show_debug:
            st.warning("⚠️ No se encontraron filas que coincidan con los patrones.")
            st.write("📊 Columnas disponibles en Form2:")
            for col in form2.columns:
                st.write(f"  - '{col}'")
        return (pd.DataFrame(), pd.DataFrame()) if show_debug else pd.DataFrame()
    
    df_long = pd.DataFrame(rows)
    
    if show_debug:
        st.success(f"✅ Formato largo creado: {len(df_long)} filas")
        st.write(f"📊 Columnas en df_long: {list(df_long.columns)}")
        st.write(f"📈 Encuadres encontrados: {df_long['Encuadre'].unique()}")
        st.write(f"📝 Preguntas encontradas: {df_long['Pregunta'].unique()}")
    
    # === 5️⃣ Agregar género desde Form1 ===
    if genero_col and not form1_base.empty:
        # Convertir tarjeta a string para hacer merge
        form1_base["tarjeta"] = form1_base["tarjeta"].astype(str).str.strip()
        df_long["Número de tarjeta"] = df_long["Número de tarjeta"].astype(str).str.strip()
        
        df_final = df_long.merge(
            form1_base[["tarjeta", "genero"]],
            left_on="Número de tarjeta",
            right_on="tarjeta",
            how="left"
        ).drop(columns=["tarjeta"])
    else:
        df_final = df_long.copy()
        df_final["genero"] = None
    
    # === 6️⃣ Ordenar y renombrar columnas ===
    column_order = ["Taller", "Marca temporal", "Encuadre", "Número de tarjeta", "genero", "Pregunta", "Valor"]
    df_final = df_final[column_order].rename(columns={"genero": "Género"})
    
    # === 7️⃣ Expandir filas con valores separados por coma ===
    if "Valor" in df_final.columns:
        # Separar por comas y eliminar espacios
        df_final["Valor"] = df_final["Valor"].astype(str).apply(
            lambda x: [v.strip() for v in x.split(",") if v.strip()]
        )
        # Explota listas en filas
        df_final = df_final.explode("Valor", ignore_index=True)
    
    if show_debug:
        return df_final, df_long
    return df_final

