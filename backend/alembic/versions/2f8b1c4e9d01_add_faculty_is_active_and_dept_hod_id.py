"""add_faculty_is_active_and_dept_hod_id

Revision ID: 2f8b1c4e9d01
Revises: 1e9ea3f9a382
Create Date: 2026-09-03 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f8b1c4e9d01'
down_revision: Union[str, Sequence[str], None] = '1e9ea3f9a382'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('faculty', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('departments', sa.Column('hod_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_departments_hod_id_faculty', 'departments', 'faculty', ['hod_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_departments_hod_id_faculty', 'departments', type_='foreignkey')
    op.drop_column('departments', 'hod_id')
    op.drop_column('faculty', 'is_active')
