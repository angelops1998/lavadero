"""Inventario de la lavandería, en dos partes:

1. **Insumos**: stock de consumibles (detergente, suavizante, bolsas…). El stock
   se mueve siempre con un movimiento manual (entrada / salida / ajuste por
   conteo), así queda el historial de quién sacó qué.
2. **Custodia**: qué ropa hay físicamente en el local ahora mismo — sacado de los
   pedidos que todavía no se entregaron — y cuál lleva tanto tiempo lista que
   nadie la vino a buscar.
"""
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from urllib.parse import quote_plus
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..templates_config import templates
from ..database import get_db
from ..config import get_settings
from ..auth import get_current_user, get_current_admin
from ..models.insumo import Insumo, MovimientoInsumo, UNIDADES_INSUMO, TIPOS_MOVIMIENTO
from ..models.orden import Orden, OrdenItem
from ..utils import flash_from_query, link_whatsapp

router = APIRouter(prefix="/inventario", tags=["inventario"])

# Confirmación de cada movimiento (cada tipo tiene su propia redacción).
_MENSAJE_OK = {
    "entrada": "Entrada registrada",
    "salida": "Salida registrada",
    "ajuste": "Stock ajustado",
}

# Cómo se nombra cada unidad de los pedidos al contar ropa en custodia.
_ETIQUETA_UNIDAD = {
    "prenda": ("prenda", "prendas"),
    "kg":     ("kg", "kg"),
    "metro":  ("metro", "metros"),
    "par":    ("par", "pares"),
}


def _dec(valor, defecto="0") -> Decimal:
    try:
        return Decimal(str(valor).replace(",", ".").strip() or defecto).quantize(Decimal("0.01"))
    except (InvalidOperation, AttributeError):
        return Decimal(defecto)


def _no_neg(valor) -> Decimal:
    d = _dec(valor)
    return d if d > 0 else Decimal("0")


def _unidad(valor) -> str:
    v = (valor or "").strip().lower()
    return v if v in UNIDADES_INSUMO else "unidad"


def _fmt(cantidad, insumo) -> str:
    """Cantidad legible con la unidad del insumo: '2,5 L', '3'."""
    n = Decimal(str(cantidad or 0))
    txt = str(int(n)) if n == n.to_integral_value() else f"{n.normalize():f}".replace(".", ",")
    return f"{txt} {insumo.unidad_abrev}".strip()


def _volver(insumo_id: int, ok: str = "", err: str = "") -> RedirectResponse:
    """Redirige al detalle del insumo con un mensaje flash."""
    query = ""
    if ok:
        query = f"?ok={quote_plus(ok)}"
    elif err:
        query = f"?err={quote_plus(err)}"
    return RedirectResponse(url=f"/inventario/{insumo_id}{query}", status_code=302)


def _dias_desde(momento) -> int:
    """Días transcurridos desde una fecha/hora. Compara solo por día para no
    mezclar datetimes con y sin zona horaria (SQLite los devuelve sin zona)."""
    if not momento:
        return 0
    dia = momento.date() if hasattr(momento, "date") else momento
    return max((date.today() - dia).days, 0)


# ── Insumos ──────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    q = (request.query_params.get("q") or "").strip()
    filtro = (request.query_params.get("filtro") or "").strip()
    ver_inactivos = request.query_params.get("inactivos") == "1"

    consulta = db.query(Insumo)
    if not ver_inactivos:
        consulta = consulta.filter(Insumo.activo == True)  # noqa: E712
    if q:
        consulta = consulta.filter(Insumo.nombre.ilike(f"%{q}%"))
    todos = consulta.order_by(Insumo.nombre).all()

    reponer = [i for i in todos if i.necesita_reponer]
    valor_total = sum((i.valor for i in todos), Decimal("0"))

    return templates.TemplateResponse(
        request, "inventario/lista.html",
        {"user": user, "insumos": reponer if filtro == "reponer" else todos,
         "q": q, "filtro": filtro, "ver_inactivos": ver_inactivos,
         "num_reponer": len(reponer), "valor_total": valor_total,
         "messages": flash_from_query(request)},
    )


@router.get("/custodia", response_class=HTMLResponse)
async def custodia(request: Request, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Ropa que está en el local: qué hay y qué nadie viene a retirar."""
    dias_abandono = get_settings().dias_abandono

    # Todo lo que sigue en el local = pedidos que aún no se entregaron.
    items = (
        db.query(OrdenItem)
        .join(Orden, OrdenItem.orden_id == Orden.id)
        .filter(Orden.estado != "entregado")
        .all()
    )
    agrup = {}
    for it in items:
        clave = (it.descripcion, it.unidad)
        g = agrup.setdefault(clave, {"descripcion": it.descripcion, "unidad": it.unidad,
                                     "cantidad": Decimal("0"), "pedidos": set()})
        g["cantidad"] += Decimal(str(it.cantidad or 0))
        g["pedidos"].add(it.orden_id)
    resumen = sorted(
        ({**g, "pedidos": len(g["pedidos"])} for g in agrup.values()),
        key=lambda r: (r["pedidos"], r["cantidad"]), reverse=True,
    )

    # Totales por unidad ("18 prendas · 24 kg"): sumar todo junto sería mezclar peras con kilos.
    acumulado = {}
    for r in resumen:
        acumulado[r["unidad"]] = acumulado.get(r["unidad"], Decimal("0")) + r["cantidad"]
    totales = []
    for unidad, cantidad in acumulado.items():
        singular, plural = _ETIQUETA_UNIDAD.get(unidad, (unidad, unidad))
        totales.append({"cantidad": cantidad,
                        "label": singular if cantidad == 1 else plural})

    en_local = db.query(Orden).filter(Orden.estado != "entregado").count()
    listos = db.query(Orden).filter(Orden.estado == "listo").count()

    # Abandonados: listos hace más de N días y todavía sin retirar.
    corte = date.today() - timedelta(days=dias_abandono)
    ordenes = (
        db.query(Orden)
        .filter(Orden.estado == "listo", Orden.fecha_listo != None,  # noqa: E711
                func.date(Orden.fecha_listo) <= corte)
        .order_by(Orden.fecha_listo.asc())
        .all()
    )
    abandonados = [
        {"orden": o, "dias": _dias_desde(o.fecha_listo), "wa": link_whatsapp(o)}
        for o in ordenes
    ]

    return templates.TemplateResponse(
        request, "inventario/custodia.html",
        {"user": user, "resumen": resumen, "totales": totales,
         "en_local": en_local, "listos": listos, "abandonados": abandonados,
         "dias_abandono": dias_abandono, "messages": flash_from_query(request)},
    )


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo(request: Request, user=Depends(get_current_admin)):
    return templates.TemplateResponse(
        request, "inventario/form.html",
        {"user": user, "insumo": None, "unidades": UNIDADES_INSUMO})


@router.post("", response_class=HTMLResponse)
async def crear(request: Request, db: Session = Depends(get_db),
                user=Depends(get_current_admin)):
    form = await request.form()
    nombre = (form.get("nombre") or "").strip()
    if not nombre:
        return templates.TemplateResponse(
            request, "inventario/form.html",
            {"user": user, "insumo": None, "unidades": UNIDADES_INSUMO,
             "error": "El nombre es obligatorio."},
            status_code=422,
        )

    insumo = Insumo(
        nombre=nombre[:120],
        unidad=_unidad(form.get("unidad")),
        stock=_no_neg(form.get("stock")),
        stock_minimo=_no_neg(form.get("stock_minimo")),
        costo_unit=_no_neg(form.get("costo_unit")),
        notas=(form.get("notas") or "").strip() or None,
        activo=True,
    )
    db.add(insumo)
    db.flush()

    # El stock inicial también queda como movimiento, para que el historial cierre.
    if insumo.stock > 0:
        db.add(MovimientoInsumo(
            insumo_id=insumo.id, tipo="entrada", cantidad=insumo.stock,
            stock_resultante=insumo.stock, motivo="Stock inicial", user_id=user.id))
    db.commit()
    return _volver(insumo.id, ok="Insumo creado")


@router.get("/{insumo_id}", response_class=HTMLResponse)
async def detalle(insumo_id: int, request: Request, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    insumo = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    if not insumo:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    movimientos = (
        db.query(MovimientoInsumo)
        .filter(MovimientoInsumo.insumo_id == insumo.id)
        .order_by(MovimientoInsumo.fecha.desc(), MovimientoInsumo.id.desc())
        .limit(50)
        .all()
    )
    return templates.TemplateResponse(
        request, "inventario/detalle.html",
        {"user": user, "insumo": insumo, "movimientos": movimientos,
         "tipos": TIPOS_MOVIMIENTO, "messages": flash_from_query(request)},
    )


@router.get("/{insumo_id}/editar", response_class=HTMLResponse)
async def editar_form(insumo_id: int, request: Request, db: Session = Depends(get_db),
                      user=Depends(get_current_admin)):
    insumo = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    if not insumo:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    return templates.TemplateResponse(
        request, "inventario/form.html",
        {"user": user, "insumo": insumo, "unidades": UNIDADES_INSUMO})


@router.post("/{insumo_id}/editar", response_class=HTMLResponse)
async def editar(insumo_id: int, request: Request, db: Session = Depends(get_db),
                 user=Depends(get_current_admin)):
    insumo = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    if not insumo:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    form = await request.form()
    nombre = (form.get("nombre") or "").strip()
    if not nombre:
        return templates.TemplateResponse(
            request, "inventario/form.html",
            {"user": user, "insumo": insumo, "unidades": UNIDADES_INSUMO,
             "error": "El nombre es obligatorio."},
            status_code=422,
        )
    # El stock NO se toca acá: se cambia solo con movimientos (así queda el historial).
    insumo.nombre = nombre[:120]
    insumo.unidad = _unidad(form.get("unidad"))
    insumo.stock_minimo = _no_neg(form.get("stock_minimo"))
    insumo.costo_unit = _no_neg(form.get("costo_unit"))
    insumo.notas = (form.get("notas") or "").strip() or None
    db.commit()
    return _volver(insumo.id, ok="Insumo actualizado")


@router.post("/{insumo_id}/movimiento")
async def movimiento(insumo_id: int, request: Request, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    """Entrada (compra), salida (consumo/merma) o ajuste por conteo físico."""
    insumo = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    if not insumo:
        return RedirectResponse(url="/inventario?err=Insumo+no+encontrado", status_code=302)

    form = await request.form()
    tipo = (form.get("tipo") or "").strip()
    if tipo not in TIPOS_MOVIMIENTO:
        return _volver(insumo_id, err="Tipo de movimiento inválido.")

    cantidad = _no_neg(form.get("cantidad"))
    stock_actual = Decimal(str(insumo.stock or 0))

    if tipo == "ajuste":
        # `cantidad` es lo que se contó en el estante: el stock pasa a ser eso.
        delta = cantidad - stock_actual
        if delta == 0:
            return _volver(insumo_id, err="El conteo coincide con el stock: no hay nada que ajustar.")
    else:
        if cantidad <= 0:
            return _volver(insumo_id, err="Poné una cantidad mayor a cero.")
        if tipo == "salida" and cantidad > stock_actual:
            return _volver(insumo_id, err=(
                f"No podés sacar {_fmt(cantidad, insumo)}: quedan {_fmt(stock_actual, insumo)}. "
                f"Si el stock está mal, usá 'Ajuste por conteo'."))
        delta = cantidad if tipo == "entrada" else -cantidad

    nuevo = (stock_actual + delta).quantize(Decimal("0.01"))

    # Solo las compras registran cuánto se pagó; además refrescan el costo de referencia.
    costo_total = None
    if tipo == "entrada":
        pagado = _no_neg(form.get("costo_total"))
        if pagado > 0:
            costo_total = pagado
            insumo.costo_unit = (pagado / cantidad).quantize(Decimal("0.01"))

    insumo.stock = nuevo
    db.add(MovimientoInsumo(
        insumo_id=insumo.id,
        tipo=tipo,
        cantidad=delta,
        stock_resultante=nuevo,
        costo_total=costo_total,
        motivo=(form.get("motivo") or "").strip()[:200] or None,
        user_id=user.id,
    ))
    db.commit()

    return _volver(insumo_id, ok=f"{_MENSAJE_OK[tipo]}. Quedan {_fmt(nuevo, insumo)}.")


@router.post("/{insumo_id}/toggle")
async def toggle(insumo_id: int, db: Session = Depends(get_db),
                 user=Depends(get_current_admin)):
    insumo = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    if insumo:
        insumo.activo = not insumo.activo
        db.commit()
    return RedirectResponse(url="/inventario", status_code=302)
