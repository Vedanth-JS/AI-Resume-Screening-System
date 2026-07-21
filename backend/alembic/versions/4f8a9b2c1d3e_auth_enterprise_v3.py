"""auth_enterprise_v3

Revision ID: 4f8a9b2c1d3e
Revises: 542d5ab8aaf7
Create Date: 2026-07-20

Add all enterprise auth tables: oauth_accounts, mfa_devices, user_sessions,
api_keys, auth_audit_logs, login_attempts, password_reset_tokens.
Add missing user columns: is_active, email_verified, phone, avatar_url, timezone.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '4f8a9b2c1d3e'
down_revision: Union[str, None] = '542d5ab8aaf7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Add missing User columns ─────────────────────────────────────────
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('users', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('timezone', sa.String(length=50), nullable=False, server_default=sa.text("'UTC'")))

    # ─── OAuth Accounts ───────────────────────────────────────────────────
    op.create_table(
        'oauth_accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),
        sa.Column('provider_email', sa.String(length=255), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_oauth_accounts_id', 'oauth_accounts', ['id'])
    op.create_index('ix_oauth_accounts_user_id', 'oauth_accounts', ['user_id'])
    op.create_index('ix_oauth_provider_user', 'oauth_accounts', ['provider', 'provider_user_id'], unique=True)

    # ─── MFA Devices ──────────────────────────────────────────────────────
    op.create_table(
        'mfa_devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('secret', sa.String(length=256), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('backup_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mfa_devices_id', 'mfa_devices', ['id'])
    op.create_index('ix_mfa_devices_user_id', 'mfa_devices', ['user_id'])

    # ─── User Sessions ────────────────────────────────────────────────────
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_token', sa.String(length=512), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.Column('device_type', sa.String(length=20), nullable=False, server_default=sa.text("'browser'")),
        sa.Column('device_name', sa.String(length=200), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('location', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_reason', sa.String(length=200), nullable=True),
        sa.Column('mfa_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_sessions_id', 'user_sessions', ['id'])
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_token', 'user_sessions', ['session_token'], unique=True)
    op.create_index('ix_sessions_user_status', 'user_sessions', ['user_id', 'status'])
    op.create_index('ix_sessions_expiry', 'user_sessions', ['expires_at'])

    # ─── API Keys ─────────────────────────────────────────────────────────
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_hash', sa.String(length=128), nullable=False),
        sa.Column('key_prefix', sa.String(length=12), nullable=False),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('allowed_ips', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('use_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_keys_id', 'api_keys', ['id'])
    op.create_index('ix_api_keys_org_id', 'api_keys', ['org_id'])
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    op.create_index('ix_api_keys_user_active', 'api_keys', ['user_id', 'is_active'])

    # ─── Auth Audit Logs ──────────────────────────────────────────────────
    op.create_table(
        'auth_audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('event', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('device_type', sa.String(length=20), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auth_audit_logs_id', 'auth_audit_logs', ['id'])
    op.create_index('ix_auth_audit_user_time', 'auth_audit_logs', ['user_id', 'created_at'])
    op.create_index('ix_auth_audit_org_time', 'auth_audit_logs', ['org_id', 'created_at'])

    # ─── Login Attempts ───────────────────────────────────────────────────
    op.create_table(
        'login_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('identifier', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('failure_reason', sa.String(length=200), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_attempts_id', 'login_attempts', ['id'])
    op.create_index('ix_login_attempts_identifier', 'login_attempts', ['identifier'])
    op.create_index('ix_login_attempts_identifier_time', 'login_attempts', ['identifier', 'created_at'])

    # ─── Password Reset Tokens ────────────────────────────────────────────
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_password_reset_tokens_id', 'password_reset_tokens', ['id'])
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('ix_password_reset_tokens_hash', 'password_reset_tokens', ['token_hash'], unique=True)

    # ─── Email Verification Tokens ────────────────────────────────────────
    op.create_table(
        'email_verification_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_email_verification_tokens_id', 'email_verification_tokens', ['id'])
    op.create_index('ix_email_verification_tokens_user_id', 'email_verification_tokens', ['user_id'])
    op.create_index('ix_email_verification_tokens_hash', 'email_verification_tokens', ['token_hash'], unique=True)

    # ─── OAuth State (CSRF protection) ────────────────────────────────────
    op.create_table(
        'oauth_states',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('state', sa.String(length=128), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('redirect_uri', sa.String(length=512), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_oauth_states_state', 'oauth_states', ['state'], unique=True)


def downgrade() -> None:
    op.drop_table('oauth_states')
    op.drop_table('email_verification_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_table('login_attempts')
    op.drop_table('auth_audit_logs')
    op.drop_table('api_keys')
    op.drop_table('user_sessions')
    op.drop_table('mfa_devices')
    op.drop_table('oauth_accounts')

    op.drop_column('users', 'timezone')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'is_active')
