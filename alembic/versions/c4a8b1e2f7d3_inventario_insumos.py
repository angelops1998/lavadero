"""inventario de insumos (stock + movimientos)

Revision ID: c4a8b1e2f7d3
Revises: 9a71d7da52bd
Create Date: 2026-07-26 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4a8b1e2f7d3'
down_revision: Union[str, Sequence[str], None] = '9a71d7da52bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insumos consumibles y el historial de movimientos de su stock."""
    op.create_table(
        'insumos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=120), nullable=False),
        sa.Column('unidad', sa.String(length=20), nullable=False, server_default='unidad'),
        sa.Column('stock', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('stock_minimo', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('costo_unit', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_insumos_id'), 'insumos', ['id'], unique=False)

    op.create_table(
        'movimientos_insumo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('insumo_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('cantidad', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('stock_resultante', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('costo_total', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('motivo', sa.String(length=200), nullable=True),
        sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['insumo_id'], ['insumos.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_movimientos_insumo_id'), 'movimientos_insumo', ['id'], unique=False)
    op.create_index(op.f('ix_movimientos_insumo_insumo_id'), 'movimientos_insumo',
                    ['insumo_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_movimientos_insumo_insumo_id'), table_name='movimientos_insumo')
    op.drop_index(op.f('ix_movimientos_insumo_id'), table_name='movimientos_insumo')
    op.drop_table('movimientos_insumo')
    op.drop_index(op.f('ix_insumos_id'), table_name='insumos')
    op.drop_table('insumos')
