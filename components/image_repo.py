import os
import random

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
