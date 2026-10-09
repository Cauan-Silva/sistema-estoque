"""Extrai fornecedor, condições e itens de um orçamento recebido.

- XML de NF-e: lido aqui mesmo, sem custo.
- PDF e imagens (prints, fotos): lidos por IA, de uma destas formas:
  - Ollama, rodando no próprio servidor (OLLAMA_URL): gratuito e nada sai da empresa;
  - API da Anthropic (ANTHROPIC_API_KEY): pago por uso, mais preciso.
  LEITURA_ORCAMENTOS=ollama|anthropic escolhe quando os dois estão configurados.

O resultado é sempre o mesmo dicionário (ver `orcamento_vazio`), para a
tela de revisão tratar todos os formatos igual.
"""

import base64
import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime

import httpx


logger = logging.getLogger(__name__)

URL_API = "https://api.anthropic.com/v1/messages"
VERSAO_API = "2023-06-01"
MODELO_PADRAO = "claude-sonnet-5-5"
TEMPO_LIMITE = 120

TIPOS_IMAGEM = {"image/png", "image/jpeg", "image/webp", "image/gif"}
TIPOS_ACEITOS = TIPOS_IMAGEM | {"application/pdf", "text/xml", "application/xml"}


class ErroLeitura(Exception):
    """Falha com mensagem pronta para o usuário."""

    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.status = status


def orcamento_vazio():
    return {
        "tipo_documento": "orcamento",
        "fornecedor_nome": None,
        "fornecedor_cnpj": None,
        "numero_documento": None,
        "data_emissao": None,
        "validade": None,
        "prazo_entrega_dias": None,
        "frete": 0.0,
        "condicao_pagamento": None,
        "observacao": None,
        "itens": [],
    }


def provedor_ia() -> str | None:
    """Qual IA lê PDF e imagens: "ollama", "anthropic" ou None (nenhuma configurada)."""
    escolhido = os.getenv("LEITURA_ORCAMENTOS", "").strip().lower()
    tem_anthropic = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    tem_ollama = bool(os.getenv("OLLAMA_URL", "").strip())

    if escolhido == "ollama" and tem_ollama:
        return "ollama"
    if escolhido == "anthropic" and tem_anthropic:
        return "anthropic"
    if tem_ollama:
        return "ollama"
    if tem_anthropic:
        return "anthropic"
    return None


def leitura_por_ia_configurada() -> bool:
    return provedor_ia() is not None


def tipo_do_arquivo(nome: str, tipo_informado: str | None, conteudo: bytes) -> str:
    """Decide o tipo pelo conteúdo, depois pela extensão (o navegador às vezes erra)."""
    inicio = conteudo[:16]
    if inicio.startswith(b"%PDF"):
        return "application/pdf"
    if inicio.startswith(b"\x89PNG"):
        return "image/png"
    if inicio.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if inicio[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "image/webp"
    if inicio.startswith(b"GIF8"):
        return "image/gif"
    if conteudo.lstrip()[:1] == b"<":
        return "application/xml"

    extensao = (nome or "").lower().rsplit(".", 1)[-1]
    por_extensao = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "xml": "application/xml",
    }
    return por_extensao.get(extensao) or (tipo_informado or "")


def extrair(conteudo: bytes, nome: str, tipo_informado: str | None = None):
    tipo = tipo_do_arquivo(nome, tipo_informado, conteudo)

    if tipo in ("application/xml", "text/xml"):
        return ler_xml_nfe(conteudo), "xml"

    if tipo not in TIPOS_ACEITOS:
        raise ErroLeitura("Formato não suportado. Envie PDF, imagem (PNG, JPG, WEBP) ou XML de NF-e.")

    return ler_com_ia(conteudo, tipo), provedor_ia()


# ---------- XML de NF-e ----------

def _sem_namespace(elemento):
    for item in elemento.iter():
        if "}" in item.tag:
            item.tag = item.tag.split("}", 1)[1]
    return elemento


def _texto(elemento, caminho):
    encontrado = elemento.find(caminho) if elemento is not None else None
    return encontrado.text.strip() if encontrado is not None and encontrado.text else None


def _numero(texto):
    try:
        return float(texto) if texto not in (None, "") else None
    except ValueError:
        return None


def ler_xml_nfe(conteudo: bytes):
    try:
        raiz = _sem_namespace(ET.fromstring(conteudo))
    except ET.ParseError:
        raise ErroLeitura("O XML não pôde ser lido. Envie o XML da NF-e como recebido.")

    nfe = raiz.find(".//infNFe")
    if nfe is None:
        raise ErroLeitura("Este XML não é de uma NF-e.")

    dados = orcamento_vazio()
    dados["tipo_documento"] = "nota_fiscal"
    dados["fornecedor_nome"] = _texto(nfe, "emit/xNome")
    dados["fornecedor_cnpj"] = _texto(nfe, "emit/CNPJ") or _texto(nfe, "emit/CPF")
    dados["numero_documento"] = _texto(nfe, "ide/nNF")
    emissao = _texto(nfe, "ide/dhEmi") or _texto(nfe, "ide/dEmi")
    dados["data_emissao"] = emissao[:10] if emissao else None
    dados["frete"] = _numero(_texto(nfe, "total/ICMSTot/vFrete")) or 0.0
    dados["observacao"] = _texto(nfe, "infAdic/infCpl")

    parcelas = nfe.findall("cobr/dup")
    if parcelas:
        vencimentos = [_texto(p, "dVenc") for p in parcelas]
        dados["condicao_pagamento"] = f"{len(parcelas)}x, vencimentos " + ", ".join(v for v in vencimentos if v)

    for item in nfe.findall("det"):
        produto = item.find("prod")
        quantidade = _numero(_texto(produto, "qCom")) or 0
        valor = _numero(_texto(produto, "vProd")) or 0
        desconto = _numero(_texto(produto, "vDesc")) or 0
        ipi = _numero(_texto(item, "imposto/IPI/IPITrib/vIPI")) or 0
        total = round(valor - desconto + ipi, 2)

        dados["itens"].append({
            "codigo": _texto(produto, "cProd"),
            "descricao": _texto(produto, "xProd") or "",
            "unidade": _texto(produto, "uCom"),
            "quantidade": quantidade,
            "preco_unitario": round(total / quantidade, 4) if quantidade else _numero(_texto(produto, "vUnCom")) or 0,
            "valor_total": total,
        })

    return dados


# ---------- Leitura por IA ----------

ESQUEMA = {
    "type": "object",
    "properties": {
        "tipo_documento": {
            "type": "string",
            "enum": ["orcamento", "pedido", "nota_fiscal", "outro"],
            "description": "Que documento é este.",
        },
        "fornecedor_nome": {
            "type": ["string", "null"],
            "description": "Razão social ou nome fantasia de quem VENDE (emitente). Nulo se não aparecer.",
        },
        "fornecedor_cnpj": {
            "type": ["string", "null"],
            "description": "CNPJ ou CPF de quem vende, como aparece. Nulo se não aparecer.",
        },
        "numero_documento": {"type": ["string", "null"]},
        "data_emissao": {"type": ["string", "null"], "description": "AAAA-MM-DD"},
        "validade": {"type": ["string", "null"], "description": "Validade da proposta, AAAA-MM-DD"},
        "prazo_entrega_dias": {
            "type": ["integer", "null"],
            "description": "Prazo de entrega em dias corridos. Se houver data de entrega e data do documento, use a diferença.",
        },
        "frete": {
            "type": "number",
            "description": "Valor do frete cobrado do comprador em reais. CIF ou frete grátis = 0.",
        },
        "condicao_pagamento": {
            "type": ["string", "null"],
            "description": "Condição de pagamento como escrita (ex.: '28/56/84 dias', '0+3x', 'à vista').",
        },
        "observacao": {
            "type": ["string", "null"],
            "description": "Resumo curto de observações úteis para a compra (transportadora, tipo de frete, condições). No máximo 400 caracteres.",
        },
        "itens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "codigo": {"type": ["string", "null"], "description": "Código do produto no fornecedor."},
                    "descricao": {"type": "string"},
                    "unidade": {"type": ["string", "null"]},
                    "quantidade": {"type": "number"},
                    "preco_unitario": {
                        "type": "number",
                        "description": "Preço final por unidade em reais, já com IPI e descontos (valor total do item ÷ quantidade).",
                    },
                    "valor_total": {"type": "number", "description": "Valor total do item em reais."},
                },
                "required": ["descricao", "quantidade", "preco_unitario", "valor_total"],
            },
        },
    },
    "required": ["tipo_documento", "fornecedor_nome", "frete", "itens"],
}

INSTRUCOES = """Você lê orçamentos, pedidos e notas fiscais enviados por fornecedores a uma empresa que está comprando.
Extraia os dados e chame a ferramenta registrar_orcamento.

Regras:
- O fornecedor é quem VENDE (emitente, empresa no cabeçalho, vendedor). Nunca use o cliente/destinatário como fornecedor. Se o vendedor não aparecer, deixe fornecedor_nome nulo.
- Números estão no formato brasileiro: "1.000,0000" é mil; "2,59" é dois e cinquenta e nove. Devolva números JSON normais (1000, 2.59).
- preco_unitario é o custo final por unidade: inclua IPI e subtraia descontos. Se houver coluna de preço com IPI, use ela.
- Inclua todos os itens, na ordem do documento. Não invente itens nem valores.
- Datas em AAAA-MM-DD. Se só houver data de entrega, calcule prazo_entrega_dias a partir da data do documento.
- Frete CIF (por conta do remetente/fornecedor) é 0."""


INSTRUCOES_OLLAMA = INSTRUCOES.replace(
    "Extraia os dados e chame a ferramenta registrar_orcamento.",
    "Extraia os dados e responda somente com um objeto JSON no formato pedido, sem texto antes ou depois. "
    "Use null quando um campo não aparecer.",
)


def _modelo() -> str:
    return os.getenv("ANTHROPIC_MODEL", "").strip() or MODELO_PADRAO


def chamar_api(corpo: dict) -> dict:
    """Separado para os testes poderem substituir a chamada."""
    chave = os.getenv("ANTHROPIC_API_KEY", "").strip()

    try:
        resposta = httpx.post(
            URL_API,
            json=corpo,
            headers={
                "x-api-key": chave,
                "anthropic-version": VERSAO_API,
                "content-type": "application/json",
            },
            timeout=TEMPO_LIMITE,
        )
    except httpx.HTTPError as erro:
        logger.warning("Falha ao chamar a API da Anthropic: %s", erro)
        raise ErroLeitura("Não foi possível conectar à API da Anthropic. Verifique a internet do servidor.", 502)

    if resposta.status_code >= 400:
        try:
            detalhe = resposta.json().get("error", {}).get("message", "")
        except ValueError:
            detalhe = resposta.text[:200]
        logger.warning("API da Anthropic respondeu %s: %s", resposta.status_code, detalhe)
        if resposta.status_code in (401, 403):
            raise ErroLeitura("A chave ANTHROPIC_API_KEY foi recusada. Confira o valor no .env.", 502)
        raise ErroLeitura(f"A API da Anthropic não conseguiu ler o arquivo ({resposta.status_code}). {detalhe}".strip(), 502)

    return resposta.json()


def ler_com_ia(conteudo: bytes, tipo: str):
    provedor = provedor_ia()

    if provedor is None:
        raise ErroLeitura(
            "A leitura de PDF e imagens não está configurada. Defina OLLAMA_URL (IA local, gratuita) "
            "ou ANTHROPIC_API_KEY no .env e reinicie a API. XML de NF-e funciona sem elas.",
            503,
        )

    if provedor == "ollama":
        from backend.orcamentos import ollama

        return normalizar(ollama.ler(conteudo, tipo, INSTRUCOES_OLLAMA, ESQUEMA))

    dados_base64 = base64.standard_b64encode(conteudo).decode()
    anexo = (
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": dados_base64}}
        if tipo == "application/pdf"
        else {"type": "image", "source": {"type": "base64", "media_type": tipo, "data": dados_base64}}
    )

    corpo = {
        "model": _modelo(),
        "max_tokens": 8000,
        "system": INSTRUCOES,
        "tools": [{
            "name": "registrar_orcamento",
            "description": "Registra os dados extraídos do documento do fornecedor.",
            "input_schema": ESQUEMA,
        }],
        "tool_choice": {"type": "tool", "name": "registrar_orcamento"},
        "messages": [{
            "role": "user",
            "content": [anexo, {"type": "text", "text": "Extraia os dados deste documento."}],
        }],
    }

    resposta = chamar_api(corpo)

    chamada = next(
        (bloco for bloco in resposta.get("content", []) if bloco.get("type") == "tool_use"),
        None,
    )

    if chamada is None:
        raise ErroLeitura("A IA não conseguiu identificar um orçamento neste arquivo.", 422)

    return normalizar(chamada.get("input") or {})


# ---------- Normalização ----------

def _data_iso(valor):
    if not valor:
        return None
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%Y-%m-%d")
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto[:10], formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _positivo(valor, casas=4):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return round(numero, casas) if numero >= 0 else None


def normalizar(bruto: dict):
    dados = orcamento_vazio()
    for chave in dados:
        if chave in bruto and chave != "itens":
            dados[chave] = bruto[chave]

    dados["data_emissao"] = _data_iso(dados["data_emissao"])
    dados["validade"] = _data_iso(dados["validade"])
    dados["frete"] = _positivo(dados["frete"], 2) or 0.0
    prazo = dados["prazo_entrega_dias"]
    dados["prazo_entrega_dias"] = int(prazo) if isinstance(prazo, (int, float)) and prazo >= 0 else None
    if dados["observacao"]:
        dados["observacao"] = str(dados["observacao"])[:500]
    if dados["fornecedor_cnpj"]:
        dados["fornecedor_cnpj"] = re.sub(r"[^\d./-]", "", str(dados["fornecedor_cnpj"]))[:20] or None

    for item in bruto.get("itens") or []:
        descricao = str(item.get("descricao") or "").strip()
        quantidade = _positivo(item.get("quantidade"))
        preco = _positivo(item.get("preco_unitario"))
        if not descricao or not quantidade or preco is None:
            continue
        dados["itens"].append({
            "codigo": str(item["codigo"]).strip() if item.get("codigo") not in (None, "") else None,
            "descricao": descricao[:300],
            "unidade": item.get("unidade"),
            "quantidade": quantidade,
            "preco_unitario": preco,
            "valor_total": _positivo(item.get("valor_total"), 2) or round(quantidade * preco, 2),
        })

    return dados
