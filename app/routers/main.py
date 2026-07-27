from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..templates_config import templates
from ..database import get_db
from ..config import get_settings
from ..auth import get_current_user_optional
from ..models.orden import Orden, ESTADOS_FLUJO
from ..models.insumo import Insumo
from ..utils import flash_from_query

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)

    # Público: pantalla de bienvenida con acceso a consulta y login.
    if not user:
        return templates.TemplateResponse(request, "home.html", {"user": None})

    # Staff: tablero con los pedidos activos agrupados por estado.
    conteos = {e: 0 for e in ESTADOS_FLUJO}
    for estado, in db.query(Orden.estado).all():
        if estado in conteos:
            conteos[estado] += 1

    activos = (
        db.query(Orden)
        .filter(Orden.estado != "entregado")
        .order_by(Orden.fecha_ingreso.desc())
        .limit(12)
        .all()
    )

    # Alerta: ropa lista que nadie retira hace más de N días.
    dias = get_settings().dias_alerta_retiro
    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    sin_retirar = (
        db.query(Orden)
        .filter(Orden.estado == "listo", Orden.fecha_listo != None,  # noqa: E711
                Orden.fecha_listo <= corte)
        .order_by(Orden.fecha_listo.asc())
        .all()
    )

    # Alerta: insumos sin stock o por debajo del mínimo (el nivel es lógica del
    # modelo, así que se filtra en Python; son pocos registros).
    insumos_bajos = [
        i for i in db.query(Insumo).filter(Insumo.activo == True)  # noqa: E712
        .order_by(Insumo.nombre).all()
        if i.necesita_reponer
    ]

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "conteos": conteos,
            "activos": activos,
            "sin_retirar": sin_retirar,
            "dias_alerta": dias,
            "insumos_bajos": insumos_bajos,
            "messages": flash_from_query(request),
        },
    )
