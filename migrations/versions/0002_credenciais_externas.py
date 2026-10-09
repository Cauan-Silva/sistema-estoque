"""Credenciais de APIs externas

Guarda o access token e o refresh token das fontes de preço (ex.: Mercado
Livre), para que a renovação automática sobreviva a reinícios da API.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from alembic import op


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "credenciais_externas",
        sa.Column("fonte", sa.String(50), primary_key=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade():
    op.drop_table("credenciais_externas")
