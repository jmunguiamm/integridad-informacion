"""Data cleaning and normalization functions."""
import pandas as pd
import streamlit as st
from .utils import get_date_column_name, normalize_date


def filter_df_by_date(df: pd.DataFrame, target_date: str) -> pd.DataFrame:
    """Filtra un DataFrame por fecha usando la columna 'Marca temporal' (primera columna)."""
    if df.empty or not target_date:
        return df

    # Obtener columna de fecha (Marca temporal) - siempre usar la primera columna si no se encuentra explícitamente
    date_col = get_date_column_name(df)
    
    # Si no hay columna de fecha, usar la primera columna (asumiendo que es la marca temporal)
    if not date_col and len(df.columns) > 0:
        date_col = df.columns[0]
    
    if not date_col:
        # Si realmente no hay columnas, retornar sin filtrar
        return df
    
    # Normalizar fechas y filtrar
    df_copy = df.copy()
    try:
        df_copy['_normalized_date'] = df_copy[date_col].apply(normalize_date)
        filtered = df_copy[df_copy['_normalized_date'] == target_date]
        
        if not filtered.empty:
            filtered = filtered.drop(columns=['_normalized_date'])
            return filtered
    except Exception:
        # Si hay error en el filtrado, retornar el DataFrame original
        return df
    
    return pd.DataFrame()


def normalize_form_data(form1: pd.DataFrame, form2: pd.DataFrame, workshop_date: str = None, show_debug: bool = False):
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
    # Filtrar por fecha si se especifica
    if workshop_date:
        if show_debug:
            st.write(f"🔍 Filtrando por fecha del taller: {workshop_date}")
            st.write(f"  - Form1 antes del filtro: {len(form1)} filas")
            st.write(f"  - Form2 antes del filtro: {len(form2)} filas")
        
        form1_filtered = filter_df_by_date(form1.copy(), workshop_date)
        form2_filtered = filter_df_by_date(form2.copy(), workshop_date)
        
        if show_debug:
            st.write(f"  - Form1 después del filtro: {len(form1_filtered)} filas")
            st.write(f"  - Form2 después del filtro: {len(form2_filtered)} filas")
            
            if form1_filtered.empty:
                st.warning("⚠️ Form1 quedó vacío después del filtrado por fecha. Verifica que la fecha coincida.")
            if form2_filtered.empty:
                st.warning("⚠️ Form2 quedó vacío después del filtrado por fecha. Verifica que la fecha coincida.")
        
        form1 = form1_filtered
        form2 = form2_filtered
    
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
    if show_debug:
        st.write("🔍 Buscando columnas en Form1...")
        st.write(f"Total columnas: {len(form1.columns)}")
    
    # Buscar columna de tarjeta
    tarjeta_col = None
    for col in form1.columns:
        col_lower = col.lower()
        if "tarjeta" in col_lower:
            tarjeta_col = col
            if show_debug:
                st.write(f"✅ Columna de tarjeta encontrada: '{col}'")
            break
    
    # Si no encuentra, buscar por otros términos
    if not tarjeta_col:
        for key in ["número", "numero", "number", "card", "asignado"]:
            for col in form1.columns:
                col_lower = col.lower()
                if key in col_lower:
                    tarjeta_col = col
                    if show_debug:
                        st.write(f"✅ Columna de tarjeta encontrada (por '{key}'): '{col}'")
                    break
            if tarjeta_col:
                break
    
    # Buscar columna de género
    genero_col = None
    for col in form1.columns:
        col_lower = col.lower()
        if "género" in col_lower or "genero" in col_lower:
            genero_col = col
            if show_debug:
                st.write(f"✅ Columna de género encontrada: '{col}'")
            break
    
    # Si no encuentra género, buscar por otros términos
    if not genero_col:
        for key in ["gender", "sexo", "identificas"]:
            for col in form1.columns:
                col_lower = col.lower()
                if key in col_lower:
                    genero_col = col
                    if show_debug:
                        st.write(f"✅ Columna de género encontrada (por '{key}'): '{col}'")
                    break
            if genero_col:
                break
    
    # Obtener columna de marca temporal
    marca_col = get_date_column_name(form1)
    
    if show_debug:
        st.write(f"📋 Columnas detectadas en Form1:")
        st.write(f"  - Tarjeta: {tarjeta_col or '❌ NO ENCONTRADA'}")
        st.write(f"  - Marca temporal: {marca_col or '❌ NO ENCONTRADA'}")
        st.write(f"  - Género: {genero_col or '❌ NO ENCONTRADA'}")
        if not marca_col:
            st.write("🔍 Primeras columnas de Form1:")
            for i, col in enumerate(form1.columns[:5], 1):
                st.write(f"  {i}. '{col}'")
    
    if not tarjeta_col or not marca_col:
        error_msg = f"No se encontraron columnas necesarias en Form1. Tarjeta: {tarjeta_col}, Marca temporal: {marca_col}"
        if show_debug:
            st.error(f"❌ {error_msg}")
            st.write("📋 Todas las columnas de Form1:")
            for i, col in enumerate(form1.columns, 1):
                st.write(f"  {i}. '{col}'")
        raise ValueError(error_msg)
    
    # Preparar base de Form1
    form1_base_cols = [marca_col, tarjeta_col]
    if genero_col:
        form1_base_cols.append(genero_col)
    
    form1_base = form1[form1_base_cols].copy()
    form1_base.columns = ["marca_temporal", "tarjeta"] + (["genero"] if genero_col else [])
    form1_base["Taller"] = workshop_date or "T_001"
    
    # === 2️⃣ Mapeo de encuadres ===
    encuadre_map = {
        1: "Desconfianza y responsabilización de actores",
        2: "Polarización social y exclusión",
        3: "Miedo y control",
    }
    
    # === 3️⃣ Patrones para identificar preguntas del Form2 ===
    patterns = [
        ("¿Qué emociones identificas en ti en reacción a la noticia? (1)", 1, "Emociones"),
        ("¿Cuáles son los elementos de este mensaje que atraen más tu atención? (1)", 1, "Elementos"),
        ("¿Qué tan confiable consideras que es la información contenida en la noticia 1?", 1, "Confianza"),
        ("¿Qué emociones identificas en ti en reacción a la noticia 2?", 2, "Emociones"),
        ("¿Cuáles son los elementos de este mensaje que atraen más tu atención? (2)", 2, "Elementos"),
        ("¿Qué tan confiable consideras que es la información contenida en la noticia 2?", 2, "Confianza"),
        ("¿Qué emociones identificas en ti en reacción a la noticia? (3)", 3, "Emociones"),
        ("¿Cuáles son los elementos de este mensaje que atraen más tu atención? (3)", 3, "Elementos"),
        ("¿Qué tan confiable consideras que es la información contenida en la noticia 3?", 3, "Confianza"),
    ]
    
    # === 4️⃣ Transformar Form2 en formato largo ===
    rows = []
    
    # Buscar columna de tarjeta y marca temporal con los nombres reales
    tarjeta_col_f2 = "Ingresa el número asignado en la tarjeta que se te dio"
    marca_col_f2 = "Marca temporal"
    
    # Iterar filas de Form2
    for _, row in form2.iterrows():
        tarjeta = str(row.get(tarjeta_col_f2, "")).strip()
        marca = row.get(marca_col_f2, None)
        
        if not tarjeta or pd.isna(marca):
            continue
        
        for pattern_text, enc_id, pregunta in patterns:
            matching_col = next((col for col in form2.columns if col.strip().lower() == pattern_text.strip().lower()), None)
            if matching_col and pd.notna(row[matching_col]) and str(row[matching_col]).strip():
                valor = str(row[matching_col]).strip()
                rows.append({
                    "Taller": workshop_date or "T_001",
                    "Marca temporal": marca,
                    "Encuadre": encuadre_map[enc_id],
                    "Número de tarjeta": tarjeta,
                    "Pregunta": pregunta,
                    "Valor": valor
                })
    
    if not rows:
        if show_debug:
            st.warning("⚠️ No se encontraron filas que coincidan con los patrones.")
            st.write("📋 Patrones buscados:")
            for pattern_text, enc_id, pregunta in patterns:
                st.write(f"  - {pattern_text} (Encuadre {enc_id}, Tipo: {pregunta})")
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

