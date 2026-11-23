from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.autenticacao import (
    criar_token_acesso,
    obter_usuario_atual,
    obter_usuario_opcional,
)
from backend.limite_login import LimitadorTentativas
from backend.permissoes import (
    PERMISSOES,
    exigir,
    perfil_do_usuario,
    permissoes_do_perfil,
)
from backend.repositorio_usuario import (
    atualizar_acesso_usuario,
    buscar_usuario_por_email,
    cadastrar_usuario,
    existe_usuario,
    listar_usuarios,
    verificar_senha,
)
from backend.schemas.usuario import (
    ConfiguracaoInicialResposta,
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
def criar_usuario(
    usuario: UsuarioCriacao,
    usuario_logado=Depends(obter_usuario_opcional)
):
    """Cadastra um usuário.

    Sem login, só é possível criar o primeiro usuário do sistema, que vira
    ADMINISTRADOR. Depois disso, apenas administradores cadastram usuários.
    """
    if usuario_logado is not None:
        if perfil_do_usuario(usuario_logado) not in PERMISSOES[
            "usuarios.gerenciar"
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil não tem permissão para esta ação."
            )

        usuario_cadastrado, erro = cadastrar_usuario(
            nome=usuario.nome,
            email=usuario.email,
            senha=usuario.senha,
            perfil=usuario.perfil
        )
    else:
        usuario_cadastrado, erro = cadastrar_usuario(
            nome=usuario.nome,
            email=usuario.email,
            senha=usuario.senha,
            apenas_primeiro=True
        )

    if erro == "ja_existem_usuarios":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Entre como administrador para cadastrar usuários.",
            headers={"WWW-Authenticate": "Bearer"}
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


@router.get(
    "/configuracao-inicial",
    response_model=ConfiguracaoInicialResposta,
    summary="Indica se o sistema ainda não tem nenhum usuário"
)
def configuracao_inicial():
    existe = existe_usuario()

    if existe is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível consultar os usuários."
        )

    return {"precisa_configurar": not existe}


@router.post(
    "/login",
    response_model=TokenResposta
)
def login(usuario_login: UsuarioLogin, request: Request):
    return autenticar_usuario(
        email=usuario_login.email,
        senha=usuario_login.senha,
        ip=_ip_do_cliente(request)
    )


@router.post(
    "/token",
    response_model=TokenResposta,
    summary="Login via formulário (usado pelo Authorize do Swagger)"
)
def login_formulario(
    request: Request,
    formulario: OAuth2PasswordRequestForm = Depends()
):
    return autenticar_usuario(
        email=formulario.username.strip().lower(),
        senha=formulario.password,
        ip=_ip_do_cliente(request)
    )


# Até 5 senhas erradas por e-mail + IP em 15 minutos; depois, HTTP 429.
limitador_login = LimitadorTentativas(
    max_tentativas=5,
    janela_segundos=15 * 60
)


def _ip_do_cliente(request: Request) -> str:
    # Usa o IP da conexão, e não X-Forwarded-For, que o cliente pode forjar.
    # Atrás de um túnel/proxy todos chegam com o mesmo IP: o limite passa a
    # valer, na prática, por e-mail.
    return request.client.host if request.client else "desconhecido"


def autenticar_usuario(email: str, senha: str, ip: str = "desconhecido"):
    chave = (email.strip().lower(), ip)

    segundos = limitador_login.segundos_restantes(chave)

    if segundos > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Muitas tentativas de login sem sucesso. "
                "Aguarde 15 minutos e tente novamente."
            ),
            headers={"Retry-After": str(segundos)}
        )

    usuario = buscar_usuario_por_email(email)

    if usuario is None or not verificar_senha(senha, usuario[3]):
        limitador_login.registrar_falha(chave)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos."
        )

    limitador_login.limpar(chave)

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