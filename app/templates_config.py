from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from decimal import Decimal
import hmac
import hashlib

templates = Jinja2Templates(directory="app/templates")


def _csrf_input(request) -> Markup:
    from .config import get_settings
    cookie_token = request.cookies.get("csrf_token", "")
    signed = hmac.new(
        get_settings().secret_key.encode(), cookie_token.encode(), hashlib.sha256
    ).hexdigest()
    return Markup(f'<input type="hidden" name="csrf_token" value="{signed}">')


def bs_filter(value) -> str:
    """Formatea un monto como 'Bs 1.234,50' (estilo boliviano)."""
    if value is None:
        value = 0
    try:
        n = Decimal(str(value))
    except Exception:
        n = Decimal(0)
    entero, _, dec = f"{n:,.2f}".partition(".")
    # f-string usa coma para miles y punto para decimales → invertir a es-BO
    entero = entero.replace(",", ".")
    return f"Bs {entero},{dec}"


def cantidad_filter(value) -> str:
    """Muestra la cantidad sin decimales si es entera (2 en vez de 2,00)."""
    try:
        n = Decimal(str(value))
    except Exception:
        return str(value)
    if n == n.to_integral_value():
        return str(int(n))
    return f"{n.normalize():f}".replace(".", ",")


_UNIDAD_ABREV = {"kg": "kg", "metro": "m", "par": "par", "prenda": ""}


def unidad_filter(value) -> str:
    """Abreviatura de la unidad para mostrar junto a la cantidad ('' para prenda)."""
    return _UNIDAD_ABREV.get((value or "").strip().lower(), "")


_MESES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def fecha_filter(value) -> str:
    """Formatea una fecha como '23 jul 2026'."""
    if value is None:
        return ""
    return f"{value.day} {_MESES[value.month][:3]} {value.year}"


def fechahora_filter(value) -> str:
    """Formatea fecha y hora como '23 jul 2026, 14:35'."""
    if value is None:
        return ""
    return f"{value.day} {_MESES[value.month][:3]} {value.year}, {value.strftime('%H:%M')}"


templates.env.globals["csrf_input"] = _csrf_input
templates.env.filters["bs"] = bs_filter
templates.env.filters["cantidad"] = cantidad_filter
templates.env.filters["unidad"] = unidad_filter
templates.env.filters["fecha"] = fecha_filter
templates.env.filters["fechahora"] = fechahora_filter
