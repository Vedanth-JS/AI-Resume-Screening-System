"""add interview scheduling fields and saved_searches table

Revision ID: b7c8d9e0f1a2
Revises: 5c9d2e7f1a3b
Create Date: 2026-08-15 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Interview Scheduling fields ──────────────────────────────────────────
    op.add_column(
        'interview_kits',
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'interview_kits',
        sa.Column('location', sa.String(255), nullable=True),
    )
    op.add_column(
        'interview_kits',
        sa.Column('meeting_link', sa.String(500), nullable=True),
    )
    op.create_index(
        'ix_interview_kits_scheduled_at',
        'interview_kits',
        ['scheduled_at'],
    )

    # ─── Saved Searches table ─────────────────────────────────────────────────
    op.create_table(
        'saved_searches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_saved_searches_id', 'saved_searches', ['id'])
    op.create_index('ix_saved_searches_org_id', 'saved_searches', ['org_id'])
    op.create_index('ix_saved_searches_user_id', 'saved_searches', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_saved_searches_user_id', table_name='saved_searches')
    op.drop_index('ix_saved_searches_org_id', table_name='saved_searches')
    op.drop_index('ix_saved_searches_id', table_name='saved_searches')
    op.drop_table('saved_searches')

    op.drop_index('ix_interview_kits_scheduled_at', table_name='interview_kits')
    op.drop_column('interview_kits', 'meeting_link')
    op.drop_column('interview_kits', 'location')
    op.drop_column('interview_kits', 'scheduled_at')
