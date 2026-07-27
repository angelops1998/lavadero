"""Carga una lista inicial de insumos típicos de lavandería (solo si no existen).

Los deja en stock 0: cada uno se carga de verdad con una entrada desde
/inventario, así queda el movimiento registrado.

Uso:
    python scripts/seed_insumos.py
"""
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.insumo import Insumo

# (nombre, unidad, stock_minimo)  unidad ∈ unidad | litro | kg | paquete | caja | rollo
INSUMOS = [
    ("Detergente en polvo",   "kg",      "5"),
    ("Detergente líquido",    "litro",   "5"),
    ("Suavizante",            "litro",   "5"),
    ("Cloro / lejía",         "litro",   "3"),
    ("Quitamanchas",          "litro",   "2"),
    ("Jabón para lavado a mano", "unidad", "3"),
    ("Almidón en aerosol",    "unidad",  "2"),
    ("Bolsas de entrega",     "unidad",  "50"),
    ("Perchas / ganchos",     "unidad",  "50"),
    ("Fundas plásticas",      "unidad",  "50"),
]


def main():
    db = SessionLocal()
    creados = 0
    try:
        for nombre, unidad, minimo in INSUMOS:
            if db.query(Insumo).filter(Insumo.nombre == nombre).first():
                continue
            db.add(Insumo(nombre=nombre, unidad=unidad,
                          stock=Decimal("0"), stock_minimo=Decimal(minimo), activo=True))
            creados += 1
        db.commit()
        print(f"[OK] {creados} insumos agregados ({len(INSUMOS) - creados} ya existían).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
