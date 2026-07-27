# LavaApp — Sistema de pedidos para lavandería

Reemplaza los recibos escritos a mano por un sistema simple, **mobile-first**, donde:

- El **personal** carga cada pedido desde el celular o la PC: cliente y el detalle exacto de
  prendas/servicios (con **suma automática** del total) — lo que hoy se pierde con el recibo
  en papel.
- El pedido se puede **enviar por WhatsApp** al cliente con un toque.
- El **cliente consulta por código** (sin crear cuenta) si su ropa ya está lista para retirar.
- El **inventario** lleva el stock de los insumos y muestra qué ropa hay guardada en el local.

## Tecnologías

FastAPI · Jinja2 (server-rendered) · SQLAlchemy 2.0 · Alembic · PostgreSQL · JWT en cookie +
bcrypt · protección CSRF. Misma arquitectura que los proyectos `pami`, `consultorio` y `numisbol`.

## Puesta en marcha (desarrollo)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env      # y completá SECRET_KEY (python -c "import secrets;print(secrets.token_hex(64))")
                          # Para probar rápido sin Postgres: DATABASE_URL=sqlite:///./dev.db

.venv/bin/alembic upgrade head
.venv/bin/python scripts/crear_admin.py <usuario> <password> "<Nombre>"
.venv/bin/python scripts/seed_servicios.py     # catálogo de ejemplo (opcional)
.venv/bin/python scripts/seed_insumos.py       # insumos típicos, en stock 0 (opcional)

.venv/bin/python run.py                          # http://localhost:8000
```

## Roles

- **admin**: todo lo del encargado + gestión de **servicios/precios**, alta/edición de
  **insumos**, **reportes** y **usuarios** (`/admin`).
- **encargado**: pedidos, clientes y los **movimientos de stock** (es quien gasta los insumos).

Los **clientes no tienen cuenta**: consultan su pedido en `/consultar` con el código del recibo
(o su teléfono). Esa pantalla nunca muestra la ubicación física (es un dato interno).

## Estados de un pedido

`Recibido → En proceso → Listo para retirar → Entregado`

Al enviar el WhatsApp, si el pedido está *Listo* se agrega el aviso para que pase a retirar.

## Inventario (`/inventario`)

Son dos cosas distintas, en dos pestañas:

- **Insumos**: lo que se compra y se gasta (detergente, suavizante, bolsas, perchas…). Cada
  insumo tiene stock, unidad y un mínimo; cuando baja de ese mínimo aparece en el tablero.
  El stock **nunca se edita a mano**: se mueve con **entrada** (compra), **salida** (consumo,
  merma) o **ajuste por conteo** (el stock pasa a ser lo que se contó en el estante). Cada
  movimiento queda con fecha, cantidad, saldo resultante y quién lo hizo. Si una entrada
  registra lo que se pagó, se recalcula el costo por unidad.
- **Ropa en el local** (`/inventario/custodia`): qué prendas hay guardadas ahora mismo,
  sumadas de los pedidos que todavía no se entregaron, y el listado de la ropa que nadie
  vino a buscar hace más de `DIAS_ABANDONO` días (con botón para recordarle al cliente por
  WhatsApp). No es una tabla aparte: sale de los pedidos, así que se mantiene sola.

## Configuración del negocio (`.env`)

| Variable             | Para qué sirve                                                  |
|----------------------|-----------------------------------------------------------------|
| `NEGOCIO_NOMBRE`     | Nombre que aparece en el sitio y en el mensaje de WhatsApp      |
| `CODIGO_PAIS`        | Prefijo para armar el link de WhatsApp (Bolivia = `591`)        |
| `BASE_URL`           | URL pública para el link de consulta que va en el WhatsApp      |
| `DIAS_ALERTA_RETIRO` | Días listo sin retirar para avisar en el tablero (default `3`)  |
| `DIAS_ABANDONO`      | Días listo sin retirar para darlo por abandonado (default `30`) |
| `TICKET_ANCHO_MM`    | Ancho del papel de la impresora térmica: `58` u `80`            |

## Producción

Igual que los otros proyectos: Postgres con usuario/contraseña propios, `HTTPS_ONLY=true`,
`SECRET_KEY` nueva, detrás de nginx + gunicorn/uvicorn. Migraciones con
`alembic upgrade head`. Los archivos `.env` y `*.db` están en `.gitignore`.

## Estructura

```
app/
  main.py            FastAPI + middleware CSRF + routers
  config.py          settings (.env)
  auth.py            login del personal (JWT en cookie)
  utils.py           código de recibo, teléfono y mensaje de WhatsApp
  models/            user, cliente, servicio, orden (+ items y estados), insumo (+ movimientos)
  routers/           main, auth, consulta (público), ordenes, clientes, servicios,
                     inventario (insumos + custodia), reportes, admin
  templates/         Jinja2 (tema claro, mobile-first)
  static/            css/main.css, js/orden-form.js (suma en vivo)
scripts/             crear_admin.py, seed_servicios.py, seed_insumos.py
```
