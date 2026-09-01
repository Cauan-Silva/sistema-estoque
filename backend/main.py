from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.database import criar_tabela

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabela()

    yield


app = FastAPI(
    title="Sistema de Gestão de Estoque",
    description=(
        "API REST para gerenciamento de estoque, "
        "produtos, categorias, movimentações "
        "e relatórios"
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