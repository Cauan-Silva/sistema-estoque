"""Leitura do CSV "Itens do Pedido de Compra" exportado pelo sistema antigo.

O arquivo usa ";" entre campos e aspas em volta de cada valor, mas não
escapa aspas dentro do texto (ex.: ELETRODUTO PVC 1"), o que quebra os
leitores de CSV comuns. Aqui cada registro começa numa linha
"<empresa>";"<número>";"<dd/mm/aaaa>"; e os campos são separados por ";".
"""

import re

CAMPOS = [
    "Local", "Numero do Pedido", "Data do Pedido", "Solicitante", "Fornecedor",
    "Item do Pedido", "Grupo do Item", "Quatidade UN", "Valor Unitario", "Valor Total",
    "Previsao de Entrega", "Status do Pedido", "Condicao de Pgto", "Observacao",
    "Aprovador", "Data de Aprovacao",
]

INICIO_REGISTRO = re.compile(r'^"([^"\n]*)";"(\d+)";"(\d{2}/\d{2}/\d{4})";', re.M)


class ArquivoInvalido(ValueError):
    pass


def ler_pedidos(texto: str):
    """Devolve (registros, problemas). Cada registro é um dict com as colunas do arquivo."""
    texto = texto.lstrip("﻿").replace("\r\n", "\n")

    if "\n" not in texto:
        raise ArquivoInvalido("O arquivo está vazio.")

    cabecalho, corpo = texto.split("\n", 1)
    colunas = [c.strip().strip('"') for c in cabecalho.split(";")]

    if colunas[:len(CAMPOS)] != CAMPOS:
        raise ArquivoInvalido(
            "As colunas não são as do relatório \"Itens do Pedido de Compra\". "
            f"Esperado: {'; '.join(CAMPOS)}"
        )

    inicios = [m.start() for m in INICIO_REGISTRO.finditer(corpo)]
    registros, problemas = [], []

    for indice, inicio in enumerate(inicios):
        fim = inicios[indice + 1] if indice + 1 < len(inicios) else len(corpo)
        bloco = corpo[inicio:fim].rstrip("\n")
        bloco = bloco[1:] if bloco.startswith('"') else bloco
        bloco = bloco[:-1] if bloco.endswith('"') else bloco
        partes = bloco.split('";"')

        if len(partes) != len(CAMPOS):
            problemas.append(f"Registro {indice + 1}: {len(partes)} campos em vez de {len(CAMPOS)} ({bloco[:80]}...)")
            continue

        registros.append({campo: valor.replace('""', '"').strip() for campo, valor in zip(CAMPOS, partes)})

    return registros, problemas
