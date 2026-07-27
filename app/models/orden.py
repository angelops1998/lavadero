from decimal import Decimal
from datetime import date
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Numeric, DateTime, Date, ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


# Flujo de estados y su presentación (etiqueta, color CSS, emoji).
ESTADOS = {
    "recibido":   {"label": "Recibido",           "color": "gris",  "emoji": "📥"},
    "en_proceso": {"label": "En proceso",         "color": "ambar", "emoji": "🧺"},
    "listo":      {"label": "Listo para retirar",  "color": "verde", "emoji": "✅"},
    "entregado":  {"label": "Entregado",          "color": "apagado", "emoji": "📦"},
    # No es parte del flujo normal: es la salida para ropa abandonada que nadie
    # vino a retirar. Por eso NO está en ESTADOS_FLUJO (no aparece como botón de
    # "avanzar estado"); se llega ahí solo desde la acción explícita "dar de baja".
    "baja":       {"label": "Dado de baja",       "color": "apagado", "emoji": "🗑️"},
}
# Orden secuencial del flujo (para el botón "avanzar estado").
ESTADOS_FLUJO = ["recibido", "en_proceso", "listo", "entregado"]


class Orden(Base):
    """Un pedido/recibo de la lavandería."""
    __tablename__ = "ordenes"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(10), unique=True, index=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)

    estado = Column(String(20), nullable=False, default="recibido")
    # Servicio express (prioridad / entrega urgente).
    express = Column(Boolean, nullable=False, default=False, server_default="0")

    # Dinero. `total` = lo que paga el cliente = subtotales + recargo − descuento.
    total = Column(Numeric(10, 2), nullable=False, default=0)
    descuento = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    recargo = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    ajuste_motivo = Column(String(200), nullable=True)

    # Pagos: `monto_pagado` admite señas / pagos parciales. `pagado` queda
    # sincronizado (True cuando se saldó todo) por compatibilidad con reportes.
    pagado = Column(Boolean, default=False, nullable=False)
    monto_pagado = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")

    notas = Column(Text, nullable=True)

    fecha_ingreso = Column(DateTime(timezone=True), server_default=func.now())
    fecha_prometida = Column(Date, nullable=True)   # cuándo se prometió tenerlo listo
    fecha_listo = Column(DateTime(timezone=True), nullable=True)
    fecha_entrega = Column(DateTime(timezone=True), nullable=True)
    # Cuándo y por qué se dio de baja la ropa abandonada (estado='baja').
    fecha_baja = Column(DateTime(timezone=True), nullable=True)
    baja_motivo = Column(String(200), nullable=True)

    creado_por = Column(Integer, ForeignKey("users.id"), nullable=True)

    cliente = relationship("Cliente", back_populates="ordenes")
    creador = relationship("User")
    items = relationship(
        "OrdenItem",
        back_populates="orden",
        cascade="all, delete-orphan",
        order_by="OrdenItem.id",
    )

    @property
    def estado_info(self) -> dict:
        return ESTADOS.get(self.estado, {"label": self.estado, "color": "gris", "emoji": ""})

    @property
    def subtotal_items(self) -> Decimal:
        """Suma de las líneas, antes de descuento/recargo."""
        return sum((Decimal(str(it.subtotal or 0)) for it in self.items), Decimal("0"))

    @property
    def saldo(self) -> Decimal:
        """Lo que falta cobrar (total − abonado)."""
        s = Decimal(str(self.total or 0)) - Decimal(str(self.monto_pagado or 0))
        return s if s > 0 else Decimal("0")

    @property
    def pago_parcial(self) -> bool:
        """Tiene una seña pero todavía no está saldado."""
        return not self.pagado and Decimal(str(self.monto_pagado or 0)) > 0

    @property
    def atrasado(self) -> bool:
        """La fecha prometida ya pasó y el pedido aún no se entregó (ni se dio de baja)."""
        return bool(self.fecha_prometida) and self.estado not in ("entregado", "baja") \
            and self.fecha_prometida < date.today()

    @property
    def dado_de_baja(self) -> bool:
        return self.estado == "baja"


class OrdenItem(Base):
    """Una línea del pedido: prenda/servicio, cantidad, precio y subtotal."""
    __tablename__ = "orden_items"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"), nullable=False)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=True)
    descripcion = Column(String(200), nullable=False)
    cantidad = Column(Numeric(10, 2), nullable=False, default=1)
    # Unidad con la que se cobró esta línea (queda fija aunque cambie el catálogo).
    unidad = Column(String(20), nullable=False, default="prenda", server_default="prenda")
    precio_unit = Column(Numeric(10, 2), nullable=False, default=0)
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)

    orden = relationship("Orden", back_populates="items")
