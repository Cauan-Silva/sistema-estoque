"""Sugere fornecedor, forma de pagamento e produto para os dados lidos.

A ordem de confiança para produtos é:
1. referência salva (este fornecedor já mandou este código/descrição antes);
2. semelhança entre a descrição do fornecedor e o nome do produto.
"""

import re
import unicodedata
from difflib import SequenceMatcher

LIMIAR_SEMELHANCA = 0.6

PALAVRAS_IGNORADAS = {
    "de", "da", "do", "das", "dos", "e", "com", "para", "em", "a", "o", "un", "und", "pc", "pcs", "cx",
}


def normalizar(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-z0-9,.]+", " ", texto.lower())
    return re.sub(r"\s+", " ", texto).strip()


def digitos(texto) -> str:
    return re.sub(r"\D", "", str(texto or ""))


def chaves_do_item(item) -> list[str]:
    """Chaves usadas para lembrar a associação feita pelo usuário."""
    chaves = []
    if item.get("codigo"):
        chaves.append(f"codigo:{normalizar(item['codigo'])}"[:300])
    if item.get("descricao"):
        chaves.append(f"descricao:{normalizar(item['descricao'])}"[:300])
    return chaves


def _palavras(texto) -> set[str]:
    return {p for p in normalizar(texto).replace(",", " ").split() if p not in PALAVRAS_IGNORADAS}


def semelhanca(a, b) -> float:
    na, nb = normalizar(a), normalizar(b)
    if not na or not nb:
        return 0.0
    sequencia = SequenceMatcher(None, na, nb).ratio()
    pa, pb = _palavras(a), _palavras(b)
    if not pa or not pb:
        return sequencia
    comuns = len(pa & pb)
    cobertura = comuns / min(len(pa), len(pb))
    jaccard = comuns / len(pa | pb)
    return round(max(sequencia, (cobertura + jaccard) / 2), 3)


def sugerir_fornecedor(nome, cnpj, fornecedores):
    alvo_cnpj = digitos(cnpj)
    if len(alvo_cnpj) >= 11:
        for fornecedor in fornecedores:
            if digitos(fornecedor.get("cpf_cnpj")) == alvo_cnpj:
                return fornecedor

    if not nome:
        return None

    melhor, nota = None, 0.0
    for fornecedor in fornecedores:
        valor = semelhanca(nome, fornecedor["nome"])
        if valor > nota:
            melhor, nota = fornecedor, valor
    return melhor if nota >= 0.75 else None


def sugerir_forma(condicao, formas):
    if not condicao:
        return None
    alvo = normalizar(condicao)
    for forma in formas:
        if normalizar(forma["titulo"]) in alvo or normalizar(forma["codigo"]) == alvo:
            return forma

    parcelas = re.findall(r"\d+", alvo)
    if "vista" in alvo:
        candidatas = [f for f in formas if f["parcelas"] == 1 and f["tipo"] == "A_VISTA"]
        return candidatas[0] if len(candidatas) == 1 else None
    if "/" in condicao and len(parcelas) >= 2:
        quantidade = len(parcelas)
        candidatas = [f for f in formas if f["parcelas"] == quantidade]
        return candidatas[0] if len(candidatas) == 1 else None
    return None


def sugerir_produto(item, produtos, referencias):
    for chave in chaves_do_item(item):
        produto_id = referencias.get(chave)
        if produto_id is not None:
            produto = next((p for p in produtos if p["id"] == produto_id), None)
            if produto:
                return {"id": produto["id"], "nome": produto["nome"], "motivo": "referencia", "confianca": 1.0}

    melhor, nota = None, 0.0
    for produto in produtos:
        valor = semelhanca(item.get("descricao"), produto["nome"])
        if valor > nota:
            melhor, nota = produto, valor

    if melhor and nota >= LIMIAR_SEMELHANCA:
        return {"id": melhor["id"], "nome": melhor["nome"], "motivo": "semelhanca", "confianca": nota}

    return None
