from fastapi import FastAPI

from backend.database import criar_tabela
from backend.routes.produtos import router as produtos_router
from backend.routes.categorias import router as categorias_router
from backend.routes.movimentacoes import router as movimentacoes_router


app = FastAPI(
    title="Sistema de Gestão de Estoque",
    description="API REST para gerenciamento de estoque",
    version="1.0.0"
)


@app.on_event("startup")
def iniciar_aplicacao():
    criar_tabela()


@app.get("/")
def raiz():
    return {
        "mensagem": "API do Sistema de Gestão de Estoque"
    }


@app.get("/health")
def health_check():
    return {
        "status": "online"
    }


app.include_router(produtos_router)
app.include_router(categorias_router)
app.include_router(movimentacoes_router)