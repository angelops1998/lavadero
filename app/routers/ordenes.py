from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_user
from ..models.orden import Orden, OrdenItem, ESTADOS, ESTADOS_FLUJO
from ..models.cliente import Cliente
from ..models.servicio import Servicio
from ..utils import generar_codigo, normalizar_telefono, link_whatsapp, flash_from_query

router = APIRouter(prefix="/ordenes", tags=["ordenes"])


def _dec(valor, defecto="0") -> Decimal:
    try:
        return Decimal(str(valor).replace(",", ".").strip() or defecto)
    except (InvalidOperation, AttributeError):
        return Decimal(defecto)


def _codigo_unico(db: Session) -> str:
    for _ in range(20):
        c = generar_codigo()
        if not db.query(Orden).filter(Orden.codigo == c).first():
            return c
    return generar_codigo(6)


def _parsear_items(form):
    """Convierte los campos repetidos del formulario en una lista de líneas."""
    descripciones = form.getlist("item_descripcion")
    cantidades = form.getlist("item_cantidad")
    precios = form.getlist("item_precio")
    servicio_ids = form.getlist("item_servicio_id")
    unidades = form.getlist("item_unidad")
    items = []
    for i, desc in enumerate(descripciones):
        desc = (desc or "").strip()
        if not desc:
            continue
        cant = _dec(cantidades[i] if i < len(cantidades) else "1", "1")
        if cant <= 0:
            cant = Decimal("1")
        precio = _dec(precios[i] if i < len(precios) else "0")
        sid = servicio_ids[i] if i < len(servicio_ids) else ""
        unidad = (unidades[i] if i < len(unidades) else "prenda") or "prenda"
        if unidad not in {"prenda", "kg", "metro", "par"}:
            unidad = "prenda"
        subtotal = (cant * precio).quantize(Decimal("0.01"))
        items.append({
            "descripcion": desc[:200],
            "cantidad": cant,
            "unidad": unidad,
            "precio_unit": precio,
            "subtotal": subtotal,
            "servicio_id": int(sid) if str(sid).isdigit() else None,
        })
    return items


def _parse_fecha(valor):
    """Convierte 'AAAA-MM-DD' del input date en un date; None si está vacío/mal."""
    try:
        return date.fromisoformat((valor or "").strip())
    except (ValueError, AttributeError):
        return None


def _no_neg(valor) -> Decimal:
    d = _dec(valor)
    return d if d > 0 else Decimal("0")


def _ajustes_y_total(form, subtotal: Decimal):
    """Lee descuento/recargo del form y calcula el total final (nunca negativo)."""
    descuento = _no_neg(form.get("descuento"))
    recargo = _no_neg(form.get("recargo"))
    total = (subtotal + recargo - descuento).quantize(Decimal("0.01"))
    if total < 0:
        total = Decimal("0")
    return descuento, recargo, total


def _monto_pagado(form, total: Decimal) -> Decimal:
    """Cuánto abonó: si marcó 'pagó todo' → total; si no, la seña (acotada al total)."""
    if form.get("pago_total") == "on":
        return total
    sena = _no_neg(form.get("sena"))
    if sena > total:
        sena = total
    return sena.quantize(Decimal("0.01"))


def _form_ctx(form):
    """Rearma el contexto del formulario para reponerlo tras un error de validación."""
    return {
        "cliente_nombre": (form.get("cliente_nombre") or "").strip(),
        "cliente_telefono": (form.get("cliente_telefono") or "").strip(),
        "notas": (form.get("notas") or "").strip(),
        "express": form.get("express") == "on",
        "descuento": (form.get("descuento") or "").strip(),
        "recargo": (form.get("recargo") or "").strip(),
        "ajuste_motivo": (form.get("ajuste_motivo") or "").strip(),
        "fecha_prometida": (form.get("fecha_prometida") or "").strip(),
        "sena": (form.get("sena") or "").strip(),
        "pago_total": form.get("pago_total") == "on",
    }


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    estado = (request.query_params.get("estado") or "").strip()
    q = (request.query_params.get("q") or "").strip()

    consulta = db.query(Orden)
    if estado in ESTADOS:
        consulta = consulta.filter(Orden.estado == estado)
    if q:
        like = f"%{q}%"
        consulta = consulta.join(Cliente).filter(
            or_(Orden.codigo.ilike(like), Cliente.nombre.ilike(like),
                Cliente.telefono.ilike(like))
        )
    ordenes = consulta.order_by(Orden.fecha_ingreso.desc()).limit(200).all()

    return templates.TemplateResponse(
        request, "ordenes/lista.html",
        {"user": user, "ordenes": ordenes, "estado_sel": estado, "q": q,
         "ESTADOS": ESTADOS, "messages": flash_from_query(request)},
    )


@router.get("/nueva", response_class=HTMLResponse)
async def nueva(request: Request, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    servicios = db.query(Servicio).filter(Servicio.activo == True).order_by(Servicio.nombre).all()
    return templates.TemplateResponse(
        request, "ordenes/form.html",
        {"user": user, "servicios": servicios, "orden": None, "form_items": []},
    )


@router.post("", response_class=HTMLResponse)
async def crear(request: Request, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    form = await request.form()
    cliente_nombre = (form.get("cliente_nombre") or "").strip()
    cliente_telefono = normalizar_telefono(form.get("cliente_telefono") or "")
    items = _parsear_items(form)

    errores = []
    if not cliente_nombre:
        errores.append("El nombre del cliente es obligatorio.")
    if not cliente_telefono:
        errores.append("El teléfono del cliente es obligatorio.")
    if not items:
        errores.append("Agregá al menos una prenda o servicio.")

    if errores:
        servicios = db.query(Servicio).filter(Servicio.activo == True).order_by(Servicio.nombre).all()
        return templates.TemplateResponse(
            request, "ordenes/form.html",
            {"user": user, "servicios": servicios, "orden": None, "errores": errores,
             "form_items": items, "form": _form_ctx(form)},
            status_code=422,
        )

    # Upsert del cliente por teléfono normalizado.
    cliente = db.query(Cliente).filter(Cliente.telefono == cliente_telefono).first()
    if cliente:
        if cliente_nombre and cliente_nombre != cliente.nombre:
            cliente.nombre = cliente_nombre
    else:
        cliente = Cliente(nombre=cliente_nombre, telefono=cliente_telefono)
        db.add(cliente)
        db.flush()

    subtotal = sum((it["subtotal"] for it in items), Decimal("0"))
    descuento, recargo, total = _ajustes_y_total(form, subtotal)
    monto_pagado = _monto_pagado(form, total)
    orden = Orden(
        codigo=_codigo_unico(db),
        cliente_id=cliente.id,
        estado="recibido",
        express=form.get("express") == "on",
        total=total,
        descuento=descuento,
        recargo=recargo,
        ajuste_motivo=(form.get("ajuste_motivo") or "").strip() or None,
        monto_pagado=monto_pagado,
        pagado=(total > 0 and monto_pagado >= total),
        fecha_prometida=_parse_fecha(form.get("fecha_prometida")),
        notas=(form.get("notas") or "").strip() or None,
        creado_por=user.id,
    )
    db.add(orden)
    db.flush()
    for it in items:
        db.add(OrdenItem(orden_id=orden.id, **it))
    db.commit()

    return RedirectResponse(url=f"/ordenes/{orden.id}?ok=Pedido+creado", status_code=302)


@router.get("/{orden_id}", response_class=HTMLResponse)
async def detalle(orden_id: int, request: Request, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if not orden:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    return templates.TemplateResponse(
        request, "ordenes/detalle.html",
        {"user": user, "orden": orden, "ESTADOS": ESTADOS, "ESTADOS_FLUJO": ESTADOS_FLUJO,
         "wa_link": link_whatsapp(orden), "messages": flash_from_query(request)},
    )


@router.get("/{orden_id}/editar", response_class=HTMLResponse)
async def editar_form(orden_id: int, request: Request, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if not orden:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    servicios = db.query(Servicio).filter(Servicio.activo == True).order_by(Servicio.nombre).all()
    form_items = [
        {"descripcion": it.descripcion, "cantidad": it.cantidad, "unidad": it.unidad,
         "precio_unit": it.precio_unit, "servicio_id": it.servicio_id}
        for it in orden.items
    ]
    return templates.TemplateResponse(
        request, "ordenes/form.html",
        {"user": user, "servicios": servicios, "orden": orden, "form_items": form_items,
         "form": {"cliente_nombre": orden.cliente.nombre,
                  "cliente_telefono": orden.cliente.telefono,
                  "notas": orden.notas or "",
                  "express": orden.express,
                  "descuento": orden.descuento or "",
                  "recargo": orden.recargo or "",
                  "ajuste_motivo": orden.ajuste_motivo or "",
                  "fecha_prometida": orden.fecha_prometida.isoformat() if orden.fecha_prometida else "",
                  "sena": orden.monto_pagado if orden.pago_parcial else "",
                  "pago_total": orden.pagado}},
    )


@router.post("/{orden_id}/editar", response_class=HTMLResponse)
async def editar(orden_id: int, request: Request, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if not orden:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)

    form = await request.form()
    cliente_nombre = (form.get("cliente_nombre") or "").strip()
    cliente_telefono = normalizar_telefono(form.get("cliente_telefono") or "")
    items = _parsear_items(form)

    errores = []
    if not cliente_nombre:
        errores.append("El nombre del cliente es obligatorio.")
    if not cliente_telefono:
        errores.append("El teléfono del cliente es obligatorio.")
    if not items:
        errores.append("Agregá al menos una prenda o servicio.")

    if errores:
        servicios = db.query(Servicio).filter(Servicio.activo == True).order_by(Servicio.nombre).all()
        return templates.TemplateResponse(
            request, "ordenes/form.html",
            {"user": user, "servicios": servicios, "orden": orden, "errores": errores,
             "form_items": items, "form": _form_ctx(form)},
            status_code=422,
        )

    # Cliente (upsert por teléfono).
    cliente = db.query(Cliente).filter(Cliente.telefono == cliente_telefono).first()
    if cliente:
        if cliente_nombre and cliente_nombre != cliente.nombre:
            cliente.nombre = cliente_nombre
    else:
        cliente = Cliente(nombre=cliente_nombre, telefono=cliente_telefono)
        db.add(cliente)
        db.flush()
    orden.cliente_id = cliente.id

    # Reemplazar líneas.
    for it in list(orden.items):
        db.delete(it)
    db.flush()
    subtotal = Decimal("0")
    for it in items:
        db.add(OrdenItem(orden_id=orden.id, **it))
        subtotal += it["subtotal"]

    descuento, recargo, total = _ajustes_y_total(form, subtotal)
    monto_pagado = _monto_pagado(form, total)
    orden.express = form.get("express") == "on"
    orden.descuento = descuento
    orden.recargo = recargo
    orden.ajuste_motivo = (form.get("ajuste_motivo") or "").strip() or None
    orden.fecha_prometida = _parse_fecha(form.get("fecha_prometida"))
    orden.notas = (form.get("notas") or "").strip() or None
    orden.total = total
    orden.monto_pagado = monto_pagado
    orden.pagado = (total > 0 and monto_pagado >= total)
    db.commit()

    return RedirectResponse(url=f"/ordenes/{orden.id}?ok=Pedido+actualizado", status_code=302)


@router.post("/{orden_id}/estado")
async def cambiar_estado(orden_id: int, request: Request, db: Session = Depends(get_db),
                         user=Depends(get_current_user)):
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if not orden:
        return RedirectResponse(url="/ordenes?err=Pedido+no+encontrado", status_code=302)
    form = await request.form()
    nuevo = (form.get("estado") or "").strip()
    if nuevo in ESTADOS:
        orden.estado = nuevo
        ahora = datetime.now(timezone.utc)
        if nuevo == "listo" and not orden.fecha_listo:
            orden.fecha_listo = ahora
        if nuevo == "entregado" and not orden.fecha_entrega:
            orden.fecha_entrega = ahora
        db.commit()
    return RedirectResponse(
        url=f"/ordenes/{orden_id}?ok=Estado+actualizado", status_code=302
    )


@router.post("/{orden_id}/pago")
async def registrar_pago(orden_id: int, request: Request, db: Session = Depends(get_db),
                         user=Depends(get_current_user)):
    """Registra un pago/seña. accion: 'agregar' (suma monto), 'saldar' (paga todo),
    'reset' (vuelve a 0)."""
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if not orden:
        return RedirectResponse(url="/ordenes?err=Pedido+no+encontrado", status_code=302)
    form = await request.form()
    accion = (form.get("accion") or "agregar").strip()
    total = Decimal(str(orden.total or 0))
    actual = Decimal(str(orden.monto_pagado or 0))

    if accion == "saldar":
        nuevo = total
    elif accion == "reset":
        nuevo = Decimal("0")
    else:
        nuevo = actual + _no_neg(form.get("monto"))

    nuevo = max(Decimal("0"), min(nuevo, total)).quantize(Decimal("0.01"))
    orden.monto_pagado = nuevo
    orden.pagado = (total > 0 and nuevo >= total)
    db.commit()
    return RedirectResponse(url=f"/ordenes/{orden_id}?ok=Pago+actualizado", status_code=302)


@router.post("/{orden_id}/eliminar")
async def eliminar(orden_id: int, request: Request, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if orden:
        db.delete(orden)
        db.commit()
    return RedirectResponse(url="/ordenes?ok=Pedido+eliminado", status_code=302)
