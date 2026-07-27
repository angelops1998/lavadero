"""categoria en servicios

Revision ID: e1a2b3c4d5f6
Revises: d5f9c2a4b8e1
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5f6'
down_revision: Union[str, Sequence[str], None] = 'd5f9c2a4b8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la categoría del catálogo de servicios (ej. Lavandería, Solo planchado)."""
    with op.batch_alter_table('servicios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('categoria', sa.String(length=60),
                                      nullable=False, server_default='General'))


def downgrade() -> None:
    with op.batch_alter_table('servicios', schema=None) as batch_op:
        batch_op.drop_column('categoria')
