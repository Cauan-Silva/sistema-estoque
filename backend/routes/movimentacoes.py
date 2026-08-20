from fastapi import APIRouter


router = APIRouter(
    prefix="/movimentacoes",
    tags=["Movimentações"]
)