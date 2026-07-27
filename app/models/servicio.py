from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime
from sqlalchemy.sql import func
from ..database import Base


class Servicio(Base):
    """Ítem del catálogo con su precio (ej. 'Lavado y secado x kg', 'Planchado camisa')."""
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    precio = Column(Numeric(10, 2), nullable=False, default=0)
    # Unidad de cobro: 'prenda' (por pieza), 'kg' (por peso), 'metro', 'par'.
    unidad = Column(String(20), nullable=False, default="prenda", server_default="prenda")
    # Categoría del catálogo (ej. 'Lavandería', 'Solo planchado'). Libre, sin tabla aparte.
    categoria = Column(String(60), nullable=False, default="General", server_default="General")
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
