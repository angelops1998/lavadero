"""unidad en servicios y orden_items

Revision ID: a1b2c3d4e5f6
Revises: 5d588dc90276
Create Date: 2026-07-24 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '5d588dc90276'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la unidad de cobro (prenda/kg/metro/par)."""
    with op.batch_alter_table('servicios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unidad', sa.String(length=20),
                                      nullable=False, server_default='prenda'))
    with op.batch_alter_table('orden_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unidad', sa.String(length=20),
                                      nullable=False, server_default='prenda'))

    # Ajusta la unidad de los servicios del catálogo estándar (por nombre).
    servicios = sa.table('servicios', sa.column('nombre', sa.String), sa.column('unidad', sa.String))
    op.execute(servicios.update().where(servicios.c.nombre == 'Lavado y secado x kg').values(unidad='kg'))
    op.execute(servicios.update().where(servicios.c.nombre == 'Cortinas x metro').values(unidad='metro'))
    op.execute(servicios.update().where(servicios.c.nombre == 'Zapatillas (par)').values(unidad='par'))


def downgrade() -> None:
    with op.batch_alter_table('orden_items', schema=None) as batch_op:
        batch_op.drop_column('unidad')
    with op.batch_alter_table('servicios', schema=None) as batch_op:
        batch_op.drop_column('unidad')
