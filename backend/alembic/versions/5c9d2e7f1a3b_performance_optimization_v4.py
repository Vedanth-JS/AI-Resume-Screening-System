"""performance_optimization_v4

Revision ID: 5c9d2e7f1a3b
Revises: 4f8a9b2c1d3e
Create Date: 2026-07-20

Comprehensive performance optimization:
- Composite indexes for multi-tenant queries
- GIN indexes on JSONB skill arrays
- Full-text search (tsvector) on job descriptions
- Materialized view for analytics dashboard
- BRIN indexes on time-series audit tables
- Batch operation table indexing
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '5c9d2e7f1a3b'
down_revision: Union[str, None] = '4f8a9b2c1d3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Create missing activity_logs table ──────────────────────────────
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_activity_logs_id', 'activity_logs', ['id'])
    op.create_index('ix_activity_logs_org_id', 'activity_logs', ['org_id'])
    op.create_index('ix_activity_logs_user_id', 'activity_logs', ['user_id'])
    op.create_index('ix_activity_entity', 'activity_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_activity_org_time', 'activity_logs', ['org_id', 'created_at'])

    # ─── 1. Composite indexes for common multi-tenant queries ─────────────
    op.create_index('ix_candidates_org_status', 'candidates',
                    ['org_id', 'status', 'deleted_at'])
    op.create_index('ix_candidates_org_email', 'candidates',
                    ['org_id', 'email'])
    op.create_index('ix_job_postings_org_status', 'job_postings',
                    ['org_id', 'status', 'deleted_at'])
    op.create_index('ix_job_postings_org_posted', 'job_postings',
                    ['org_id', 'posted_at'])
    op.create_index('ix_applications_org_status', 'applications',
                    ['org_id', 'status', 'deleted_at'])
    op.create_index('ix_applications_org_score', 'applications',
                    ['org_id', 'score'])
    op.create_index('ix_applications_job_score', 'applications',
                    ['job_id', 'score'])
    op.create_index('ix_screening_results_app_id', 'screening_results',
                    ['application_id'])
    op.create_index('ix_screening_results_job_score', 'screening_results',
                    ['job_id', 'score'])

    # Audit query indexes
    op.create_index('ix_auth_audit_org_event_time', 'auth_audit_logs',
                    ['org_id', 'event', 'created_at'])
    op.create_index('ix_audit_logs_user_action_time', 'audit_logs',
                    ['user_id', 'action', 'created_at'])

    # ─── 2. GIN indexes on JSONB arrays (skills, tags) ───────────────────
    # job_postings.required_skills is JSONB array — GIN for containment queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_job_postings_skills_gin
        ON job_postings USING gin (required_skills jsonb_path_ops)
    """)

    # candidates.parsed_json has skills array
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_candidates_skills_gin_new
        ON candidates USING gin ((parsed_json->'skills') jsonb_path_ops)
    """)

    # ─── 3. Full-text search on job descriptions ────────────────────────
    op.execute("""
        ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS description_tsv tsvector
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_job_postings_tsv
        ON job_postings USING gin (description_tsv)
    """)
    # Populate tsvector for existing rows
    op.execute("""
        UPDATE job_postings
        SET description_tsv = to_tsvector('english', COALESCE(description, ''))
        WHERE description_tsv IS NULL
    """)
    # Trigger to auto-update tsvector
    op.execute("""
        CREATE OR REPLACE FUNCTION job_postings_tsv_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.description_tsv := to_tsvector('english', COALESCE(NEW.description, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_job_postings_tsv ON job_postings
    """)
    op.execute("""
        CREATE TRIGGER trg_job_postings_tsv
        BEFORE INSERT OR UPDATE ON job_postings
        FOR EACH ROW EXECUTE FUNCTION job_postings_tsv_trigger()
    """)

    # ─── 4. BRIN indexes for time-series audit tables (efficient for large tables) ──
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_auth_audit_logs_created_brin
        ON auth_audit_logs USING brin (created_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_logs_created_brin
        ON audit_logs USING brin (created_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_login_attempts_created_brin
        ON login_attempts USING brin (created_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_activity_logs_created_brin
        ON activity_logs USING brin (created_at)
    """)

    # ─── 5. Materialized view for analytics dashboard ────────────────────
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_analytics_overview AS
        SELECT
            a.org_id,
            COUNT(*) AS total_screened,
            ROUND(AVG(a.score)::numeric, 2) AS average_score,
            COUNT(*) FILTER (WHERE a.score >= 70) AS accepted,
            COUNT(*) FILTER (WHERE a.score >= 40 AND a.score < 70) AS review,
            COUNT(*) FILTER (WHERE a.score < 40) AS rejected,
            MAX(a.created_at) AS last_screening_at
        FROM applications a
        WHERE a.deleted_at IS NULL
        GROUP BY a.org_id
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_analytics_org_id
        ON mv_analytics_overview (org_id)
    """)

    # Materialized view for skill demand
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_skill_demand AS
        SELECT
            jp.org_id,
            jsonb_array_elements_text(jp.required_skills) AS skill,
            COUNT(*) AS demand_count
        FROM job_postings jp
        WHERE jp.deleted_at IS NULL
        GROUP BY jp.org_id, skill
        ORDER BY demand_count DESC
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_mv_skill_demand_org
        ON mv_skill_demand (org_id, demand_count DESC)
    """)

    # ─── 6. Partial indexes for active records (reduce index size) ───────
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_job_postings_active
        ON job_postings (org_id, posted_at DESC)
        WHERE deleted_at IS NULL AND status = 'active'
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_applications_pending
        ON applications (org_id, created_at DESC)
        WHERE deleted_at IS NULL AND status NOT IN ('REJECTED', 'WITHDRAWN')
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_user_sessions_active
        ON user_sessions (user_id, last_activity DESC)
        WHERE status = 'active'
    """)

    # ─── 7. Covering indexes for frequent read patterns ─────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_applications_job_cand_score
        ON applications (job_id, candidate_id)
        INCLUDE (score, status, created_at)
        WHERE deleted_at IS NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_candidates_org_covering
        ON candidates (org_id, id)
        INCLUDE (name, email, status)
        WHERE deleted_at IS NULL
    """)

    # ─── 8. Auto-VACUUM tweak hints on high-churn tables ────────────────
    op.execute("""
        ALTER TABLE login_attempts SET (
            autovacuum_vacuum_scale_factor = 0.05,
            autovacuum_analyze_scale_factor = 0.02
        )
    """)
    op.execute("""
        ALTER TABLE auth_audit_logs SET (
            autovacuum_vacuum_scale_factor = 0.05,
            autovacuum_analyze_scale_factor = 0.02
        )
    """)

    # ─── 9. Refresh functions for materialized views ─────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_mv_analytics_overview()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_analytics_overview;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_mv_skill_demand()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_skill_demand;
        END;
        $$ LANGUAGE plpgsql
    """)


def downgrade() -> None:
    # Drop refresh functions
    op.execute("DROP FUNCTION IF EXISTS refresh_mv_skill_demand()")
    op.execute("DROP FUNCTION IF EXISTS refresh_mv_analytics_overview()")

    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_skill_demand")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_analytics_overview")

    # Drop covering indexes
    op.drop_index('ix_candidates_org_covering', table_name='candidates')
    op.drop_index('ix_applications_job_cand_score', table_name='applications')

    # Drop partial indexes
    op.drop_index('ix_user_sessions_active', table_name='user_sessions')
    op.drop_index('ix_applications_pending', table_name='applications')
    op.drop_index('ix_job_postings_active', table_name='job_postings')

    # Drop BRIN indexes
    op.execute("DROP INDEX IF EXISTS ix_activity_logs_created_brin")
    op.execute("DROP INDEX IF EXISTS ix_login_attempts_created_brin")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_created_brin")
    op.execute("DROP INDEX IF EXISTS ix_auth_audit_logs_created_brin")

    # Drop FTS trigger and tsvector
    op.execute("DROP TRIGGER IF EXISTS trg_job_postings_tsv ON job_postings")
    op.execute("DROP FUNCTION IF EXISTS job_postings_tsv_trigger()")
    op.drop_index('ix_job_postings_tsv', table_name='job_postings')
    op.execute("ALTER TABLE job_postings DROP COLUMN IF EXISTS description_tsv")

    # Drop GIN indexes
    op.execute("DROP INDEX IF EXISTS ix_candidates_skills_gin_new")
    op.execute("DROP INDEX IF EXISTS ix_job_postings_skills_gin")

    # Drop composite indexes
    op.drop_index('ix_audit_logs_user_action_time', table_name='audit_logs')
    op.drop_index('ix_auth_audit_org_event_time', table_name='auth_audit_logs')
    op.drop_index('ix_screening_results_job_score', table_name='screening_results')
    op.drop_index('ix_screening_results_app_id', table_name='screening_results')
    op.drop_index('ix_applications_job_score', table_name='applications')
    op.drop_index('ix_applications_org_score', table_name='applications')
    op.drop_index('ix_applications_org_status', table_name='applications')
    op.drop_index('ix_job_postings_org_posted', table_name='job_postings')
    op.drop_index('ix_job_postings_org_status', table_name='job_postings')
    op.drop_index('ix_candidates_org_email', table_name='candidates')
    op.drop_index('ix_candidates_org_status', table_name='candidates')
    op.drop_table('activity_logs')
