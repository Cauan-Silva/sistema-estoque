import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.autenticacao import validar_token_acesso
from backend.database import aplicar_migracoes
from backend.logs import configurar_logs
from backend.repositorio_auditoria import registrar_auditoria

from backend.routes.produtos import (
    router as produtos_router
)
from backend.routes.categorias import (
    router as categorias_router
)
from backend.routes.movimentacoes import (
    router as movimentacoes_router
)
from backend.routes.relatorios import (
    router as relatorios_router
)
from backend.routes.usuarios import (
    router as usuarios_router
)
from backend.routes.fornecedores import (
    router as fornecedores_router
)
from backend.routes.solicitacoes_compra import (
    router as solicitacoes_compra_router
)
from backend.routes.cotacoes import (
    router as cotacoes_router
)
from backend.routes.compras import (
    router as compras_router
)
from backend.routes.formas_pagamento import (
    router as formas_pagamento_router
)
from backend.routes.auditoria import (
    router as auditoria_router
)
from backend.routes.exportacoes import (
    router as exportacoes_router
)


configurar_logs()

logger = logging.getLogger("backend.requisicoes")

METODOS_AUDITADOS = {"POST", "PUT", "PATCH", "DELETE"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    aplicar_migracoes()

    yield


def usuario_da_requisicao(request: Request) -> int | None:
    cabecalho = request.headers.get("authorization", "")

    if not cabecalho.lower().startswith("bearer "):
        return None

    dados = validar_token_acesso(cabecalho[7:])

    return dados["usuario_id"] if dados else None


app = FastAPI(
    title="Sistema de Gestão de Estoque",
    description=(
        "API REST para gerenciamento de estoque, "
        "produtos, categorias, movimentações, "
        "relatórios, usuários, fornecedores, "
        "solicitações de compra, cotações, "
        "aprovações e compras"
    ),
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
def raiz():
    return {
        "mensagem": (
            "API do Sistema de Gestão de Estoque"
        )
    }


@app.get("/health")
def health_check():
    return {
        "status": "online"
    }


app.include_router(produtos_router)
app.include_router(categorias_router)
app.include_router(movimentacoes_router)
app.include_router(relatorios_router)
app.include_router(usuarios_router)
app.include_router(fornecedores_router)
app.include_router(solicitacoes_compra_router)
app.include_router(cotacoes_router)
app.include_router(compras_router)
app.include_router(formas_pagamento_router)
app.include_router(auditoria_router)
app.include_router(exportacoes_router)


PASTA_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


class FrontendSemCache(StaticFiles):
    """Obriga o navegador a confirmar com o servidor se os arquivos mudaram.

    Sem isso, depois de uma atualização o navegador pode continuar usando
    versões antigas do JavaScript e do CSS.
    """

    def file_response(self, *args, **kwargs):
        resposta = super().file_response(*args, **kwargs)
        resposta.headers["Cache-Control"] = "no-cache"
        return resposta

if PASTA_FRONTEND.is_dir():
    app.mount(
        "/app",
        FrontendSemCache(directory=PASTA_FRONTEND, html=True),
        name="frontend"
    )


@app.middleware("http")
async def registrar_requisicao(request: Request, chamar_proximo):
    id_requisicao = uuid.uuid4().hex[:12]
    inicio = time.perf_counter()

    try:
        resposta = await chamar_proximo(request)

    except Exception:
        logger.exception(
            "Erro não tratado id=%s %s %s",
            id_requisicao,
            request.method,
            request.url.path
        )

        resposta = JSONResponse(
            status_code=500,
            content={
                "detail": (
                    "Erro interno no servidor. "
                    f"Código para suporte: {id_requisicao}."
                )
            }
        )

    duracao_ms = round((time.perf_counter() - inicio) * 1000)
    caminho = request.url.path
    usuario_id = usuario_da_requisicao(request)

    resposta.headers["X-Request-ID"] = id_requisicao

    if not caminho.startswith("/app"):
        nivel = (
            logging.ERROR if resposta.status_code >= 500
            else logging.WARNING if resposta.status_code >= 400
            else logging.INFO
        )

        logger.log(
            nivel,
            "%s %s %s %dms usuario=%s id=%s",
            request.method,
            caminho,
            resposta.status_code,
            duracao_ms,
            usuario_id or "-",
            id_requisicao
        )

    if request.method in METODOS_AUDITADOS and not caminho.startswith("/app"):
        await run_in_threadpool(
            registrar_auditoria,
            id_requisicao,
            usuario_id,
            request.method,
            caminho[:300],
            resposta.status_code,
            request.client.host if request.client else None,
            duracao_ms
        )

    return resposta
