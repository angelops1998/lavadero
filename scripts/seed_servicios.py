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
    ("Serv. limpieza de tapiz de sillas", "12.00", "prenda"),
    ("Almohadón sillón", "25.00", "prenda"),
    ("Boina", "20.00", "prenda"),
    ("Caminito", "15.00", "prenda"),
    ("Cobertor de edredón", "15.00", "prenda"),
    ("Cortina doble", "30.00", "prenda"),
    ("Cubrecamas delgado", "25.00", "prenda"),
    ("Cuellera", "30.00", "prenda"),
    ("Desmanchante", "10.00", "prenda"),
    ("Edredón", "40.00", "prenda"),
    ("Edredón con 2 fundas", "45.00", "prenda"),
    ("Edredón Queen/King plumas (2.5 - 3 plz)", "70.00", "prenda"),
    ("Edredón Queen/King sintético (2.5 - 3 plz)", "50.00", "prenda"),
    ("Edredón simple plumas/grueso (1 - 2 plz)", "55.00", "prenda"),
    ("Edredón simple sintético (1 - 2 plz)", "35.00", "prenda"),
    ("Frazada", "35.00", "prenda"),
    ("Funda de almohada", "5.00", "prenda"),
    ("Funda de sillón", "25.00", "prenda"),
    ("Gorra", "15.00", "prenda"),
    ("Hamaca", "35.00", "prenda"),
    ("Individuales", "5.00", "prenda"),
    ("Kilo lavado y planchado laboratorio", "25.00", "kg"),
    ("Maleta grande", "60.00", "prenda"),
    ("Maleta mediana", "50.00", "prenda"),
    ("Manta", "30.00", "prenda"),
    ("Mantel", "30.00", "prenda"),
    ("Mantel mediano", "25.00", "prenda"),
    ("Mantilla", "25.00", "prenda"),
    ("Mochila", "35.00", "prenda"),
    ("Mosquitero", "25.00", "prenda"),
    ("Pantuflas", "20.00", "par"),
    ("Peluche grande", "50.00", "prenda"),
    ("Peluche mediano", "25.00", "prenda"),
    ("Peluche pequeño", "5.00", "prenda"),
    ("Piso", "35.00", "prenda"),
    ("Piso mediano", "30.00", "prenda"),
    ("Piso pequeño", "12.00", "prenda"),
    ("Porta bebé", "60.00", "prenda"),
    ("Puff sillón", "50.00", "prenda"),
    ("Salto de baño", "25.00", "prenda"),
    ("Secado ropa por kilo", "10.00", "kg"),
    ("Sleeping", "30.00", "prenda"),
    ("Sombrero", "30.00", "prenda"),
    ("Tenis de gamuza/cuero", "40.00", "par"),
    ("Tenis de tela/sintético", "35.00", "par"),
    ("Toalla pequeña", "12.00", "prenda"),
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
