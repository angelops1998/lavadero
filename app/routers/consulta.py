from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..templates_config import templates
from ..database import get_db
from ..models.orden import Orden
from ..utils import buscar_cliente

router = APIRouter()


@router.get("/consultar", response_class=HTMLResponse)
async def consultar(request: Request, db: Session = Depends(get_db)):
    """Pantalla PÚBLICA: el cliente busca su pedido por código o teléfono.
    Nunca se muestra la ubicación física (dato interno)."""
    codigo = (request.query_params.get("codigo") or "").strip().upper()
    telefono = (request.query_params.get("telefono") or "").strip()

    if not codigo and not telefono:
        return templates.TemplateResponse(request, "consulta/form.html", {"user": None})

    ordenes = []
    no_encontrado = False

    if codigo:
        orden = db.query(Orden).filter(Orden.codigo == codigo).first()
        if orden:
            ordenes = [orden]
        else:
            no_encontrado = True
    else:
        # Tolerante al formato: da igual si lo escribe con 591 adelante o sin él.
        cliente = buscar_cliente(db, telefono)
        if cliente:
            ordenes = [o for o in cliente.ordenes if o.estado not in ("entregado", "baja")]
            if not ordenes:
                # Tiene cliente pero sin pedidos activos → mostrar igual el más reciente.
                ordenes = cliente.ordenes[:1]
        if not ordenes:
            no_encontrado = True

    # Si algún pedido sigue en curso, la página se refresca sola: el cliente la
    # deja abierta esperando el "listo para retirar".
    pendiente = any(o.estado not in ("entregado", "baja") for o in ordenes)

    return templates.TemplateResponse(
        request,
        "consulta/resultado.html",
        {
            "user": None,
            "ordenes": ordenes,
            "no_encontrado": no_encontrado,
            "busqueda": codigo or telefono,
            "pendiente": pendiente,
        },
    )
