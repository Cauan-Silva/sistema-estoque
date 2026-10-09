"""Referências de produto por fornecedor e preço unitário com 4 casas

Guarda como cada fornecedor chama um produto nosso (código ou descrição
do orçamento), para sugerir a associação na próxima importação.

Também passa o preço unitário das cotações e compras para 4 casas decimais,
porque itens baratos comprados aos milhares (ex.: R$ 0,0435) perdiam valor
ao arredondar para centavos.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from alembic import op


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "referencias_fornecedor",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "fornecedor_id",
            sa.Integer(),
            sa.ForeignKey("fornecedores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chave", sa.String(300), nullable=False),
        sa.Column(
            "produto_id",
            sa.Integer(),
            sa.ForeignKey("produtos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("fornecedor_id", "chave", name="referencias_fornecedor_chave_unica"),
    )


    for tabela in ("itens_cotacao", "itens_compra"):
        op.alter_column(
            tabela,
            "preco_unitario",
            type_=sa.Numeric(12, 4),
            existing_type=sa.Numeric(10, 2),
            existing_nullable=False,
        )


def downgrade():
    for tabela in ("itens_cotacao", "itens_compra"):
        op.alter_column(
            tabela,
            "preco_unitario",
            type_=sa.Numeric(10, 2),
            existing_type=sa.Numeric(12, 4),
            existing_nullable=False,
        )
    op.drop_table("referencias_fornecedor")
