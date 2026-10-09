"""Leitura de orçamentos com um modelo rodando no próprio servidor (Ollama).

Nada sai da rede da empresa e não há custo por uso. PDFs com texto são
enviados como texto (qualquer modelo serve); prints, fotos e PDFs
escaneados vão como imagem e precisam de um modelo com visão, como o
qwen2.5vl ou o gemma3.
"""

import base64
import json
import logging
import os

import httpx

from backend.orcamentos import pdf

logger = logging.getLogger(__name__)

MODELO_PADRAO = "qwen2.5vl:7b"
TEMPO_LIMITE = 600
MINIMO_TEXTO = 80


def url_base() -> str:
    return os.getenv("OLLAMA_URL", "").strip().rstrip("/")


def modelo() -> str:
    return os.getenv("OLLAMA_MODEL", "").strip() or MODELO_PADRAO


def chamar_ollama(corpo: dict) -> dict:
    """Separado para os testes poderem substituir a chamada."""
    from backend.orcamentos.leitura import ErroLeitura

    try:
        resposta = httpx.post(f"{url_base()}/api/chat", json=corpo, timeout=TEMPO_LIMITE)
    except httpx.TimeoutException:
        raise ErroLeitura("O Ollama demorou demais para responder. Tente um modelo menor ou um arquivo com menos páginas.", 504)
    except httpx.HTTPError as erro:
        logger.warning("Falha ao chamar o Ollama: %s", erro)
        raise ErroLeitura(
            f"Não foi possível conectar ao Ollama em {url_base()}. Confira se ele está aberto e se OLLAMA_URL está certo.",
            502,
        )

    if resposta.status_code == 404:
        raise ErroLeitura(
            f"O modelo \"{modelo()}\" não está instalado no Ollama. Rode: ollama pull {modelo()}",
            502,
        )

    if resposta.status_code >= 400:
        try:
            detalhe = resposta.json().get("error", "")
        except ValueError:
            detalhe = resposta.text[:200]
        raise ErroLeitura(f"O Ollama não conseguiu ler o arquivo ({resposta.status_code}). {detalhe}".strip(), 502)

    return resposta.json()


def ler(conteudo: bytes, tipo: str, instrucoes: str, esquema: dict) -> dict:
    from backend.orcamentos.leitura import ErroLeitura

    mensagem = {"role": "user", "content": "Extraia os dados deste documento e responda só com o JSON pedido."}

    if tipo == "application/pdf":
        try:
            texto = pdf.texto(conteudo)
        except Exception:
            raise ErroLeitura("Não foi possível abrir o PDF. Ele pode estar protegido ou corrompido.")

        if len(texto) >= MINIMO_TEXTO:
            mensagem["content"] = (
                "Extraia os dados do documento abaixo (texto tirado de um PDF; as colunas podem estar "
                "desalinhadas) e responda só com o JSON pedido.\n\n" + texto[:30000]
            )
        else:
            paginas = pdf.imagens(conteudo)
            mensagem["images"] = [base64.standard_b64encode(p).decode() for p in paginas]
    else:
        mensagem["images"] = [base64.standard_b64encode(conteudo).decode()]

    resposta = chamar_ollama({
        "model": modelo(),
        "stream": False,
        "format": esquema,
        "options": {"temperature": 0},
        "messages": [{"role": "system", "content": instrucoes}, mensagem],
    })

    texto_resposta = (resposta.get("message") or {}).get("content") or ""

    try:
        return json.loads(texto_resposta)
    except json.JSONDecodeError:
        logger.warning("Resposta do Ollama não é JSON: %s", texto_resposta[:300])
        raise ErroLeitura("A IA local não devolveu os dados no formato esperado. Tente de novo ou use outro modelo.", 422)
