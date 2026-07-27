from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_user, get_current_admin
from ..models.servicio import Servicio
from ..utils import flash_from_query

router = APIRouter(prefix="/servicios", tags=["servicios"])


UNIDADES_VALIDAS = {"prenda", "kg", "metro", "par"}


def _precio(valor) -> Decimal:
    try:
        return Decimal(str(valor).replace(",", ".").strip() or "0").quantize(Decimal("0.01"))
    except (InvalidOperation, AttributeError):
        return Decimal("0.00")


def _unidad(valor) -> str:
    v = (valor or "").strip().lower()
    return v if v in UNIDADES_VALIDAS else "prenda"


def _categoria(valor) -> str:
    v = (valor or "").strip()
    return v or "General"


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    servicios = db.query(Servicio).order_by(Servicio.activo.desc(), Servicio.nombre).all()
    grupos = {}
    for s in servicios:
        grupos.setdefault(s.categoria, []).append(s)
    categorias = [{"nombre": nombre, "servicios": items} for nombre, items in sorted(grupos.items())]
    return templates.TemplateResponse(
        request, "servicios/lista.html",
        {"user": user, "categorias": categorias, "messages": flash_from_query(request)},
    )


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo(request: Request, db: Session = Depends(get_db),
                user=Depends(get_current_admin)):
    categorias = [c[0] for c in db.query(Servicio.categoria).distinct().order_by(Servicio.categoria)]
    return templates.TemplateResponse(
        request, "servicios/form.html", {"user": user, "servicio": None, "categorias": categorias})


@router.post("", response_class=HTMLResponse)
async def crear(request: Request, nombre: str = Form(""), precio: str = Form("0"),
                unidad: str = Form("prenda"), categoria: str = Form("General"),
                db: Session = Depends(get_db), user=Depends(get_current_admin)):
    nombre = nombre.strip()
    if not nombre:
        categorias = [c[0] for c in db.query(Servicio.categoria).distinct().order_by(Servicio.categoria)]
        return templates.TemplateResponse(
            request, "servicios/form.html",
            {"user": user, "servicio": None, "categorias": categorias, "error": "El nombre es obligatorio."},
            status_code=422,
        )
    db.add(Servicio(nombre=nombre, precio=_precio(precio), unidad=_unidad(unidad),
                    categoria=_categoria(categoria), activo=True))
    db.commit()
    return RedirectResponse(url="/servicios?ok=Servicio+creado", status_code=302)


@router.get("/{servicio_id}/editar", response_class=HTMLResponse)
async def editar_form(servicio_id: int, request: Request, db: Session = Depends(get_db),
                      user=Depends(get_current_admin)):
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    categorias = [c[0] for c in db.query(Servicio.categoria).distinct().order_by(Servicio.categoria)]
    return templates.TemplateResponse(
        request, "servicios/form.html", {"user": user, "servicio": servicio, "categorias": categorias})


@router.post("/{servicio_id}/editar", response_class=HTMLResponse)
async def editar(servicio_id: int, request: Request, nombre: str = Form(""),
                 precio: str = Form("0"), unidad: str = Form("prenda"),
                 categoria: str = Form("General"),
                 db: Session = Depends(get_db), user=Depends(get_current_admin)):
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    nombre = nombre.strip()
    if not nombre:
        categorias = [c[0] for c in db.query(Servicio.categoria).distinct().order_by(Servicio.categoria)]
        return templates.TemplateResponse(
            request, "servicios/form.html",
            {"user": user, "servicio": servicio, "categorias": categorias, "error": "El nombre es obligatorio."},
            status_code=422,
        )
    servicio.nombre = nombre
    servicio.precio = _precio(precio)
    servicio.unidad = _unidad(unidad)
    servicio.categoria = _categoria(categoria)
    db.commit()
    return RedirectResponse(url="/servicios?ok=Servicio+actualizado", status_code=302)


@router.post("/{servicio_id}/toggle")
async def toggle(servicio_id: int, db: Session = Depends(get_db),
                 user=Depends(get_current_admin)):
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if servicio:
        servicio.activo = not servicio.activo
        db.commit()
    return RedirectResponse(url="/servicios", status_code=302)
