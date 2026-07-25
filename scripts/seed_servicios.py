"""Carga un catálogo inicial de servicios (solo si no existen).

Uso:
    python scripts/seed_servicios.py
"""
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.servicio import Servicio

# (nombre, precio, unidad)  unidad ∈ prenda | kg | metro | par
CATALOGO = [
    ("Lavado y secado x kg", "15.00", "kg"),
    ("Lavado en seco - saco", "35.00", "prenda"),
    ("Lavado en seco - pantalón", "25.00", "prenda"),
    ("Planchado - camisa", "8.00", "prenda"),
    ("Planchado - pantalón", "10.00", "prenda"),
    ("Edredón / cobija", "45.00", "prenda"),
    ("Frazada", "30.00", "prenda"),
    ("Cortinas x metro", "20.00", "metro"),
    ("Zapatillas (par)", "40.00", "par"),
    ("Traje completo", "60.00", "prenda"),
]


def main():
    db = SessionLocal()
    creados = 0
    try:
        for nombre, precio, unidad in CATALOGO:
            existe = db.query(Servicio).filter(Servicio.nombre == nombre).first()
            if existe:
                continue
            db.add(Servicio(nombre=nombre, precio=Decimal(precio), unidad=unidad, activo=True))
            creados += 1
        db.commit()
        print(f"[OK] {creados} servicios agregados ({len(CATALOGO) - creados} ya existían).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
