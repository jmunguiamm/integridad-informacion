"""QR code generation utilities."""
from io import BytesIO


def qr_image_for(url: str):
    """Genera QR PNG de un link."""
    try:
        import qrcode
        buf = BytesIO()
        qrcode.make(url).save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None

