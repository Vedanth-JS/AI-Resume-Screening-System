"""add granular scoring and detailed audit fields

Revision ID: 542d5ab8aaf7
Revises: 4e4288e747ff
Create Date: 2026-04-02 23:27:41.190505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '542d5ab8aaf7'
down_revision: Union[str, None] = '4e4288e747ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    # 1. Update screening_results
    op.add_column('screening_results', sa.Column('keyword_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('screening_results', sa.Column('skills_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('screening_results', sa.Column('experience_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('screening_results', sa.Column('education_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('screening_results', sa.Column('format_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('screening_results', sa.Column('certs_score', sa.Float(), nullable=False, server_default='0.0'))

    # 2. Update audit_logs
    op.add_column('audit_logs', sa.Column('model_version', sa.String(length=50), nullable=True))
    op.add_column('audit_logs', sa.Column('prompt_hash', sa.String(length=64), nullable=True))
    op.add_column('audit_logs', sa.Column('input_hash', sa.String(length=64), nullable=True))
    op.add_column('audit_logs', sa.Column('output_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('audit_logs', sa.Column('bias_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))


def downgrade() -> None:
    # 1. Revert audit_logs
    op.drop_column('audit_logs', 'bias_flags')
    op.drop_column('audit_logs', 'output_json')
    op.drop_column('audit_logs', 'input_hash')
    op.drop_column('audit_logs', 'prompt_hash')
    op.drop_column('audit_logs', 'model_version')

    # 2. Revert screening_results
    op.drop_column('screening_results', 'certs_score')
    op.drop_column('screening_results', 'format_score')
    op.drop_column('screening_results', 'education_score')
    op.drop_column('screening_results', 'experience_score')
    op.drop_column('screening_results', 'skills_score')
    op.drop_column('screening_results', 'keyword_score')
