from fastapi import APIRouter, HTTPException, status

from backend.repositorio_usuario import cadastrar_usuario
from backend.schemas.usuario import (
    UsuarioCriacao,
    UsuarioResposta,
)


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)


@router.post(
    "",
    response_model=UsuarioResposta,
    status_code=status.HTTP_201_CREATED
)
def criar_usuario(usuario: UsuarioCriacao):
    usuario_cadastrado, erro = cadastrar_usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha=usuario.senha
    )

    if erro == "email_duplicado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado."
        )

    if erro is not None or usuario_cadastrado is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível cadastrar o usuário."
        )

    return {
        "id": usuario_cadastrado[0],
        "nome": usuario_cadastrado[1],
        "email": usuario_cadastrado[2],
        "ativo": usuario_cadastrado[3],
        "data_criacao": usuario_cadastrado[4]
    }