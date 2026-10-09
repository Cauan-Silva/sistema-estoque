"""Preços de referência anotados pelo usuário

Preço visto em uma loja (ex.: Mercado Livre) e anotado à mão na tela de
preços do produto, para usar como referência na negociação.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "precos_referencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "produto_id",
            sa.Integer(),
            sa.ForeignKey("produtos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("valor", sa.Numeric(12, 4), nullable=False),
        sa.Column("fonte", sa.String(60), nullable=False, server_default="Mercado Livre"),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("observacao", sa.String(300), nullable=True),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "data_registro",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("valor >= 0", name="precos_referencia_valor_check"),
    )


def downgrade():
    op.drop_table("precos_referencia")
