import logging
import os
import time

import httpx

from backend.precos.base import FontePreco, Oferta, ResultadoFonte


logger = logging.getLogger(__name__)

URL_PADRAO = "https://api.mercadolibre.com/sites/MLB/search"
VALIDADE_CACHE_SEGUNDOS = 600


class MercadoLivre(FontePreco):
    nome = "Mercado Livre"

    def __init__(self, cliente: httpx.Client | None = None):
        self._cliente = cliente
        self._cache: dict[tuple[str, int], tuple[float, ResultadoFonte]] = {}

    @property
    def token(self) -> str:
        return os.getenv("MERCADO_LIVRE_TOKEN", "").strip()

    @property
    def url(self) -> str:
        return os.getenv("MERCADO_LIVRE_URL", URL_PADRAO).strip() or URL_PADRAO

    def configurada(self) -> bool:
        return bool(self.token)

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
            return self._resultado(
                "nao_configurada",
                termo,
                "Defina MERCADO_LIVRE_TOKEN no .env para consultar o Mercado Livre.",
            )

        chave = (termo.lower(), limite)
        guardado = self._cache.get(chave)

        if guardado and time.monotonic() - guardado[0] < VALIDADE_CACHE_SEGUNDOS:
            return guardado[1]

        cliente = self._cliente or httpx.Client(timeout=8)

        try:
            resposta = cliente.get(
                self.url,
                params={"q": termo, "limit": limite},
                headers={"Authorization": f"Bearer {self.token}"},
            )

        except httpx.HTTPError as erro:
            logger.warning("Mercado Livre indisponível: %s", erro)
            return self._resultado("erro", termo, "Não foi possível conectar ao Mercado Livre.")

        finally:
            if self._cliente is None:
                cliente.close()

        if resposta.status_code in (401, 403):
            logger.warning("Mercado Livre recusou o token (HTTP %s).", resposta.status_code)
            return self._resultado(
                "erro",
                termo,
                "O Mercado Livre recusou o acesso. Confira se o MERCADO_LIVRE_TOKEN é válido e não expirou.",
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
