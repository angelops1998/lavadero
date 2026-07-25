from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_user
from ..models.cliente import Cliente
from ..utils import normalizar_telefono, flash_from_query

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    q = (request.query_params.get("q") or "").strip()
    ver_inactivos = request.query_params.get("inactivos") == "1"
    consulta = db.query(Cliente)
    if not ver_inactivos:
        consulta = consulta.filter(Cliente.activo.is_(True))
    if q:
        like = f"%{q}%"
        consulta = consulta.filter(or_(Cliente.nombre.ilike(like),
                                       Cliente.telefono.ilike(like)))
    clientes = consulta.order_by(Cliente.nombre).limit(300).all()
    return templates.TemplateResponse(
        request, "clientes/lista.html",
        {"user": user, "clientes": clientes, "q": q, "ver_inactivos": ver_inactivos,
         "messages": flash_from_query(request)},
    )


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo(request: Request, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    return templates.TemplateResponse(
        request, "clientes/form.html", {"user": user, "cliente": None})


@router.post("", response_class=HTMLResponse)
async def crear(request: Request, nombre: str = Form(""), telefono: str = Form(""),
                notas: str = Form(""), db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    nombre = nombre.strip()
    tel = normalizar_telefono(telefono)
    if not nombre or not tel:
        return templates.TemplateResponse(
            request, "clientes/form.html",
            {"user": user, "cliente": None, "error": "Nombre y teléfono son obligatorios.",
             "form": {"nombre": nombre, "telefono": tel, "notas": notas}},
            status_code=422,
        )
    cliente = Cliente(nombre=nombre, telefono=tel, notas=notas.strip() or None)
    try:
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
    except IntegrityError:
        db.rollback()
        existente = db.query(Cliente).filter(Cliente.telefono == tel).first()
        return RedirectResponse(url=f"/clientes/{existente.id}?err=Ese+telefono+ya+existe",
                                status_code=302)
    return RedirectResponse(url=f"/clientes/{cliente.id}?ok=Cliente+creado", status_code=302)


@router.get("/{cliente_id}", response_class=HTMLResponse)
async def detalle(cliente_id: int, request: Request, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    return templates.TemplateResponse(
        request, "clientes/detalle.html",
        {"user": user, "cliente": cliente, "messages": flash_from_query(request)},
    )


@router.get("/{cliente_id}/editar", response_class=HTMLResponse)
async def editar_form(cliente_id: int, request: Request, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    return templates.TemplateResponse(
        request, "clientes/form.html", {"user": user, "cliente": cliente})


@router.post("/{cliente_id}/editar", response_class=HTMLResponse)
async def editar(cliente_id: int, request: Request, nombre: str = Form(""),
                 telefono: str = Form(""), notas: str = Form(""),
                 db: Session = Depends(get_db), user=Depends(get_current_user)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    nombre = nombre.strip()
    tel = normalizar_telefono(telefono)
    if not nombre or not tel:
        return templates.TemplateResponse(
            request, "clientes/form.html",
            {"user": user, "cliente": cliente, "error": "Nombre y teléfono son obligatorios."},
            status_code=422,
        )
    cliente.nombre = nombre
    cliente.telefono = tel
    cliente.notas = notas.strip() or None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request, "clientes/form.html",
            {"user": user, "cliente": cliente, "error": "Ese teléfono ya pertenece a otro cliente."},
            status_code=422,
        )
    return RedirectResponse(url=f"/clientes/{cliente.id}?ok=Cliente+actualizado", status_code=302)


@router.post("/{cliente_id}/desactivar", response_class=HTMLResponse)
async def desactivar(cliente_id: int, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return RedirectResponse(url="/clientes", status_code=302)
    cliente.activo = False
    db.commit()
    return RedirectResponse(url="/clientes?ok=Cliente+desactivado", status_code=302)


@router.post("/{cliente_id}/reactivar", response_class=HTMLResponse)
async def reactivar(cliente_id: int, db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return RedirectResponse(url="/clientes", status_code=302)
    cliente.activo = True
    db.commit()
    return RedirectResponse(url=f"/clientes/{cliente.id}?ok=Cliente+reactivado", status_code=302)
