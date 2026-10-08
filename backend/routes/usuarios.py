from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.autenticacao import (
    criar_token_acesso,
    obter_usuario_atual,
)
from backend.permissoes import exigir, permissoes_do_perfil
from backend.repositorio_usuario import (
    atualizar_acesso_usuario,
    buscar_usuario_por_email,
    cadastrar_usuario,
    listar_usuarios,
    verificar_senha,
)
from backend.schemas.usuario import (
    TokenResposta,
    UsuarioAcesso,
    UsuarioAtualResposta,
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
        "data_criacao": usuario_cadastrado[4],
        "perfil": usuario_cadastrado[5]
    }


@router.post(
    "/login",
    response_model=TokenResposta
)
def login(usuario_login: UsuarioLogin):
    return autenticar_usuario(
        email=usuario_login.email,
        senha=usuario_login.senha
    )


@router.post(
    "/token",
    response_model=TokenResposta,
    summary="Login via formulário (usado pelo Authorize do Swagger)"
)
def login_formulario(
    formulario: OAuth2PasswordRequestForm = Depends()
):
    return autenticar_usuario(
        email=formulario.username.strip().lower(),
        senha=formulario.password
    )


def autenticar_usuario(email: str, senha: str):
    usuario = buscar_usuario_por_email(email)

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos."
        )

    senha_valida = verificar_senha(
        senha,
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
    response_model=UsuarioAtualResposta
)
def usuario_atual(
    usuario=Depends(obter_usuario_atual)
):
    return {
        "id": usuario[0],
        "nome": usuario[1],
        "email": usuario[2],
        "ativo": usuario[4],
        "data_criacao": usuario[5],
        "perfil": usuario[6],
        "permissoes": permissoes_do_perfil(usuario[6])
    }


@router.get(
    "",
    response_model=list[UsuarioResposta],
    dependencies=[exigir("usuarios.gerenciar")]
)
def listar():
    usuarios = listar_usuarios()

    if usuarios is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível listar os usuários."
        )

    return usuarios


@router.patch(
    "/{usuario_id}",
    response_model=UsuarioResposta
)
def alterar_acesso(
    usuario_id: int,
    dados: UsuarioAcesso,
    administrador=exigir("usuarios.gerenciar")
):
    if usuario_id == administrador[0] and (
        (dados.perfil is not None and dados.perfil != "ADMINISTRADOR")
        or dados.ativo is False
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Você não pode remover o seu próprio acesso de "
                "administrador. Peça a outro administrador."
            )
        )

    usuario, erro = atualizar_acesso_usuario(
        usuario_id,
        dados.perfil,
        dados.ativo
    )

    if erro == "usuario_nao_encontrado":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )

    if erro is not None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível alterar o acesso do usuário."
        )

    return usuario