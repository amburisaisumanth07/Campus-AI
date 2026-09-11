"""add_mits_entity_tables

Revision ID: 3b5a8c24d678
Revises: 4c91d830ef12
Create Date: 2026-08-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b5a8c24d678'
down_revision: Union[str, Sequence[str], None] = '4c91d830ef12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create announcements table
    op.create_table(
        'announcements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='General'),
        sa.Column('published_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('document_url', sa.String(length=1000), nullable=True),
        sa.Column('source_name', sa.String(length=255), nullable=False, server_default='MITS Official Portal'),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True, server_default='200'),
        sa.Column('is_valid', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('error_reason', sa.Text(), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_announcements_id'), 'announcements', ['id'], unique=False)
    op.create_index(op.f('ix_announcements_category'), 'announcements', ['category'], unique=False)
    op.create_index(op.f('ix_announcements_published_date'), 'announcements', ['published_date'], unique=False)
    op.create_index(op.f('ix_announcements_content_hash'), 'announcements', ['content_hash'], unique=False)

    # 2. Create academic_calendar table
    op.create_table(
        'academic_calendar',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('academic_year', sa.String(length=50), nullable=False, server_default='2026-2027'),
        sa.Column('program', sa.String(length=100), nullable=False, server_default='B.Tech'),
        sa.Column('year', sa.String(length=50), nullable=True),
        sa.Column('semester', sa.String(length=50), nullable=True),
        sa.Column('event_name', sa.String(length=500), nullable=False),
        sa.Column('event_description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('document_url', sa.String(length=1000), nullable=True),
        sa.Column('source_name', sa.String(length=255), nullable=False, server_default='MITS Academic Section'),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True, server_default='200'),
        sa.Column('is_valid', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('error_reason', sa.Text(), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_academic_calendar_id'), 'academic_calendar', ['id'], unique=False)
    op.create_index(op.f('ix_academic_calendar_academic_year'), 'academic_calendar', ['academic_year'], unique=False)
    op.create_index(op.f('ix_academic_calendar_program'), 'academic_calendar', ['program'], unique=False)
    op.create_index(op.f('ix_academic_calendar_start_date'), 'academic_calendar', ['start_date'], unique=False)
    op.create_index(op.f('ix_academic_calendar_content_hash'), 'academic_calendar', ['content_hash'], unique=False)

    # 3. Create examinations table
    op.create_table(
        'examinations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('exam_type', sa.String(length=50), nullable=False, server_default='notification'),
        sa.Column('program', sa.String(length=100), nullable=True, server_default='B.Tech'),
        sa.Column('year', sa.String(length=50), nullable=True),
        sa.Column('semester', sa.String(length=50), nullable=True),
        sa.Column('published_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exam_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('document_url', sa.String(length=1000), nullable=True),
        sa.Column('source_name', sa.String(length=255), nullable=False, server_default='MITS Examination Cell'),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True, server_default='200'),
        sa.Column('is_valid', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('error_reason', sa.Text(), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_examinations_id'), 'examinations', ['id'], unique=False)
    op.create_index(op.f('ix_examinations_exam_type'), 'examinations', ['exam_type'], unique=False)
    op.create_index(op.f('ix_examinations_published_date'), 'examinations', ['published_date'], unique=False)
    op.create_index(op.f('ix_examinations_content_hash'), 'examinations', ['content_hash'], unique=False)

    # 4. Create departments table
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('school', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('hod', sa.String(length=255), nullable=True),
        sa.Column('hod_name', sa.String(length=255), nullable=True),
        sa.Column('hod_designation', sa.String(length=255), nullable=True),
        sa.Column('hod_profile_url', sa.String(length=1000), nullable=True),
        sa.Column('hod_source_url', sa.String(length=1000), nullable=True),
        sa.Column('hod_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('phone', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('faculty', sa.Text(), nullable=True),
        sa.Column('programs', sa.Text(), nullable=True),
        sa.Column('courses', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('source_hash', sa.String(length=64), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True, server_default='200'),
        sa.Column('is_valid', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('error_reason', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_departments_id'), 'departments', ['id'], unique=False)
    op.create_index(op.f('ix_departments_code'), 'departments', ['code'], unique=True)

    # 5. Create faculty table
    op.create_table(
        'faculty',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('designation', sa.String(length=255), nullable=True),
        sa.Column('qualification', sa.String(length=255), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=100), nullable=True),
        sa.Column('profile_url', sa.String(length=1000), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True, server_default='https://mits.ac.in/faculty-information'),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('is_valid', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_faculty_id'), 'faculty', ['id'], unique=False)
    op.create_index(op.f('ix_faculty_name'), 'faculty', ['name'], unique=False)
    op.create_index(op.f('ix_faculty_department'), 'faculty', ['department'], unique=False)
    op.create_index(op.f('ix_faculty_content_hash'), 'faculty', ['content_hash'], unique=False)

    # 6. Create placements table
    op.create_table(
        'placements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('job_role', sa.String(length=255), nullable=True),
        sa.Column('drive_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('eligibility', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('package_details', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('document_url', sa.String(length=1000), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_placements_id'), 'placements', ['id'], unique=False)
    op.create_index(op.f('ix_placements_company'), 'placements', ['company'], unique=False)
    op.create_index(op.f('ix_placements_drive_date'), 'placements', ['drive_date'], unique=False)

    # 7. Create college_info table
    op.create_table(
        'college_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='general'),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_college_info_id'), 'college_info', ['id'], unique=False)
    op.create_index(op.f('ix_college_info_key'), 'college_info', ['key'], unique=True)

    # 8. Create important_links table
    op.create_table(
        'important_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='portals'),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_valid', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_important_links_id'), 'important_links', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_important_links_id'), table_name='important_links')
    op.drop_table('important_links')

    op.drop_index(op.f('ix_college_info_key'), table_name='college_info')
    op.drop_index(op.f('ix_college_info_id'), table_name='college_info')
    op.drop_table('college_info')

    op.drop_index(op.f('ix_placements_drive_date'), table_name='placements')
    op.drop_index(op.f('ix_placements_company'), table_name='placements')
    op.drop_index(op.f('ix_placements_id'), table_name='placements')
    op.drop_table('placements')

    op.drop_index(op.f('ix_faculty_content_hash'), table_name='faculty')
    op.drop_index(op.f('ix_faculty_department'), table_name='faculty')
    op.drop_index(op.f('ix_faculty_name'), table_name='faculty')
    op.drop_index(op.f('ix_faculty_id'), table_name='faculty')
    op.drop_table('faculty')

    op.drop_index(op.f('ix_departments_code'), table_name='departments')
    op.drop_index(op.f('ix_departments_id'), table_name='departments')
    op.drop_table('departments')

    op.drop_index(op.f('ix_examinations_content_hash'), table_name='examinations')
    op.drop_index(op.f('ix_examinations_published_date'), table_name='examinations')
    op.drop_index(op.f('ix_examinations_exam_type'), table_name='examinations')
    op.drop_index(op.f('ix_examinations_id'), table_name='examinations')
    op.drop_table('examinations')

    op.drop_index(op.f('ix_academic_calendar_content_hash'), table_name='academic_calendar')
    op.drop_index(op.f('ix_academic_calendar_start_date'), table_name='academic_calendar')
    op.drop_index(op.f('ix_academic_calendar_program'), table_name='academic_calendar')
    op.drop_index(op.f('ix_academic_calendar_academic_year'), table_name='academic_calendar')
    op.drop_index(op.f('ix_academic_calendar_id'), table_name='academic_calendar')
    op.drop_table('academic_calendar')

    op.drop_index(op.f('ix_announcements_content_hash'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_published_date'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_category'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_id'), table_name='announcements')
    op.drop_table('announcements')
