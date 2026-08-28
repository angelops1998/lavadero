from urllib.parse import urlencode
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .config import get_settings
from .routers import (
    main as main_router,
    auth,
    consulta,
    ordenes,
    clientes,
    servicios,
    inventario,
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
        # El token tiene que existir ANTES de dibujar la página: si la cookie no
        # vino (navegador recién abierto, pestaña nueva, link de afuera), se
        # genera acá y la plantilla firma ESTE token. Antes se firmaba una cookie
        # vacía y recién después se mandaba una nueva y distinta, así que el
        # primer formulario que se guardaba tiraba 403 "Acceso denegado".
        cookie_token = request.cookies.get("csrf_token")
        token_nuevo = None if cookie_token else secrets.token_hex(32)
        request.state.csrf_token = cookie_token or token_nuevo

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
                # El 403 también deja la cookie: así el reintento ya sale bien.
                response = templates.TemplateResponse(request, "403.html", {}, status_code=403)
                if token_nuevo:
                    set_csrf_cookie(response, token_nuevo)
                return response

        response = await call_next(request)
        if token_nuevo:
            set_csrf_cookie(response, token_nuevo)
        return response


class NoCacheHTMLMiddleware(BaseHTTPMiddleware):
    """Las páginas HTML muestran datos que cambian (el estado de un pedido, el
    tablero). Sin esta cabecera el navegador se queda con la copia vieja y el
    cliente sigue viendo "Recibido" aunque en el mostrador ya se haya marcado
    "En proceso". Los estáticos no pasan por acá: los cachea nginx."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# El orden importa: se ejecutan de abajo hacia arriba, así que la cabecera se
# agrega también a las respuestas que devuelve el CSRF (ej. el 403).
app.add_middleware(CSRFMiddleware)
app.add_middleware(NoCacheHTMLMiddleware)


@app.exception_handler(NotAuthenticatedException)
async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
    # urlencode: el destino puede traer su propia query (?estado=listo) y sin
    # escapar el '&' partiría el parámetro next a la mitad.
    return RedirectResponse(url=f"/auth/login?{urlencode({'next': exc.next_url})}",
                            status_code=302)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    # Un id que no es número en la URL (/ordenes/abc) es, para el que navega,
    # una página que no existe — no un error de API en JSON crudo.
    if any((e.get("loc") or [""])[0] == "path" for e in exc.errors()):
        return templates.TemplateResponse(request, "404.html", {}, status_code=404)
    return JSONResponse({"detail": jsonable_encoder(exc.errors())}, status_code=422)


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
app.include_router(inventario.router)
app.include_router(admin.router)
app.include_router(reportes.router)
