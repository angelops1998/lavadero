from decimal import Decimal
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_admin, hash_password
from ..models.user import User
from ..models.cliente import Cliente
from ..models.orden import Orden
from ..utils import flash_from_query

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db),
                    user=Depends(get_current_admin)):
    total_pedidos = db.query(Orden).count()
    listos = db.query(Orden).filter(Orden.estado == "listo").count()
    en_proceso = db.query(Orden).filter(Orden.estado == "en_proceso").count()
    recibidos = db.query(Orden).filter(Orden.estado == "recibido").count()
    total_clientes = db.query(Cliente).count()

    # Lo pendiente es el saldo, no el total: si el cliente dejó una seña, esa
    # plata ya está cobrada. Así el panel dice lo mismo que /reportes.
    facturado = Decimal("0")
    pendiente = Decimal("0")
    for total, monto_pagado in db.query(Orden.total, Orden.monto_pagado).all():
        total = Decimal(str(total or 0))
        abonado = min(Decimal(str(monto_pagado or 0)), total)
        facturado += total
        pendiente += total - abonado

    return templates.TemplateResponse(
        request, "admin/dashboard.html",
        {"user": user, "total_pedidos": total_pedidos, "listos": listos,
         "en_proceso": en_proceso, "recibidos": recibidos,
         "total_clientes": total_clientes, "facturado": facturado, "pendiente": pendiente,
         "messages": flash_from_query(request)},
    )


@router.get("/usuarios", response_class=HTMLResponse)
async def usuarios(request: Request, db: Session = Depends(get_db),
                   user=Depends(get_current_admin)):
    lista = db.query(User).order_by(User.nombre).all()
    return templates.TemplateResponse(
        request, "admin/usuarios.html",
        {"user": user, "usuarios": lista, "messages": flash_from_query(request)},
    )


@router.get("/usuarios/nuevo", response_class=HTMLResponse)
async def usuario_nuevo(request: Request, user=Depends(get_current_admin)):
    return templates.TemplateResponse(
        request, "admin/usuario_form.html", {"user": user, "editar": None})


@router.post("/usuarios", response_class=HTMLResponse)
async def usuario_crear(request: Request, nombre: str = Form(""), usuario: str = Form(""),
                        password: str = Form(""), rol: str = Form("encargado"),
                        db: Session = Depends(get_db), user=Depends(get_current_admin)):
    nombre = nombre.strip()
    usuario_l = usuario.lower().strip()
    password = password.strip()
    errores = []
    if not nombre:
        errores.append("El nombre es obligatorio.")
    if len(usuario_l) < 3:
        errores.append("El usuario debe tener al menos 3 caracteres.")
    if len(password) < 6:
        errores.append("La contraseña debe tener al menos 6 caracteres.")
    if rol not in ("encargado", "admin"):
        rol = "encargado"
    if errores:
        return templates.TemplateResponse(
            request, "admin/usuario_form.html",
            {"user": user, "editar": None, "errores": errores,
             "form": {"nombre": nombre, "usuario": usuario_l, "rol": rol}},
            status_code=422,
        )
    nuevo = User(nombre=nombre, usuario=usuario_l, rol=rol,
                 hashed_password=hash_password(password), is_active=True)
    try:
        db.add(nuevo)
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request, "admin/usuario_form.html",
            {"user": user, "editar": None, "errores": ["Ese usuario ya existe."],
             "form": {"nombre": nombre, "usuario": usuario_l, "rol": rol}},
            status_code=422,
        )
    return RedirectResponse(url="/admin/usuarios?ok=Usuario+creado", status_code=302)


@router.get("/usuarios/{user_id}/editar", response_class=HTMLResponse)
async def usuario_editar_form(user_id: int, request: Request, db: Session = Depends(get_db),
                              user=Depends(get_current_admin)):
    editar = db.query(User).filter(User.id == user_id).first()
    if not editar:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    return templates.TemplateResponse(
        request, "admin/usuario_form.html", {"user": user, "editar": editar})


@router.post("/usuarios/{user_id}/editar", response_class=HTMLResponse)
async def usuario_editar(user_id: int, request: Request, nombre: str = Form(""),
                         rol: str = Form("encargado"), password: str = Form(""),
                         is_active: str = Form(""), db: Session = Depends(get_db),
                         user=Depends(get_current_admin)):
    editar = db.query(User).filter(User.id == user_id).first()
    if not editar:
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    nombre = nombre.strip()
    if not nombre:
        return templates.TemplateResponse(
            request, "admin/usuario_form.html",
            {"user": user, "editar": editar, "errores": ["El nombre es obligatorio."]},
            status_code=422,
        )
    editar.nombre = nombre
    editar.rol = rol if rol in ("encargado", "admin") else "encargado"
    editar.is_active = (is_active == "on")
    if password.strip():
        if len(password.strip()) < 6:
            return templates.TemplateResponse(
                request, "admin/usuario_form.html",
                {"user": user, "editar": editar,
                 "errores": ["La nueva contraseña debe tener al menos 6 caracteres."]},
                status_code=422,
            )
        editar.hashed_password = hash_password(password.strip())
    db.commit()
    return RedirectResponse(url="/admin/usuarios?ok=Usuario+actualizado", status_code=302)
