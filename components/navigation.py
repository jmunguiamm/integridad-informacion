"""Navigation utilities for pages."""


def get_navigation_context(current_page: str, page_order: list[str]) -> dict:
    """Return helper data for navigating within a linear set of pages."""
    if current_page not in page_order:
        raise ValueError(f"Página '{current_page}' no está en el flujo definido.")

    idx = page_order.index(current_page)
    prev_page = page_order[idx - 1] if idx > 0 else None
    next_page = page_order[idx + 1] if idx < len(page_order) - 1 else None

    return {
        "index": idx,
        "previous": prev_page,
        "next": next_page,
        "total": len(page_order),
    }

