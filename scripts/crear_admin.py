"""Crea (o actualiza) un usuario administrador de la lavandería.

Uso:
    python scripts/crear_admin.py <usuario> <password> "<Nombre Completo>"

Ejemplo:
    python scripts/crear_admin.py maria clave123 "María Pérez"

Si el usuario ya existe, lo promueve a admin y le resetea la contraseña.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User
from app.auth import hash_password


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("usuario")
    ap.add_argument("password")
    ap.add_argument("nombre")
    args = ap.parse_args()

    usuario = args.usuario.lower().strip()
    if not args.password:
        sys.exit("[ERROR] La contraseña no puede estar vacía.")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.usuario == usuario).first()
        if user:
            user.nombre = args.nombre.strip() or user.nombre
            user.rol = "admin"
            user.is_active = True
            user.hashed_password = hash_password(args.password)
            accion = "actualizado"
        else:
            user = User(
                nombre=args.nombre.strip(),
                usuario=usuario,
                rol="admin",
                is_active=True,
                hashed_password=hash_password(args.password),
            )
            db.add(user)
            accion = "creado"
        db.commit()
        print(f"[OK] Administrador '{usuario}' {accion}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
