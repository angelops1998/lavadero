"""Reporte de ganancias: facturado por período (fecha de ingreso),
cobrado vs. pendiente, desglose diario y ranking de servicios.
Solo para admin (dato financiero)."""
from decimal import Decimal
from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..templates_config import templates
from ..fechas import a_local, hoy_local
from ..database import get_db
from ..auth import get_current_admin
from ..models.orden import Orden, OrdenItem
from ..utils import flash_from_query

router = APIRouter(prefix="/reportes", tags=["reportes"])


def _parse_fecha(valor, defecto: date) -> date:
    try:
        return date.fromisoformat((valor or "").strip())
    except (ValueError, AttributeError):
        return defecto


def _dec(valor) -> Decimal:
    return Decimal(str(valor or 0))


@router.get("", response_class=HTMLResponse)
async def reporte(request: Request, db: Session = Depends(get_db),
                  user=Depends(get_current_admin)):
    hoy = hoy_local()
    preset = (request.query_params.get("preset") or "").strip()
    if preset == "hoy":
        desde = hasta = hoy
    elif preset == "semana":
        desde, hasta = hoy - timedelta(days=6), hoy
    elif preset == "mes":
        desde, hasta = hoy.replace(day=1), hoy
    else:
        preset = ""
        desde = _parse_fecha(request.query_params.get("desde"), hoy.replace(day=1))
        hasta = _parse_fecha(request.query_params.get("hasta"), hoy)
    if hasta < desde:
        desde, hasta = hasta, desde

    # La base guarda UTC y el rango pedido es en días locales, así que traemos
    # un día de más a cada lado (el desfase nunca llega a 24 h) y recortamos en
    # Python ya convertido a hora local. Con func.date es portable SQLite/Postgres.
    ordenes = [
        o for o in db.query(Orden)
        .filter(func.date(Orden.fecha_ingreso) >= desde - timedelta(days=1),
                func.date(Orden.fecha_ingreso) <= hasta + timedelta(days=1))
        .all()
        if o.fecha_ingreso is None or desde <= a_local(o.fecha_ingreso).date() <= hasta
    ]

    facturado = cobrado = Decimal("0")
    por_dia = {}
    for o in ordenes:
        total = _dec(o.total)
        facturado += total
        # Cobrado real = lo efectivamente abonado (incluye señas parciales).
        cobrado += min(_dec(o.monto_pagado), total)
        d = a_local(o.fecha_ingreso).date() if o.fecha_ingreso else desde
        acc = por_dia.setdefault(d, {"facturado": Decimal("0"), "pedidos": 0})
        acc["facturado"] += total
        acc["pedidos"] += 1

    pendiente = facturado - cobrado
    num_pedidos = len(ordenes)
    ticket = (facturado / num_pedidos) if num_pedidos else Decimal("0")

    # Desglose diario (más reciente arriba) con barra proporcional.
    max_dia = max((v["facturado"] for v in por_dia.values()), default=Decimal("0"))
    dias = []
    for d in sorted(por_dia, reverse=True):
        v = por_dia[d]
        pct = int(v["facturado"] / max_dia * 100) if max_dia else 0
        dias.append({"fecha": d, "facturado": v["facturado"],
                     "pedidos": v["pedidos"], "pct": pct})

    # Ranking de servicios por lo facturado en cada línea del pedido.
    ranking = []
    ids = [o.id for o in ordenes]
    if ids:
        agrup = {}
        items = db.query(OrdenItem).filter(OrdenItem.orden_id.in_(ids)).all()
        for it in items:
            g = agrup.setdefault(
                it.descripcion,
                {"subtotal": Decimal("0"), "cantidad": Decimal("0"),
                 "veces": 0, "unidad": it.unidad},
            )
            g["subtotal"] += _dec(it.subtotal)
            g["cantidad"] += _dec(it.cantidad)
            g["veces"] += 1
        top = max((g["subtotal"] for g in agrup.values()), default=Decimal("0"))
        ranking = sorted(
            ({"descripcion": k, "pct": int(v["subtotal"] / top * 100) if top else 0, **v}
             for k, v in agrup.items()),
            key=lambda r: r["subtotal"], reverse=True,
        )[:15]

    return templates.TemplateResponse(
        request, "reportes/index.html",
        {"user": user, "desde": desde, "hasta": hasta, "preset": preset,
         "facturado": facturado, "cobrado": cobrado, "pendiente": pendiente,
         "num_pedidos": num_pedidos, "ticket": ticket,
         "dias": dias, "ranking": ranking,
         "messages": flash_from_query(request)},
    )
