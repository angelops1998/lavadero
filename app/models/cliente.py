from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Cliente(Base):
    """Cliente de la lavandería. No tiene login: es solo un registro de contacto."""
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    telefono = Column(String(30), unique=True, index=True, nullable=False)
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ordenes = relationship(
        "Orden", back_populates="cliente", order_by="desc(Orden.fecha_ingreso)"
    )
