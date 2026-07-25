from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    """Personal de la lavandería (encargado / admin). Los clientes NO usan esta tabla."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    usuario = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False, default="encargado")  # encargado | admin
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def es_admin(self) -> bool:
        return self.rol == "admin"
