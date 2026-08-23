"""add draft value to chequestate enum

Revision ID: 15f79f7fe831
Revises: 8cf2b1129331
Create Date: 2026-08-24 00:14:24.491401

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15f79f7fe831'
down_revision: Union[str, Sequence[str], None] = '8cf2b1129331'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE chequestate ADD VALUE IF NOT EXISTS 'draft'")

def downgrade() -> None:
    """Downgrade schema."""
    pass
