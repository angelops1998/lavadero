"""Utilidades: generación de códigos de recibo, normalización de teléfono
y armado del mensaje de WhatsApp."""
import secrets
from decimal import Decimal
from urllib.parse import quote
from .config import get_settings

# Alfabeto sin caracteres ambiguos (sin O/0, I/1, etc.) para que el código
# escrito o dictado por teléfono no se confunda.
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generar_codigo(largo: int = 5) -> str:
    """Código corto aleatorio para el recibo / consulta pública."""
    return "".join(secrets.choice(_ALFABETO) for _ in range(largo))


def normalizar_telefono(telefono: str) -> str:
    """Deja solo dígitos. Quita ceros iniciales y el '+' si estuvieran."""
    if not telefono:
        return ""
    digitos = "".join(c for c in telefono if c.isdigit())
    return digitos


def telefono_whatsapp(telefono: str) -> str:
    """Devuelve el número en formato internacional para wa.me (ej. 59171234567).
    Si ya trae el código de país lo respeta; si no, lo antepone."""
    digitos = normalizar_telefono(telefono)
    if not digitos:
        return ""
    cod = get_settings().codigo_pais
    if digitos.startswith(cod):
        return digitos
    return f"{cod}{digitos}"


def _fmt_bs(value) -> str:
    n = Decimal(str(value or 0))
    entero, _, dec = f"{n:,.2f}".partition(".")
    entero = entero.replace(",", ".")
    return f"Bs {entero},{dec}"


def _fmt_cant(value) -> str:
    n = Decimal(str(value or 0))
    if n == n.to_integral_value():
        return str(int(n))
    return f"{n.normalize():f}".replace(".", ",")


_MESES = [
    "", "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]


def _fmt_fecha(value) -> str:
    if value is None:
        return ""
    return f"{value.day} {_MESES[value.month]} {value.year}"


def mensaje_whatsapp(orden) -> str:
    """Arma el texto del mensaje para el cliente a partir de una Orden."""
    from .models.orden import ESTADOS
    s = get_settings()
    est = ESTADOS.get(orden.estado, {})
    lineas = []
    lineas.append(f"Hola {orden.cliente.nombre} 👋")
    lineas.append(f"Tu pedido en *{s.negocio_nombre}*:")
    lineas.append("")
    lineas.append(f"Recibo: *{orden.codigo}*")
    lineas.append(f"Estado: {est.get('emoji', '')} {est.get('label', orden.estado)}")
    if orden.express:
        lineas.append("⚡ Servicio express")
    if orden.fecha_prometida and orden.estado != "entregado":
        lineas.append(f"🗓️ Estimado para: {_fmt_fecha(orden.fecha_prometida)}")
    lineas.append("")
    lineas.append("Detalle:")
    for it in orden.items:
        lineas.append(f"• {_fmt_cant(it.cantidad)} x {it.descripcion} — {_fmt_bs(it.subtotal)}")
    descuento = Decimal(str(orden.descuento or 0))
    recargo = Decimal(str(orden.recargo or 0))
    if descuento > 0:
        lineas.append(f"Descuento: −{_fmt_bs(descuento)}")
    if recargo > 0:
        lineas.append(f"Recargo: +{_fmt_bs(recargo)}")
    lineas.append("")
    lineas.append(f"Total: *{_fmt_bs(orden.total)}*")
    abonado = Decimal(str(orden.monto_pagado or 0))
    if orden.pagado:
        lineas.append("Pagado ✅")
    elif abonado > 0:
        lineas.append(f"Abonado: {_fmt_bs(abonado)}")
        lineas.append(f"Saldo: *{_fmt_bs(orden.saldo)}*")
    else:
        lineas.append("(pendiente de pago)")
    lineas.append("")
    if orden.estado == "listo":
        lineas.append("✅ ¡Ya podés pasar a retirar tu ropa!")
    lineas.append(f"Consultá el estado acá: {s.base_url}/consultar?codigo={orden.codigo}")
    return "\n".join(lineas)


def link_whatsapp(orden) -> str:
    """URL wa.me con el mensaje pre-cargado."""
    tel = telefono_whatsapp(orden.cliente.telefono)
    texto = quote(mensaje_whatsapp(orden))
    if tel:
        return f"https://wa.me/{tel}?text={texto}"
    return f"https://wa.me/?text={texto}"


def flash_from_query(request) -> list:
    """Lee mensajes de éxito/error de los query params (?ok=... / ?err=...)."""
    msgs = []
    ok = request.query_params.get("ok")
    err = request.query_params.get("err")
    if ok:
        msgs.append({"type": "success", "text": ok})
    if err:
        msgs.append({"type": "error", "text": err})
    return msgs
