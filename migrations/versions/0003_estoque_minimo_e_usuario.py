"""Estoque mínimo por produto e usuário da movimentação

- produtos.estoque_minimo: limite para considerar o estoque baixo (padrão 5,
  o mesmo valor fixo usado antes).
- movimentacoes.usuario_id: quem registrou a movimentação. Fica nulo nas
  movimentações antigas.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "produtos",
        sa.Column("estoque_minimo", sa.Integer(), nullable=False, server_default="5"),
    )
    op.create_check_constraint(
        "produtos_estoque_minimo_check", "produtos", "estoque_minimo >= 0"
    )
    op.add_column(
        "movimentacoes",
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("movimentacoes", "usuario_id")
    op.drop_constraint("produtos_estoque_minimo_check", "produtos")
    op.drop_column("produtos", "estoque_minimo")
