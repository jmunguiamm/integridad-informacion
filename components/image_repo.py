import os
import random
import re
import unicodedata
import math
from datetime import datetime
from typing import Optional, Iterable

import streamlit as st

from config.secrets import read_secrets
from data.sheets import sheet_to_df


def get_images_for_dominant_theme(theme: str, folder: str = "images") -> list[str]:
    """
    Busca imágenes relacionadas con un tema dominante dentro de /images.
    Ejemplo: si theme='violencia', buscará violencia_1.*, violencia_2.*, etc.
    Devuelve hasta 3 rutas existentes o fallback si no hay coincidencias.
    """
    if not theme:
        return []

    theme = theme.lower().strip()
    valid_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp")

    if not os.path.isdir(folder):
        return []

    all_files = [f for f in os.listdir(folder) if f.lower().endswith(valid_exts)]

    # Buscar imágenes que contengan el tema en su nombre
    matching = [
        os.path.join(folder, f)
        for f in all_files
        if theme in f.lower()
    ]

    # Si hay más de 3, mezclar aleatoriamente (para que las noticias no repitan orden fijo)
    if len(matching) > 3:
        random.shuffle(matching)
        matching = matching[:3]

    # Fallback si no hay coincidencias
    if not matching:
        fallback = [
            os.path.join(folder, f"taller{i+1}.jpeg")
            for i in range(3)
            if os.path.isfile(os.path.join(folder, f"taller{i+1}.jpeg"))
        ]
        return fallback

    return matching


@st.cache_data(show_spinner=False)
def _load_image_catalog():
    sheet_id = read_secrets("IMAGES_SHEET_ID", "")
    tab = read_secrets("IMAGES_TAB", "")
    if not sheet_id or not tab:
        st.session_state.setdefault("workflow_debug_messages", []).append(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Catálogo de imágenes no disponible: falta configuración.",
                "level": "warning",
                "context": "Selección de imágenes",
                "data": {"sheet_id": bool(sheet_id), "tab": bool(tab)},
            }
        )
        return None
    try:
        df = sheet_to_df(sheet_id, tab)
        if df is not None and not df.empty:
            df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        st.session_state.setdefault("workflow_debug_messages", []).append(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "No pude cargar la tabla de imágenes.",
                "level": "error",
                "context": "Selección de imágenes",
                "data": {"error": str(e)},
            }
        )
        return None


def _split_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [t.strip().lower() for t in re.split(r"[,;/|]", value) if t.strip()]
    if isinstance(value, (list, tuple)):
        return [str(v).strip().lower() for v in value if str(v).strip()]
    return [str(value).strip().lower()]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    ascii_friendly = _strip_accents(lowered)
    return re.sub(r"[^\w]+", " ", ascii_friendly).strip()


def _tokenize(text: str) -> set[str]:
    return {token for token in _normalize_text(text).split() if token}


def _score_row(row, theme: str, story: str, encuadre: Optional[str]) -> float:
    score = 0.0
    theme_tokens = _tokenize(theme)
    story_tokens = _tokenize(story)
    combined_tokens = theme_tokens | story_tokens

    tags = _split_tags(row.get("Tags"))
    descripcion = str(row.get("Descripción") or row.get("Descripcion") or "")
    descripcion_tokens = {tok for tok in _tokenize(descripcion) if len(tok) > 3}
    contexto_tags = _split_tags(row.get("Contexto"))

    tema_col = str(row.get("Tema") or row.get("Temática") or "").lower()
    if theme and theme in tema_col:
        score += 4
    elif theme_tokens and tema_col:
        tema_tokens = _tokenize(tema_col)
        if tema_tokens & theme_tokens:
            score += 2.5

    for tag in tags:
        tag_norm = _normalize_text(tag)
        if not tag_norm:
            continue
        tag_tokens = _tokenize(tag_norm)
        if tag_norm and tag_norm in story:
            score += 4
        overlap_story = len(tag_tokens & story_tokens)
        overlap_theme = len(tag_tokens & theme_tokens)
        if overlap_story >= max(1, len(tag_tokens) // 2):
            score += 3
        elif overlap_story:
            score += 1.5
        if overlap_theme:
            score += 1.5

    if descripcion_tokens:
        overlap_desc = len(descripcion_tokens & story_tokens)
        score += min(overlap_desc * 0.8, 6)
        if theme_tokens and descripcion_tokens & theme_tokens:
            score += 2

    for ctx in contexto_tags:
        ctx_tokens = _tokenize(ctx)
        if ctx_tokens & combined_tokens:
            score += 1.5

    tiempo = str(row.get("Tiempo (Día/Noche)") or "").lower()
    if tiempo:
        tiempo_token = "noche" if "noche" in tiempo else "día" if "día" in tiempo else ""
        if tiempo_token and tiempo_token in story_tokens:
            score += 1.5

    if encuadre:
        encuadre_values = _split_tags(row.get("Encuadre"))
        encuadre_norm = _normalize_text(encuadre)
        for enc in encuadre_values:
            enc_norm = _normalize_text(enc)
            if not enc_norm:
                continue
            if enc_norm == encuadre_norm or enc_norm in encuadre_norm or encuadre_norm in enc_norm:
                score += 4
                break
            enc_tokens = _tokenize(enc_norm)
            if enc_tokens & _tokenize(encuadre):
                score += 2.5
                break

    return score


def select_image_for_story(
    theme: str,
    story_text: str,
    encuadre: Optional[str] = None,
    folder: str = "images",
    exclude_paths: Optional[Iterable[str]] = None,
    debug: bool = False,
) -> Optional[str]:
    catalog = _load_image_catalog()
    theme = (theme or "").lower()
    story = (story_text or "").lower()
    exclude = set(exclude_paths or [])

    best_path = None
    best_score = float("-inf")
    debug_entries = []
    no_catalog_reason = None

    if catalog is None:
        no_catalog_reason = "Catálogo de imágenes no disponible o sin credenciales."
    elif catalog.empty:
        no_catalog_reason = "Catálogo de imágenes vacío."
    else:
        for _, row in catalog.iterrows():
            raw_name = str(row.get("Imagen") or "").strip()
            if not raw_name:
                continue
            candidate_path = raw_name
            if not os.path.isabs(candidate_path):
                cleaned = candidate_path.lstrip("/\\")
                prefix = f"{folder.rstrip('/\\')}{os.sep}"
                if not cleaned.startswith(prefix):
                    candidate_path = os.path.join(folder, cleaned)
                else:
                    candidate_path = cleaned
            if not os.path.isfile(candidate_path):
                continue
            if candidate_path in exclude:
                continue
            score = _score_row(row, theme, story, encuadre)
            if debug:
                debug_entries.append(
                    {
                        "image": candidate_path,
                        "score": round(score, 2),
                        "row": row.to_dict(),
                    }
                )
            if score > best_score:
                best_score = score
                best_path = candidate_path

    selected_path = best_path

    if not selected_path:
        matches = [path for path in get_images_for_dominant_theme(theme, folder) if path not in exclude]
        selected_path = matches[0] if matches else None

    if debug:
        if no_catalog_reason and not debug_entries:
            debug_entries = no_catalog_reason

        if isinstance(debug_entries, list):
            for entry in debug_entries:
                entry["exists"] = os.path.isfile(entry["image"])
                entry["excluded"] = entry["image"] in exclude

        best_score_value = None
        if math.isfinite(best_score):
            best_score_value = round(best_score, 2)

        debug_log = st.session_state.setdefault("image_scoring_debug", [])
        debug_log.append(
            {
                "theme": theme,
                "encuadre": encuadre,
                "story_preview": story[:180],
                "candidates": debug_entries or "Sin candidatos válidos",
                "selected": selected_path,
                "best_score": best_score_value,
                "used_fallback": bool(selected_path) and selected_path != best_path,
            }
        )
        st.session_state["image_scoring_debug"] = debug_log[-200:]

    return selected_path
