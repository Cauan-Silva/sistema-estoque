import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt


CHAVE_SECRETA = os.getenv(
    "JWT_SECRET_KEY",
    "chave-desenvolvimento"
)

ALGORITMO = "HS256"
TEMPO_EXPIRACAO_MINUTOS = 30


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