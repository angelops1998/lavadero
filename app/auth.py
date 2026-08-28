from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from .database import get_db
from .models.user import User
from .config import get_settings

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def get_user_by_usuario(db: Session, usuario: str) -> Optional[User]:
    return db.query(User).filter(User.usuario == usuario).first()


def authenticate_user(db: Session, usuario: str, password: str) -> Optional[User]:
    user = get_user_by_usuario(db, usuario.lower().strip())
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def get_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get("access_token")


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Devuelve el usuario (staff) autenticado, o None."""
    token = get_token_from_cookie(request)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        usuario: str = payload.get("sub")
        if not usuario:
            return None
    except JWTError:
        return None
    return get_user_by_usuario(db, usuario)


class NotAuthenticatedException(Exception):
    def __init__(self, next_url: str = "/"):
        self.next_url = next_url


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Devuelve el usuario staff autenticado o redirige al login."""
    user = get_current_user_optional(request, db)
    if not user:
        # Con la query incluida: si la sesión vence mirando /reportes?desde=…,
        # volver al login no tiene que perder los filtros que había puesto.
        destino = request.url.path
        if request.url.query:
            destino = f"{destino}?{request.url.query}"
        raise NotAuthenticatedException(next_url=destino)
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user


def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Exige que el usuario sea administrador."""
    if user.rol != "admin":
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador.")
    return user
