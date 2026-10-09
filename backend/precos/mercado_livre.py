import logging
import os
import time

import httpx

from backend.precos.base import FontePreco, Oferta, ResultadoFonte
from backend.precos.credenciais import (
    ErroCredencial,
    existem_credenciais,
    expiracao,
    obter_token_valido,
)


logger = logging.getLogger(__name__)

URL_BUSCA = "https://api.mercadolibre.com/sites/MLB/search"
URL_TOKEN = "https://api.mercadolibre.com/oauth/token"
URL_AUTORIZACAO = "https://auth.mercadolivre.com.br/authorization"
NOME_CREDENCIAL = "mercado_livre"
VALIDADE_CACHE_SEGUNDOS = 600


class ErroOAuth(Exception):
    pass


def _variavel(nome: str) -> str:
    return os.getenv(nome, "").strip()


def credenciais_do_aplicativo():
    return {
        "client_id": _variavel("MERCADO_LIVRE_CLIENT_ID"),
        "client_secret": _variavel("MERCADO_LIVRE_CLIENT_SECRET"),
        "redirect_uri": _variavel("MERCADO_LIVRE_REDIRECT_URI"),
    }


def _pedir_token(cliente: httpx.Client, dados: dict):
    try:
        resposta = cliente.post(
            URL_TOKEN,
            data=dados,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        )
    except httpx.HTTPError as erro:
        raise ErroOAuth("Não foi possível conectar ao Mercado Livre.") from erro

    if resposta.status_code >= 400:
        try:
            detalhe = resposta.json().get("message") or resposta.json().get("error")
        except ValueError:
            detalhe = resposta.text[:200]
        raise ErroOAuth(f"O Mercado Livre recusou a autorização: {detalhe}")

    corpo = resposta.json()

    return corpo["access_token"], corpo.get("refresh_token"), expiracao(corpo.get("expires_in", 21600))


def trocar_codigo(codigo: str, cliente: httpx.Client | None = None):
    """Troca o código da autorização por tokens (usado uma vez, no comando de autorização)."""
    app = credenciais_do_aplicativo()
    proprio = cliente is None
    cliente = cliente or httpx.Client(timeout=10)

    try:
        return _pedir_token(
            cliente,
            {
                "grant_type": "authorization_code",
                "client_id": app["client_id"],
                "client_secret": app["client_secret"],
                "code": codigo.strip(),
                "redirect_uri": app["redirect_uri"],
            },
        )
    finally:
        if proprio:
            cliente.close()


class MercadoLivre(FontePreco):
    nome = "Mercado Livre"

    def __init__(self, cliente: httpx.Client | None = None):
        self._cliente = cliente
        self._cache: dict[tuple[str, int], tuple[float, ResultadoFonte]] = {}

    @property
    def url(self) -> str:
        return _variavel("MERCADO_LIVRE_URL") or URL_BUSCA

    def _usa_oauth(self) -> bool:
        app = credenciais_do_aplicativo()
        return bool(app["client_id"] and app["client_secret"])

    def configurada(self) -> bool:
        if self._usa_oauth():
            return existem_credenciais(NOME_CREDENCIAL)
        return bool(_variavel("MERCADO_LIVRE_TOKEN"))

    def _renovar(self, cliente):
        app = credenciais_do_aplicativo()

        def renovar(refresh_token):
            return _pedir_token(
                cliente,
                {
                    "grant_type": "refresh_token",
                    "client_id": app["client_id"],
                    "client_secret": app["client_secret"],
                    "refresh_token": refresh_token,
                },
            )

        return renovar

    def _token(self, cliente, forcar=False) -> str:
        if not self._usa_oauth():
            return _variavel("MERCADO_LIVRE_TOKEN")

        return obter_token_valido(NOME_CREDENCIAL, self._renovar(cliente), forcar=forcar)

    def _resultado(self, situacao, termo, mensagem=None, ofertas=None):
        return ResultadoFonte(
            fonte=self.nome,
            situacao=situacao,
            mensagem=mensagem,
            termo=termo,
            ofertas=ofertas or [],
        )

    def buscar(self, termo: str, limite: int = 10) -> ResultadoFonte:
        termo = termo.strip()

        if not self.configurada():
            mensagem = (
                "Autorize o aplicativo com: python -m backend.precos.autorizar_mercado_livre"
                if self._usa_oauth()
                else "Configure o Mercado Livre no .env para consultar preços de mercado."
            )
            return self._resultado("nao_configurada", termo, mensagem)

        chave = (termo.lower(), limite)
        guardado = self._cache.get(chave)

        if guardado and time.monotonic() - guardado[0] < VALIDADE_CACHE_SEGUNDOS:
            return guardado[1]

        cliente = self._cliente or httpx.Client(timeout=8)

        try:
            resposta = None

            for tentativa in range(2):
                token = self._token(cliente, forcar=tentativa > 0)

                resposta = cliente.get(
                    self.url,
                    params={"q": termo, "limit": limite},
                    headers={"Authorization": f"Bearer {token}"},
                )

                if resposta.status_code != 401 or not self._usa_oauth():
                    break

        except (ErroCredencial, ErroOAuth) as erro:
            logger.warning("Credencial do Mercado Livre indisponível: %s", erro)
            return self._resultado(
                "erro",
                termo,
                "A autorização do Mercado Livre expirou ou foi revogada. "
                "Rode de novo: python -m backend.precos.autorizar_mercado_livre",
            )

        except httpx.HTTPError as erro:
            logger.warning("Mercado Livre indisponível: %s", erro)
            return self._resultado("erro", termo, "Não foi possível conectar ao Mercado Livre.")

        finally:
            if self._cliente is None:
                cliente.close()

        if resposta.status_code in (401, 403):
            logger.warning("Mercado Livre recusou o acesso (HTTP %s).", resposta.status_code)
            return self._resultado(
                "erro",
                termo,
                "O Mercado Livre recusou o acesso. Confira a configuração e a autorização do aplicativo.",
            )

        if resposta.status_code == 429:
            return self._resultado("erro", termo, "Limite de consultas do Mercado Livre atingido. Tente mais tarde.")

        if resposta.status_code >= 400:
            logger.warning("Mercado Livre respondeu HTTP %s.", resposta.status_code)
            return self._resultado("erro", termo, f"O Mercado Livre respondeu com erro {resposta.status_code}.")

        try:
            dados = resposta.json()
        except ValueError:
            return self._resultado("erro", termo, "Resposta inesperada do Mercado Livre.")

        ofertas = []

        for item in dados.get("results", [])[:limite]:
            preco = item.get("price")

            if preco is None:
                continue

            ofertas.append(
                Oferta(
                    titulo=str(item.get("title", "")).strip(),
                    preco=float(preco),
                    moeda=item.get("currency_id") or "BRL",
                    link=item.get("permalink"),
                    vendedor=(item.get("seller") or {}).get("nickname"),
                    condicao={"new": "Novo", "used": "Usado"}.get(item.get("condition"), item.get("condition")),
                )
            )

        resultado = self._resultado(
            "ok",
            termo,
            None if ofertas else "Nenhuma oferta encontrada para este termo.",
            ofertas,
        )

        self._cache[chave] = (time.monotonic(), resultado)

        return resultado
