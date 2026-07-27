from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Numeric, DateTime, ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


# Unidades en las que se compra/consume un insumo (etiqueta y abreviatura).
UNIDADES_INSUMO = {
    "unidad":  {"label": "Unidad / pieza", "abrev": "u"},
    "litro":   {"label": "Litro (L)",      "abrev": "L"},
    "kg":      {"label": "Kilo (kg)",      "abrev": "kg"},
    "paquete": {"label": "Paquete",        "abrev": "paq"},
    "caja":    {"label": "Caja",           "abrev": "caja"},
    "rollo":   {"label": "Rollo",          "abrev": "rollo"},
}

# Tipos de movimiento de stock. El stock se mueve SIEMPRE por un movimiento,
# así queda el historial de quién sacó qué y cuándo.
#   entrada → compra / reposición        (suma)
#   salida  → consumo, merma, rotura     (resta)
#   ajuste  → conteo físico: el stock pasa a ser lo que se contó (suma o resta)
TIPOS_MOVIMIENTO = {
    "entrada": {"label": "Entrada",          "emoji": "📥", "color": "verde"},
    "salida":  {"label": "Salida",           "emoji": "📤", "color": "ambar"},
    "ajuste":  {"label": "Ajuste por conteo", "emoji": "🔧", "color": "gris"},
}


class Insumo(Base):
    """Consumible de la lavandería (detergente, suavizante, bolsas, perchas…).
    El `stock` es el saldo actual; su historia está en `movimientos`."""
    __tablename__ = "insumos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    # Unidad en la que se cuenta el stock ('litro', 'kg', 'unidad'…).
    unidad = Column(String(20), nullable=False, default="unidad", server_default="unidad")

    stock = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    # Cuando el stock baja de acá se avisa en el tablero. 0 = sin aviso.
    stock_minimo = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    # Costo de referencia por unidad; se recalcula solo con cada compra.
    costo_unit = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")

    notas = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    movimientos = relationship(
        "MovimientoInsumo",
        back_populates="insumo",
        cascade="all, delete-orphan",
        order_by="desc(MovimientoInsumo.fecha), desc(MovimientoInsumo.id)",
    )

    @property
    def unidad_abrev(self) -> str:
        """Abreviatura para mostrar al lado de la cantidad ('' para unidad suelta)."""
        info = UNIDADES_INSUMO.get(self.unidad)
        abrev = info["abrev"] if info else self.unidad
        return "" if abrev == "u" else abrev

    @property
    def nivel(self) -> str:
        """'sin_stock' | 'bajo' | 'ok' — cómo está parado el insumo."""
        stock = Decimal(str(self.stock or 0))
        minimo = Decimal(str(self.stock_minimo or 0))
        if stock <= 0:
            return "sin_stock"
        if minimo > 0 and stock <= minimo:
            return "bajo"
        return "ok"

    @property
    def necesita_reponer(self) -> bool:
        return self.nivel != "ok"

    @property
    def valor(self) -> Decimal:
        """Cuánta plata hay parada en este insumo (stock × costo de referencia)."""
        return (Decimal(str(self.stock or 0))
                * Decimal(str(self.costo_unit or 0))).quantize(Decimal("0.01"))


class MovimientoInsumo(Base):
    """Un movimiento de stock. `cantidad` es la diferencia con signo
    (+ entra, − sale) y `stock_resultante` el saldo que quedó después."""
    __tablename__ = "movimientos_insumo"

    id = Column(Integer, primary_key=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)

    tipo = Column(String(20), nullable=False)
    cantidad = Column(Numeric(10, 2), nullable=False, default=0)
    stock_resultante = Column(Numeric(10, 2), nullable=False, default=0)
    # Lo que se pagó, solo en las compras (sirve para el gasto del período).
    costo_total = Column(Numeric(10, 2), nullable=True)
    motivo = Column(String(200), nullable=True)

    fecha = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    insumo = relationship("Insumo", back_populates="movimientos")
    usuario = relationship("User")

    @property
    def tipo_info(self) -> dict:
        return TIPOS_MOVIMIENTO.get(
            self.tipo, {"label": self.tipo, "emoji": "", "color": "gris"})

    @property
    def entra(self) -> bool:
        return Decimal(str(self.cantidad or 0)) > 0

    @property
    def cantidad_abs(self) -> Decimal:
        return abs(Decimal(str(self.cantidad or 0)))
