from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..templates_config import templates
from ..database import get_db
from ..auth import authenticate_user, create_access_token, get_current_user_optional

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url="/", status_code=302)
    next_url = request.query_params.get("next", "/")
    return templates.TemplateResponse(
        request, "auth/login.html", {"next": next_url, "user": None, "hide_footer": True}
    )


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    usuario: str = Form(""),
    password: str = Form(""),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    password = password.strip()
    if not usuario.strip() or not password:
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Completá el usuario y la contraseña.", "next": next,
             "form": {"usuario": usuario}, "user": None, "hide_footer": True},
            status_code=422,
        )

    user = authenticate_user(db, usuario, password)
    if not user:
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Usuario o contraseña incorrectos.", "next": next,
             "form": {"usuario": usuario}, "user": None, "hide_footer": True},
            status_code=401,
        )
    if not user.is_active:
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Tu cuenta está desactivada.", "next": next,
             "user": None, "hide_footer": True},
            status_code=401,
        )

    token = create_access_token(data={"sub": user.usuario})
    response = RedirectResponse(url=next or "/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,  # 7 días
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response
