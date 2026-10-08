import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from backend.repositorio_usuario import buscar_usuario_por_id


CHAVE_SECRETA = os.getenv("JWT_SECRET_KEY")

if not CHAVE_SECRETA:
    raise RuntimeError(
        "JWT_SECRET_KEY não foi configurada."
    )


ALGORITMO = "HS256"
TEMPO_EXPIRACAO_MINUTOS = 30


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/usuarios/token"
)


def criar_token_acesso(
    usuario_id: int,
    email: str
) -> str:
    expiracao = datetime.now(timezone.utc) + timedelta(
        minutes=TEMPO_EXPIRACAO_MINUTOS
    )

    dados_token = {
        "sub": str(usuario_id),
        "email": email,
        "exp": expiracao
    }

    return jwt.encode(
        dados_token,
        CHAVE_SECRETA,
        algorithm=ALGORITMO
    )


def validar_token_acesso(token: str):
    try:
        dados = jwt.decode(
            token,
            CHAVE_SECRETA,
            algorithms=[ALGORITMO]
        )

        usuario_id = dados.get("sub")
        email = dados.get("email")

        if usuario_id is None or email is None:
            return None

        return {
            "usuario_id": int(usuario_id),
            "email": email
        }

    except (JWTError, ValueError):
        return None


def obter_usuario_atual(
    token: str = Depends(oauth2_scheme)
):
    dados_token = validar_token_acesso(token)

    if dados_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    usuario = buscar_usuario_por_id(
        dados_token["usuario_id"]
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if not usuario[4]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo."
        )

    return usuario