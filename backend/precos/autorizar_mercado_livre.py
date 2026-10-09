"""Autoriza o aplicativo do Mercado Livre uma única vez.

Uso:
    python -m backend.precos.autorizar_mercado_livre

Pré-requisitos no .env: MERCADO_LIVRE_CLIENT_ID, MERCADO_LIVRE_CLIENT_SECRET e
MERCADO_LIVRE_REDIRECT_URI (o mesmo endereço cadastrado no aplicativo).
Depois disso, a API renova o token sozinha.
"""

import sys
from urllib.parse import parse_qs, urlencode, urlparse

from backend.database import aplicar_migracoes
from backend.precos.credenciais import salvar_credenciais
from backend.precos.mercado_livre import (
    NOME_CREDENCIAL,
    URL_AUTORIZACAO,
    ErroOAuth,
    credenciais_do_aplicativo,
    trocar_codigo,
)


def extrair_codigo(texto: str) -> str:
    texto = texto.strip()

    if texto.startswith("http"):
        valores = parse_qs(urlparse(texto).query).get("code")
        return valores[0] if valores else ""

    return texto


def main():
    app = credenciais_do_aplicativo()
    faltando = [nome for nome, valor in app.items() if not valor]

    if faltando:
        nomes = ", ".join(f"MERCADO_LIVRE_{nome.upper()}" for nome in faltando)
        print(f"Preencha no .env: {nomes}")
        return 1

    endereco = f"{URL_AUTORIZACAO}?" + urlencode(
        {"response_type": "code", "client_id": app["client_id"], "redirect_uri": app["redirect_uri"]}
    )

    print("1. Abra este endereço no navegador e autorize o aplicativo:\n")
    print(f"   {endereco}\n")
    print("2. Você será levado para o endereço de retorno do aplicativo.")
    print("   Copie o código TG-... que aparece (no httpbin.org, em \"code\") ou o endereço completo com ?code=.\n")

    codigo = extrair_codigo(input("Cole aqui o endereço ou só o código: "))

    if not codigo:
        print("Nenhum código encontrado. Tente de novo.")
        return 1

    try:
        access_token, refresh_token, expira_em = trocar_codigo(codigo)
    except ErroOAuth as erro:
        print(erro)
        return 1

    aplicar_migracoes()
    salvar_credenciais(NOME_CREDENCIAL, access_token, refresh_token, expira_em)

    print("\nPronto. O Mercado Livre está autorizado e o token será renovado automaticamente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
