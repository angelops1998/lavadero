"""Zona horaria del negocio.

En la base todo se guarda en UTC (`DateTime(timezone=True)` + `func.now()`),
pero el mostrador y el cliente piensan en hora local: un pedido recibido a las
23:10 de Bolivia es de ESE día, no del siguiente. Acá se centraliza la
conversión para que la usen los filtros de las plantillas y los reportes.
"""
from datetime import date, datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import get_settings


@lru_cache()
def zona_negocio() -> ZoneInfo:
    """Zona horaria configurada (TIMEZONE). Si el nombre no existe, UTC."""
    try:
        return ZoneInfo(get_settings().timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def a_local(valor):
    """Pasa un datetime guardado en UTC a la hora local del negocio.

    Los `date` puros (ej. `fecha_prometida`) no llevan hora: se devuelven tal
    cual. SQLite devuelve los datetimes sin zona, así que a los naive se les
    asume UTC, que es como los escribe la app."""
    if not isinstance(valor, datetime):
        return valor
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(zona_negocio())


def ahora_local() -> datetime:
    """Fecha y hora actual en la zona del negocio."""
    return datetime.now(zona_negocio())


def hoy_local() -> date:
    """El día de hoy según el reloj del negocio, no el del servidor (UTC)."""
    return ahora_local().date()
