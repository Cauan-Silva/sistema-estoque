"""Mostra quais consultas do Mercado Livre estão liberadas para o aplicativo.

Uso:
    python -m backend.precos.diagnosticar_mercado_livre "switch 8 portas"

Não mostra tokens nem segredos, só o código HTTP de cada consulta.
"""

import sys

import httpx

from backend.precos.credenciais import ErroCredencial
from backend.precos.mercado_livre import URL_API, ErroOAuth, MercadoLivre

SIGNIFICADO = {
    200: "liberado",
    401: "token inválido ou expirado",
    403: "bloqueado para este aplicativo",
    404: "não encontrado",
    429: "limite de consultas atingido",
}


def main():
    termo = " ".join(sys.argv[1:]).strip() or "switch 8 portas"
    fonte = MercadoLivre()

    if not fonte.configurada():
        print("O Mercado Livre não está configurado. Rode: python -m backend.precos.autorizar_mercado_livre")
        return 1

    with httpx.Client(timeout=10) as cliente:
        try:
            consultas = [
                ("Conta autorizada", f"{URL_API}/users/me", None),
                ("Busca de anúncios", f"{URL_API}/sites/MLB/search", {"q": termo, "limit": 3}),
                ("Busca no catálogo", f"{URL_API}/products/search", {"status": "active", "site_id": "MLB", "q": termo, "limit": 3}),
            ]

            primeiro_produto = None

            for nome, url, params in consultas:
                resposta = fonte._consultar(cliente, url, params)
                print(f"{nome:<22} HTTP {resposta.status_code}  {SIGNIFICADO.get(resposta.status_code, '')}")

                if nome == "Conta autorizada" and resposta.status_code == 200:
                    print(f"{'':<22} conta: {resposta.json().get('nickname')}")

                if nome == "Busca no catálogo" and resposta.status_code == 200:
                    resultados = resposta.json().get("results", [])
                    print(f"{'':<22} {len(resultados)} produto(s) no catálogo")
                    primeiro_produto = resultados[0]["id"] if resultados else None

            if primeiro_produto:
                resposta = fonte._consultar(cliente, f"{URL_API}/products/{primeiro_produto}/items", {"limit": 3})
                print(f"{'Anúncios do produto':<22} HTTP {resposta.status_code}  {SIGNIFICADO.get(resposta.status_code, '')}")

        except (ErroCredencial, ErroOAuth) as erro:
            print(f"Problema com a autorização: {erro}")
            return 1
        except httpx.HTTPError as erro:
            print(f"Sem conexão com o Mercado Livre: {erro}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
