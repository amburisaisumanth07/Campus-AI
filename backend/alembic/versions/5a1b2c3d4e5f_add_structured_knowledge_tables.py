"""add_structured_knowledge_tables

Revision ID: 5a1b2c3d4e5f
Revises: 2f8b1c4e9d01
Create Date: 2026-09-12 23:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '2f8b1c4e9d01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. people table
    op.create_table(
        'people',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('designation', sa.String(length=255), nullable=True),
        sa.Column('qualification', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=100), nullable=True),
        sa.Column('profile_url', sa.String(length=1000), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_people_id'), 'people', ['id'], unique=False)
    op.create_index(op.f('ix_people_name'), 'people', ['name'], unique=False)
    op.create_index(op.f('ix_people_email'), 'people', ['email'], unique=False)

    # 2. roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), server_default='GENERAL', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_code'), 'roles', ['code'], unique=True)

    # 3. leadership table
    op.create_table(
        'leadership',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('role_code', sa.String(length=50), nullable=False),
        sa.Column('role_title', sa.String(length=255), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('term_start', sa.String(length=50), nullable=True),
        sa.Column('term_end', sa.String(length=50), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('source_title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leadership_id'), 'leadership', ['id'], unique=False)
    op.create_index(op.f('ix_leadership_person_id'), 'leadership', ['person_id'], unique=False)
    op.create_index(op.f('ix_leadership_role_code'), 'leadership', ['role_code'], unique=False)
    op.create_index(op.f('ix_leadership_is_current'), 'leadership', ['is_current'], unique=False)

    # 4. schools table
    op.create_table(
        'schools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('dean_person_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['dean_person_id'], ['people.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schools_id'), 'schools', ['id'], unique=False)
    op.create_index(op.f('ix_schools_code'), 'schools', ['code'], unique=True)

    # 5. Alter departments: add school_id and hod_person_id
    op.add_column('departments', sa.Column('school_id', sa.Integer(), nullable=True))
    op.add_column('departments', sa.Column('hod_person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_departments_school_id_schools', 'departments', 'schools', ['school_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_departments_hod_person_id_people', 'departments', 'people', ['hod_person_id'], ['id'], ondelete='SET NULL')

    # 6. programs table
    op.create_table(
        'programs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('degree_level', sa.String(length=50), server_default='UG', nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('duration_years', sa.Integer(), server_default='4', nullable=False),
        sa.Column('eligibility', sa.Text(), nullable=True),
        sa.Column('intake', sa.Integer(), nullable=True),
        sa.Column('regulations_code', sa.String(length=50), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_programs_id'), 'programs', ['id'], unique=False)
    op.create_index(op.f('ix_programs_code'), 'programs', ['code'], unique=True)
    op.create_index(op.f('ix_programs_degree_level'), 'programs', ['degree_level'], unique=False)
    op.create_index(op.f('ix_programs_department_id'), 'programs', ['department_id'], unique=False)

    # 7. Alter faculty: add person_id, experience_years, specialization, research_interests, publications
    op.add_column('faculty', sa.Column('person_id', sa.Integer(), nullable=True))
    op.add_column('faculty', sa.Column('experience_years', sa.Integer(), nullable=True))
    op.add_column('faculty', sa.Column('specialization', sa.String(length=255), nullable=True))
    op.add_column('faculty', sa.Column('research_interests', sa.Text(), nullable=True))
    op.add_column('faculty', sa.Column('publications', sa.Text(), nullable=True))
    op.create_foreign_key('fk_faculty_person_id_people', 'faculty', 'people', ['person_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_faculty_person_id'), 'faculty', ['person_id'], unique=False)

    # 8. faculty_department table
    op.create_table(
        'faculty_department',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('faculty_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['faculty_id'], ['faculty.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_faculty_dept_assoc_faculty', 'faculty_department', ['faculty_id'], unique=False)
    op.create_index('ix_faculty_dept_assoc_dept', 'faculty_department', ['department_id'], unique=False)

    # 9. committees table
    op.create_table(
        'committees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), server_default='STATUTORY', nullable=False),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('meeting_frequency', sa.String(length=100), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_committees_id'), 'committees', ['id'], unique=False)
    op.create_index(op.f('ix_committees_code'), 'committees', ['code'], unique=True)

    # 10. committee_members table
    op.create_table(
        'committee_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('committee_id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('role_in_committee', sa.String(length=100), server_default='Member', nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['committee_id'], ['committees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_committee_members_id'), 'committee_members', ['id'], unique=False)
    op.create_index(op.f('ix_committee_members_committee_id'), 'committee_members', ['committee_id'], unique=False)

    # 11. cells table
    op.create_table(
        'cells',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), server_default='STUDENT_SUPPORT', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cells_id'), 'cells', ['id'], unique=False)
    op.create_index(op.f('ix_cells_code'), 'cells', ['code'], unique=True)

    # 12. cell_coordinators table
    op.create_table(
        'cell_coordinators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cell_id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=100), server_default='Coordinator', nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['cell_id'], ['cells.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cell_coordinators_id'), 'cell_coordinators', ['id'], unique=False)

    # 13. facilities table
    op.create_table(
        'facilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), server_default='GENERAL', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('timings', sa.String(length=255), nullable=True),
        sa.Column('contact_person_id', sa.Integer(), nullable=True),
        sa.Column('rules', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['contact_person_id'], ['people.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_facilities_id'), 'facilities', ['id'], unique=False)
    op.create_index(op.f('ix_facilities_name'), 'facilities', ['name'], unique=False)

    # 14. contacts table
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('department_or_unit', sa.String(length=255), nullable=False),
        sa.Column('role_or_purpose', sa.String(length=255), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=100), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contacts_id'), 'contacts', ['id'], unique=False)

    # 15. admissions table
    op.create_table(
        'admissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=True),
        sa.Column('academic_year', sa.String(length=50), server_default='2026-2027', nullable=False),
        sa.Column('category', sa.String(length=100), server_default='GENERAL', nullable=False),
        sa.Column('eligibility_criteria', sa.Text(), nullable=False),
        sa.Column('application_process', sa.Text(), nullable=True),
        sa.Column('fee_details', sa.Text(), nullable=True),
        sa.Column('entrance_exam', sa.String(length=100), nullable=True),
        sa.Column('intake', sa.Integer(), nullable=True),
        sa.Column('scholarship_info', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admissions_id'), 'admissions', ['id'], unique=False)

    # 16. academic_rules table
    op.create_table(
        'academic_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_type', sa.String(length=100), nullable=False),
        sa.Column('regulation_code', sa.String(length=50), server_default='R20', nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('threshold_percentage', sa.Float(), nullable=True),
        sa.Column('penalties_or_remedies', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_academic_rules_id'), 'academic_rules', ['id'], unique=False)
    op.create_index(op.f('ix_academic_rules_rule_type'), 'academic_rules', ['rule_type'], unique=False)

    # 17. examination_rules table
    op.create_table(
        'examination_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_type', sa.String(length=100), nullable=False),
        sa.Column('regulation_code', sa.String(length=50), server_default='R20', nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('see_weightage', sa.Float(), nullable=True),
        sa.Column('cie_weightage', sa.Float(), nullable=True),
        sa.Column('min_pass_marks', sa.String(length=100), nullable=True),
        sa.Column('revaluation_deadline_days', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_examination_rules_id'), 'examination_rules', ['id'], unique=False)
    op.create_index(op.f('ix_examination_rules_rule_type'), 'examination_rules', ['rule_type'], unique=False)

    # 18. placement_data table
    op.create_table(
        'placement_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('academic_year', sa.String(length=50), server_default='2026-2027', nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('package_lpa', sa.Float(), nullable=True),
        sa.Column('tier_category', sa.String(length=50), nullable=True),
        sa.Column('role_title', sa.String(length=255), nullable=True),
        sa.Column('eligibility_cgpa', sa.Float(), nullable=True),
        sa.Column('eligible_branches', sa.String(length=500), nullable=True),
        sa.Column('process_details', sa.Text(), nullable=True),
        sa.Column('total_offers', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_placement_data_id'), 'placement_data', ['id'], unique=False)
    op.create_index(op.f('ix_placement_data_company_name'), 'placement_data', ['company_name'], unique=False)

    # 19. institution_history table
    op.create_table(
        'institution_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('milestone_year', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), server_default='MILESTONE', nullable=False),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_institution_history_id'), 'institution_history', ['id'], unique=False)
    op.create_index(op.f('ix_institution_history_milestone_year'), 'institution_history', ['milestone_year'], unique=False)


def downgrade() -> None:
    op.drop_table('institution_history')
    op.drop_table('placement_data')
    op.drop_table('examination_rules')
    op.drop_table('academic_rules')
    op.drop_table('admissions')
    op.drop_table('contacts')
    op.drop_table('facilities')
    op.drop_table('cell_coordinators')
    op.drop_table('cells')
    op.drop_table('committee_members')
    op.drop_table('committees')
    op.drop_table('faculty_department')
    op.drop_constraint('fk_faculty_person_id_people', 'faculty', type_='foreignkey')
    op.drop_column('faculty', 'publications')
    op.drop_column('faculty', 'research_interests')
    op.drop_column('faculty', 'specialization')
    op.drop_column('faculty', 'experience_years')
    op.drop_column('faculty', 'person_id')
    op.drop_table('programs')
    op.drop_constraint('fk_departments_hod_person_id_people', 'departments', type_='foreignkey')
    op.drop_constraint('fk_departments_school_id_schools', 'departments', type_='foreignkey')
    op.drop_column('departments', 'hod_person_id')
    op.drop_column('departments', 'school_id')
    op.drop_table('schools')
    op.drop_table('leadership')
    op.drop_table('roles')
    op.drop_table('people')
