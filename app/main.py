from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .config import get_settings
from .routers import (
    main as main_router,
    auth,
    consulta,
    ordenes,
    clientes,
    servicios,
    admin,
    reportes,
)
from .auth import NotAuthenticatedException
from .csrf import set_csrf_cookie, validate_csrf
from .templates_config import templates
import secrets

settings = get_settings()

app = FastAPI(
    title=settings.negocio_nombre,
    description="Sistema de gestión de pedidos para lavandería",
    version="1.0.0",
)

# El login maneja su propio flujo; el resto de los POST exigen token CSRF.
_CSRF_EXEMPT = {"/auth/login"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path not in _CSRF_EXEMPT:
            body = await request.body()

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = receive

            from urllib.parse import parse_qs
            content_type = request.headers.get("content-type", "")
            form_token = ""
            if "application/x-www-form-urlencoded" in content_type:
                parsed = parse_qs(body.decode("utf-8", errors="replace"))
                form_token = parsed.get("csrf_token", [""])[0]
            elif "multipart/form-data" in content_type:
                import re
                decoded = body.decode("utf-8", errors="replace")
                m = re.search(r'name="csrf_token"\r\n\r\n([^\r\n]+)', decoded)
                form_token = m.group(1) if m else ""

            try:
                validate_csrf(request, form_token)
            except HTTPException:
                return templates.TemplateResponse(request, "403.html", {}, status_code=403)

        response = await call_next(request)
        if "csrf_token" not in request.cookies:
            token = secrets.token_hex(32)
            set_csrf_cookie(response, token)
        return response


app.add_middleware(CSRFMiddleware)


@app.exception_handler(NotAuthenticatedException)
async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
    return RedirectResponse(url=f"/auth/login?next={exc.next_url}", status_code=302)


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request, "403.html", {}, status_code=403)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request, "404.html", {}, status_code=404)


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(main_router.router)
app.include_router(auth.router)
app.include_router(consulta.router)
app.include_router(ordenes.router)
app.include_router(clientes.router)
app.include_router(servicios.router)
app.include_router(admin.router)
app.include_router(reportes.router)
