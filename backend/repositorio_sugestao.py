"""Sugestão de compra a partir do estoque mínimo e do consumo médio.

Para cada produto:
- consumo diário = saídas dos últimos `dias_consumo` dias ÷ `dias_consumo`;
- em pedido = itens de solicitações abertas, em cotação ou aprovadas, mais o
  que já foi comprado e ainda não chegou;
- prazo = média do prazo de entrega das cotações aprovadas do produto
  (ou `prazo_padrao`, se ele nunca foi comprado pelo sistema);
- ponto de pedido = estoque mínimo + consumo diário × prazo;
- quando estoque + em pedido ≤ ponto de pedido, sugere comprar o suficiente
  para voltar ao mínimo e cobrir `cobertura_dias` de consumo depois da entrega
  (no mínimo um lote do tamanho do estoque mínimo).
"""

import logging
import math

import psycopg2

from backend.database import conectar

logger = logging.getLogger(__name__)

CONSULTA = """
    WITH consumo AS (
        SELECT produto_id, SUM(quantidade) AS saidas
        FROM movimentacoes
        WHERE tipo = 'SAIDA'
          AND data_movimentacao >= CURRENT_TIMESTAMP - make_interval(days => %(dias)s)
        GROUP BY produto_id
    ),
    solicitado AS (
        SELECT i.produto_id, SUM(i.quantidade) AS quantidade
        FROM itens_solicitacao_compra i
        JOIN solicitacoes_compra s ON s.id = i.solicitacao_id
        WHERE s.status IN ('ABERTA', 'EM_COTACAO', 'APROVADA')
        GROUP BY i.produto_id
    ),
    comprado AS (
        SELECT ic.produto_id, SUM(ic.quantidade) AS quantidade
        FROM itens_compra ic
        JOIN compras c ON c.id = ic.compra_id
        JOIN solicitacoes_compra s ON s.id = c.solicitacao_id
        WHERE s.status = 'COMPRADA'
        GROUP BY ic.produto_id
    ),
    recebido AS (
        SELECT ir.produto_id, SUM(ir.quantidade) AS quantidade
        FROM itens_recebimento ir
        JOIN recebimentos r ON r.id = ir.recebimento_id
        JOIN compras c ON c.id = r.compra_id
        JOIN solicitacoes_compra s ON s.id = c.solicitacao_id
        WHERE s.status = 'COMPRADA'
        GROUP BY ir.produto_id
    ),
    prazo AS (
        SELECT ic.produto_id, AVG(c.prazo_entrega_dias) AS dias
        FROM itens_cotacao ic
        JOIN cotacoes c ON c.id = ic.cotacao_id
        JOIN solicitacoes_compra s ON s.cotacao_aprovada_id = c.id
        GROUP BY ic.produto_id
    ),
    ultima_compra AS (
        SELECT DISTINCT ON (ic.produto_id)
            ic.produto_id, ic.preco_unitario, f.id AS fornecedor_id, f.nome AS fornecedor
        FROM itens_compra ic
        JOIN compras c ON c.id = ic.compra_id
        JOIN fornecedores f ON f.id = c.fornecedor_id
        ORDER BY ic.produto_id, c.data_compra DESC, c.id DESC
    )
    SELECT
        p.id, p.nome, p.categoria_id, cat.nome, p.quantidade, p.estoque_minimo, p.preco,
        COALESCE(co.saidas, 0),
        COALESCE(so.quantidade, 0) + GREATEST(COALESCE(cp.quantidade, 0) - COALESCE(re.quantidade, 0), 0),
        pr.dias,
        uc.preco_unitario, uc.fornecedor_id, uc.fornecedor
    FROM produtos p
    LEFT JOIN categorias cat ON cat.id = p.categoria_id
    LEFT JOIN consumo co ON co.produto_id = p.id
    LEFT JOIN solicitado so ON so.produto_id = p.id
    LEFT JOIN comprado cp ON cp.produto_id = p.id
    LEFT JOIN recebido re ON re.produto_id = p.id
    LEFT JOIN prazo pr ON pr.produto_id = p.id
    LEFT JOIN ultima_compra uc ON uc.produto_id = p.id
    ORDER BY p.nome;
"""


def calcular(registro, dias_consumo: int, cobertura_dias: int, prazo_padrao: int):
    (
        produto_id, nome, categoria_id, categoria, estoque, minimo, preco_cadastro,
        saidas, em_pedido, prazo_medio, ultimo_preco, fornecedor_id, fornecedor,
    ) = registro

    consumo_diario = float(saidas) / dias_consumo
    prazo = round(float(prazo_medio)) if prazo_medio is not None else prazo_padrao
    disponivel = estoque + int(em_pedido)
    ponto_pedido = minimo + consumo_diario * prazo
    alvo = minimo + consumo_diario * (prazo + cobertura_dias)

    precisa = disponivel <= ponto_pedido
    # Compra pelo menos um lote do tamanho do estoque mínimo, para não sugerir 1 unidade de cada vez.
    sugerido = max(math.ceil(alvo - disponivel), minimo, 1) if precisa else 0

    if estoque <= minimo and int(em_pedido) == 0:
        motivo = "No estoque mínimo ou abaixo, sem pedido aberto"
    elif estoque <= minimo:
        motivo = "Abaixo do mínimo, mas o pedido aberto não cobre o consumo"
    elif precisa:
        motivo = f"Deve chegar ao mínimo antes de uma reposição de {prazo} dias"
    else:
        motivo = None

    preco = float(ultimo_preco) if ultimo_preco is not None else float(preco_cadastro)

    return {
        "produto_id": produto_id,
        "produto": nome,
        "categoria_id": categoria_id,
        "categoria": categoria,
        "estoque": estoque,
        "estoque_minimo": minimo,
        "em_pedido": int(em_pedido),
        "consumo_periodo": int(saidas),
        "consumo_mensal": round(consumo_diario * 30, 1),
        "dias_restantes": math.floor(estoque / consumo_diario) if consumo_diario > 0 else None,
        "prazo_entrega_dias": prazo,
        "prazo_estimado": prazo_medio is None,
        "ponto_pedido": math.ceil(ponto_pedido),
        "sugerido": sugerido,
        "motivo": motivo,
        "preco_referencia": preco,
        "valor_estimado": round(preco * sugerido, 2),
        "ultimo_fornecedor_id": fornecedor_id,
        "ultimo_fornecedor": fornecedor,
    }


def sugestoes_de_compra(dias_consumo=90, cobertura_dias=30, prazo_padrao=7, todos=False):
    conexao = conectar()
    if conexao is None:
        return None
    try:
        cursor = conexao.cursor()
        cursor.execute(CONSULTA, {"dias": dias_consumo})
        produtos = [calcular(r, dias_consumo, cobertura_dias, prazo_padrao) for r in cursor.fetchall()]
        cursor.close()
        conexao.close()
    except psycopg2.Error as erro:
        conexao.close()
        logger.error(f"Erro ao calcular sugestões de compra: {erro}")
        return None

    if not todos:
        produtos = [p for p in produtos if p["sugerido"] > 0]

    produtos.sort(key=lambda p: (
        p["sugerido"] == 0,
        not (p["estoque"] <= p["estoque_minimo"]),
        p["dias_restantes"] if p["dias_restantes"] is not None else float("inf"),
        p["produto"],
    ))

    return produtos
