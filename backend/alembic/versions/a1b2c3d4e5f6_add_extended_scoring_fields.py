"""
add_extended_scoring_fields

Adds semantic_score, section_score, matched_skills, missing_skills, red_flags, xai_json
to screening_results table. All new columns are nullable (NULL for historic rows).

Revision ID: a1b2c3d4e5f6
Revises: 5c9d2e7f1a3b
Create Date: 2026-08-14 11:41:12.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '5c9d2e7f1a3b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Add extended scoring columns to screening_results ─────────────────────

    # Numeric score components not previously stored
    op.add_column(
        'screening_results',
        sa.Column('semantic_score', sa.Float(), nullable=True, comment='Cosine similarity of embeddings (0-100)')
    )
    op.add_column(
        'screening_results',
        sa.Column('section_score', sa.Float(), nullable=True, comment='Resume section completeness score (0-100)')
    )

    # Structured skill match data
    op.add_column(
        'screening_results',
        sa.Column(
            'matched_skills',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='List of JD skills found in resume'
        )
    )
    op.add_column(
        'screening_results',
        sa.Column(
            'missing_skills',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='List of required JD skills absent from resume'
        )
    )
    op.add_column(
        'screening_results',
        sa.Column(
            'red_flags',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='LLM-identified concerns about the candidate'
        )
    )

    # Full XAI reasoning JSON from generate_xai_reasoning()
    op.add_column(
        'screening_results',
        sa.Column(
            'xai_json',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Full explainable AI output: verdict, reasoning, strengths, gaps'
        )
    )

    # Index on semantic_score for ranking queries
    op.create_index(
        'ix_screening_results_semantic_score',
        'screening_results',
        ['semantic_score'],
        postgresql_ops={'semantic_score': 'DESC NULLS LAST'}
    )


def downgrade() -> None:
    op.drop_index('ix_screening_results_semantic_score', table_name='screening_results')
    op.drop_column('screening_results', 'xai_json')
    op.drop_column('screening_results', 'red_flags')
    op.drop_column('screening_results', 'missing_skills')
    op.drop_column('screening_results', 'matched_skills')
    op.drop_column('screening_results', 'section_score')
    op.drop_column('screening_results', 'semantic_score')
