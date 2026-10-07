from fastapi import APIRouter, Depends, HTTPException, status

from backend.autenticacao import (
    criar_token_acesso,
    obter_usuario_atual,
)
from backend.repositorio_usuario import (
    buscar_usuario_por_email,
    cadastrar_usuario,
    verificar_senha,
)
from backend.schemas.usuario import (
    TokenResposta,
    UsuarioCriacao,
    UsuarioLogin,
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


@router.post(
    "/login",
    response_model=TokenResposta
)
def login(usuario_login: UsuarioLogin):
    usuario = buscar_usuario_por_email(
        usuario_login.email
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos."
        )

    senha_valida = verificar_senha(
        usuario_login.senha,
        usuario[3]
    )

    if not senha_valida:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos."
        )

    if not usuario[4]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo."
        )

    token = criar_token_acesso(
        usuario_id=usuario[0],
        email=usuario[2]
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get(
    "/me",
    response_model=UsuarioResposta
)
def usuario_atual(
    usuario=Depends(obter_usuario_atual)
):
    return {
        "id": usuario[0],
        "nome": usuario[1],
        "email": usuario[2],
        "ativo": usuario[4],
        "data_criacao": usuario[5]
    }