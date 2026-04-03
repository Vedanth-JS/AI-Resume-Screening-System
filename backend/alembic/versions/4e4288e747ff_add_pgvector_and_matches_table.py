"""add pgvector and matches table

Revision ID: 4e4288e747ff
Revises: 385d4ccd465e
Create Date: 2026-04-02 23:02:33.555301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e4288e747ff'
down_revision: Union[str, None] = '385d4ccd465e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from pgvector.sqlalchemy import Vector

def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Alter resume_embeddings table
    # Since we are changing JSON to Vector(768), we might need to handle existing data.
    # For now, we drop the column and recreate it as it's a "fresh" build.
    op.drop_column('resume_embeddings', 'embedding')
    op.add_column('resume_embeddings', sa.Column('embedding', Vector(768), nullable=False))
    op.create_index(op.f('ix_resume_embeddings_candidate_id'), 'resume_embeddings', ['candidate_id'], unique=False)

    # 3. Create job_candidate_matches table
    op.create_table('job_candidate_matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['job_postings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_candidate_matches_candidate_id'), 'job_candidate_matches', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_job_candidate_matches_job_id'), 'job_candidate_matches', ['job_id'], unique=False)
    op.create_index('ix_job_match_score', 'job_candidate_matches', [sa.text('similarity_score DESC')], unique=False)

    # 4. Add Vector Index (IVFFlat)
    # Note: lists=100 is a safe default for small-ish datasets. 
    # In production, lists should be approx. sqrt(rows).
    op.execute("CREATE INDEX ON resume_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")


def downgrade() -> None:
    op.drop_index(op.f('ix_job_candidate_matches_job_id'), table_name='job_candidate_matches')
    op.drop_index(op.f('ix_job_candidate_matches_candidate_id'), table_name='job_candidate_matches')
    op.drop_table('job_candidate_matches')
    op.drop_index(op.f('ix_resume_embeddings_candidate_id'), table_name='resume_embeddings')
    op.drop_column('resume_embeddings', 'embedding')
    op.add_column('resume_embeddings', sa.Column('embedding', sa.JSON(), nullable=False))
