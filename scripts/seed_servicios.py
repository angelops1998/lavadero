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

# (categoria, nombre, precio, unidad)  unidad ∈ prenda | kg | metro | par
CATALOGO = [
    ("Lavandería", "Serv. limpieza de tapiz de sillas", "12.00", "prenda"),
    ("Lavandería", "Almohadón sillón", "25.00", "prenda"),
    ("Lavandería", "Boina", "20.00", "prenda"),
    ("Lavandería", "Caminito", "15.00", "prenda"),
    ("Lavandería", "Cobertor de edredón", "15.00", "prenda"),
    ("Lavandería", "Cortina doble", "30.00", "prenda"),
    ("Lavandería", "Cubrecamas delgado", "25.00", "prenda"),
    ("Lavandería", "Cuellera", "30.00", "prenda"),
    ("Lavandería", "Desmanchante", "10.00", "prenda"),
    ("Lavandería", "Edredón", "40.00", "prenda"),
    ("Lavandería", "Edredón con 2 fundas", "45.00", "prenda"),
    ("Lavandería", "Edredón Queen/King plumas (2.5 - 3 plz)", "70.00", "prenda"),
    ("Lavandería", "Edredón Queen/King sintético (2.5 - 3 plz)", "50.00", "prenda"),
    ("Lavandería", "Edredón simple plumas/grueso (1 - 2 plz)", "55.00", "prenda"),
    ("Lavandería", "Edredón simple sintético (1 - 2 plz)", "35.00", "prenda"),
    ("Lavandería", "Frazada", "35.00", "prenda"),
    ("Lavandería", "Funda de almohada", "5.00", "prenda"),
    ("Lavandería", "Funda de sillón", "25.00", "prenda"),
    ("Lavandería", "Gorra", "15.00", "prenda"),
    ("Lavandería", "Hamaca", "35.00", "prenda"),
    ("Lavandería", "Individuales", "5.00", "prenda"),
    ("Lavandería", "Kilo lavado y planchado laboratorio", "25.00", "kg"),
    ("Lavandería", "Maleta grande", "60.00", "prenda"),
    ("Lavandería", "Maleta mediana", "50.00", "prenda"),
    ("Lavandería", "Manta", "30.00", "prenda"),
    ("Lavandería", "Mantel", "30.00", "prenda"),
    ("Lavandería", "Mantel mediano", "25.00", "prenda"),
    ("Lavandería", "Mantilla", "25.00", "prenda"),
    ("Lavandería", "Mochila", "35.00", "prenda"),
    ("Lavandería", "Mosquitero", "25.00", "prenda"),
    ("Lavandería", "Pantuflas", "20.00", "par"),
    ("Lavandería", "Peluche grande", "50.00", "prenda"),
    ("Lavandería", "Peluche mediano", "25.00", "prenda"),
    ("Lavandería", "Peluche pequeño", "5.00", "prenda"),
    ("Lavandería", "Piso", "35.00", "prenda"),
    ("Lavandería", "Piso mediano", "30.00", "prenda"),
    ("Lavandería", "Piso pequeño", "12.00", "prenda"),
    ("Lavandería", "Porta bebé", "60.00", "prenda"),
    ("Lavandería", "Puff sillón", "50.00", "prenda"),
    ("Lavandería", "Salto de baño", "25.00", "prenda"),
    ("Lavandería", "Secado ropa por kilo", "10.00", "kg"),
    ("Lavandería", "Sleeping", "30.00", "prenda"),
    ("Lavandería", "Sombrero", "30.00", "prenda"),
    ("Lavandería", "Tenis de gamuza/cuero", "40.00", "par"),
    ("Lavandería", "Tenis de tela/sintético", "35.00", "par"),
    ("Lavandería", "Toalla pequeña", "12.00", "prenda"),
]


def main():
    db = SessionLocal()
    creados = 0
    try:
        for categoria, nombre, precio, unidad in CATALOGO:
            servicio = db.query(Servicio).filter(Servicio.nombre == nombre).first()
            if servicio:
                if servicio.categoria != categoria:
                    servicio.categoria = categoria
                continue
            db.add(Servicio(nombre=nombre, precio=Decimal(precio), unidad=unidad,
                            categoria=categoria, activo=True))
            creados += 1
        db.commit()
        print(f"[OK] {creados} servicios agregados ({len(CATALOGO) - creados} ya existían).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
