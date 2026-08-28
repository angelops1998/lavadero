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
    """Número local, como lo dicta el mostrador: solo dígitos, sin el '+', sin
    ceros iniciales y sin el código de país.

    El mismo cliente se anota un día como 71234567 y otro como 591 71234567; si
    se guardaran tal cual serían dos clientes distintos y la consulta pública por
    teléfono encontraría solo uno. Guardando siempre la forma corta, las dos
    maneras de escribirlo caen en el mismo registro."""
    if not telefono:
        return ""
    digitos = "".join(c for c in telefono if c.isdigit()).lstrip("0")
    cod = get_settings().codigo_pais
    # Solo se saca el prefijo si lo que queda sigue siendo un número plausible
    # (7 dígitos o más), así un local que casualmente empiece con 591 no se rompe.
    if cod and digitos.startswith(cod) and len(digitos) - len(cod) >= 7:
        digitos = digitos[len(cod):].lstrip("0")
    return digitos


def telefono_whatsapp(telefono: str) -> str:
    """Devuelve el número en formato internacional para wa.me (ej. 59171234567)."""
    digitos = normalizar_telefono(telefono)
    if not digitos:
        return ""
    return f"{get_settings().codigo_pais}{digitos}"


def buscar_cliente(db, telefono: str):
    """Busca el cliente por teléfono. Además del número ya normalizado, revisa
    los registros viejos que hayan quedado guardados con el código de país
    adelante, para no crear un duplicado del mismo cliente."""
    from .models.cliente import Cliente
    tel = normalizar_telefono(telefono)
    if not tel:
        return None
    cliente = db.query(Cliente).filter(Cliente.telefono == tel).first()
    if cliente:
        return cliente
    # Son pocos registros (una lavandería de barrio): comparar en Python alcanza.
    for c in db.query(Cliente).all():
        if normalizar_telefono(c.telefono) == tel:
            return c
    return None


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
