"""Initial schema — clients, api_keys, refresh_tokens

Revision ID: 0001
Revises:
Create Date: 2026-04-17 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── clients ─────────────────────────────────────────────────────────────
    op.create_table(
        "clients",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("email",        sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("full_name",    sa.String(255), server_default=""),
        sa.Column("is_active",    sa.Boolean(),   server_default=sa.true()),
        # Email verification
        sa.Column("is_email_verified",             sa.Boolean(),  server_default=sa.false()),
        sa.Column("email_verification_token",      sa.String(64), nullable=True),
        sa.Column("email_verification_expires_at", sa.DateTime(), nullable=True),
        # Password reset
        sa.Column("password_reset_token",          sa.String(64), nullable=True),
        sa.Column("password_reset_expires_at",     sa.DateTime(), nullable=True),
        # Timestamps
        sa.Column("created_at",   sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_clients_email", "clients", ["email"], unique=True)
    op.create_index("ix_clients_email_verification_token", "clients", ["email_verification_token"])
    op.create_index("ix_clients_password_reset_token",     "clients", ["password_reset_token"])

    # ── api_keys ─────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id",          sa.String(36),  primary_key=True),
        sa.Column("client_id",   sa.String(36),  sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name",        sa.String(255), server_default="Default Key"),
        sa.Column("key_prefix",  sa.String(12),  nullable=False),
        sa.Column("key_hash",    sa.String(64),  nullable=False),
        sa.Column("is_active",   sa.Boolean(),   server_default=sa.true()),
        sa.Column("created_at",  sa.DateTime(),  server_default=sa.func.now()),
        sa.Column("last_used_at",sa.DateTime(),  nullable=True),
        sa.Column("usage_count", sa.Integer(),   server_default="0"),
    )
    op.create_index("ix_api_keys_client_id", "api_keys", ["client_id"])
    op.create_index("ix_api_keys_key_hash",  "api_keys", ["key_hash"], unique=True)

    # ── refresh_tokens ───────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id",          sa.String(36),  primary_key=True),
        sa.Column("client_id",   sa.String(36),  sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash",  sa.String(64),  nullable=False),
        sa.Column("expires_at",  sa.DateTime(),  nullable=False),
        sa.Column("created_at",  sa.DateTime(),  server_default=sa.func.now()),
        sa.Column("revoked",     sa.Boolean(),   server_default=sa.false()),
        sa.Column("user_agent",  sa.String(512), nullable=True),
        sa.Column("ip_address",  sa.String(45),  nullable=True),
    )
    op.create_index("ix_refresh_tokens_client_id",  "refresh_tokens", ["client_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("api_keys")
    op.drop_table("clients")
