"""baja de ropa abandonada (fecha_baja, baja_motivo en ordenes)

Revision ID: d5f9c2a4b8e1
Revises: c4a8b1e2f7d3
Create Date: 2026-07-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5f9c2a4b8e1'
down_revision: Union[str, Sequence[str], None] = 'c4a8b1e2f7d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Permite marcar un pedido como 'baja' (ropa abandonada que se dejó de rastrear)."""
    with op.batch_alter_table('ordenes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fecha_baja', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('baja_motivo', sa.String(length=200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('ordenes', schema=None) as batch_op:
        batch_op.drop_column('baja_motivo')
        batch_op.drop_column('fecha_baja')
