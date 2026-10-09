"""Anexos das solicitações de compra (notas fiscais, propostas, boletos)

Os arquivos ficam no próprio banco (bytea), para entrarem no backup junto
com o resto dos dados e funcionarem igual com ou sem Docker.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "anexos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "solicitacao_id",
            sa.Integer(),
            sa.ForeignKey("solicitacoes_compra.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("descricao", sa.String(200), nullable=True),
        sa.Column("nome_arquivo", sa.String(255), nullable=False),
        sa.Column("tipo_conteudo", sa.String(100), nullable=False),
        sa.Column("tamanho", sa.Integer(), nullable=False),
        sa.Column("conteudo", sa.LargeBinary(), nullable=False),
        sa.Column(
            "fornecedor_id",
            sa.Integer(),
            sa.ForeignKey("fornecedores.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "data_envio",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "tipo IN ('NOTA_FISCAL', 'PROPOSTA', 'PEDIDO', 'BOLETO', 'OUTRO')",
            name="anexos_tipo_check",
        ),
    )


def downgrade():
    op.drop_table("anexos")
