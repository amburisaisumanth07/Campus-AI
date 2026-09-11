"""add_website_sources_and_sync_history

Revision ID: 4c91d830ef12
Revises: 3a8f9c12b456
Create Date: 2026-08-22 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM



# revision identifiers, used by Alembic.
revision: str = '4c91d830ef12'
down_revision: Union[str, Sequence[str], None] = '3a8f9c12b456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create enums safely if not already present
    conn = op.get_bind()
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE website_source_status AS ENUM ('ACTIVE', 'IDLE', 'SYNCING', 'ERROR', 'DISABLED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE sync_status AS ENUM ('SUCCESS', 'FAILED', 'IN_PROGRESS');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE source_type AS ENUM ('MANUAL_UPLOAD', 'OFFICIAL_WEBSITE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))

    # 2. Create website_sources table
    op.create_table(
        'website_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('base_url', sa.String(length=1000), nullable=False),
        sa.Column('allowed_domains', sa.String(length=1000), nullable=False),
        sa.Column('allowed_paths', sa.String(length=1000), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sync_interval', sa.String(length=20), nullable=False, server_default='6h'),
        sa.Column('max_pages', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_successful_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', PG_ENUM('ACTIVE', 'IDLE', 'SYNCING', 'ERROR', 'DISABLED', name='website_source_status', create_type=False, _create_events=False), nullable=False, server_default='IDLE'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_website_sources_id'), 'website_sources', ['id'], unique=False)
    op.create_index(op.f('ix_website_sources_created_by_id'), 'website_sources', ['created_by_id'], unique=False)

    # 3. Create website_sync_history table
    op.create_table(
        'website_sync_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', PG_ENUM('SUCCESS', 'FAILED', 'IN_PROGRESS', name='sync_status', create_type=False, _create_events=False), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('documents_discovered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('documents_added', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('documents_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('documents_unchanged', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('documents_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['website_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_website_sync_history_id'), 'website_sync_history', ['id'], unique=False)
    op.create_index(op.f('ix_website_sync_history_source_id'), 'website_sync_history', ['source_id'], unique=False)

    # 4. Alter documents table
    op.add_column('documents', sa.Column('source_type', PG_ENUM('MANUAL_UPLOAD', 'OFFICIAL_WEBSITE', name='source_type', create_type=False, _create_events=False), nullable=False, server_default='MANUAL_UPLOAD'))
    op.add_column('documents', sa.Column('source_url', sa.String(length=1000), nullable=True))
    op.add_column('documents', sa.Column('source_hash', sa.String(length=64), nullable=True))
    op.add_column('documents', sa.Column('website_source_id', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('documents', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('documents', sa.Column('last_processed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_documents_website_source_id', 'documents', 'website_sources', ['website_source_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_documents_source_hash'), 'documents', ['source_hash'], unique=False)
    op.create_index(op.f('ix_documents_website_source_id'), 'documents', ['website_source_id'], unique=False)


def downgrade() -> None:
    op.drop_constraint('fk_documents_website_source_id', 'documents', type_='foreignkey')
    op.drop_index(op.f('ix_documents_website_source_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_source_hash'), table_name='documents')
    op.drop_column('documents', 'last_processed_at')
    op.drop_column('documents', 'last_seen_at')
    op.drop_column('documents', 'discovered_at')
    op.drop_column('documents', 'website_source_id')
    op.drop_column('documents', 'source_hash')
    op.drop_column('documents', 'source_url')
    op.drop_column('documents', 'source_type')

    op.drop_index(op.f('ix_website_sync_history_source_id'), table_name='website_sync_history')
    op.drop_index(op.f('ix_website_sync_history_id'), table_name='website_sync_history')
    op.drop_table('website_sync_history')

    op.drop_index(op.f('ix_website_sources_created_by_id'), table_name='website_sources')
    op.drop_index(op.f('ix_website_sources_id'), table_name='website_sources')
    op.drop_table('website_sources')

    op.execute(sa.text("DROP TYPE IF EXISTS source_type"))
    op.execute(sa.text("DROP TYPE IF EXISTS sync_status"))
    op.execute(sa.text("DROP TYPE IF EXISTS website_source_status"))

