"""Limite de tentativas de login, em memória, contra ataques de força bruta.

Cada chave (por exemplo, e-mail + IP) pode errar a senha até `max_tentativas`
vezes dentro de `janela_segundos`; depois disso fica bloqueada até a falha mais
antiga sair da janela. Um login com sucesso zera a contagem.

A memória é limitada: cada chave guarda no máximo `max_tentativas` horários e
o total de chaves não passa de `max_chaves` (as expiradas saem primeiro; se
ainda faltar espaço, saem as mais antigas).

O estado vive no processo: reiniciar a API zera os bloqueios e, com vários
workers, cada um conta as falhas separadamente.
"""

import time
from collections import OrderedDict, deque
from threading import Lock


class LimitadorTentativas:
    def __init__(
        self,
        max_tentativas: int = 5,
        janela_segundos: float = 15 * 60,
        max_chaves: int = 10_000,
        relogio=time.monotonic,
    ):
        self.max_tentativas = max_tentativas
        self.janela_segundos = janela_segundos
        self.max_chaves = max_chaves
        self.relogio = relogio
        self._falhas: OrderedDict = OrderedDict()
        self._trava = Lock()

    def _descartar_expiradas(self, chave, agora) -> deque | None:
        falhas = self._falhas.get(chave)

        if falhas is None:
            return None

        while falhas and agora - falhas[0] >= self.janela_segundos:
            falhas.popleft()

        if not falhas:
            del self._falhas[chave]
            return None

        return falhas

    def _liberar_espaco(self, agora):
        if len(self._falhas) <= self.max_chaves:
            return

        for chave in list(self._falhas):
            self._descartar_expiradas(chave, agora)

        while len(self._falhas) > self.max_chaves:
            self._falhas.popitem(last=False)

    def registrar_falha(self, chave):
        with self._trava:
            agora = self.relogio()
            falhas = self._descartar_expiradas(chave, agora)

            if falhas is None:
                falhas = deque(maxlen=self.max_tentativas)
                self._falhas[chave] = falhas
            else:
                self._falhas.move_to_end(chave)

            falhas.append(agora)
            self._liberar_espaco(agora)

    def bloqueado(self, chave) -> bool:
        return self.segundos_restantes(chave) > 0

    def segundos_restantes(self, chave) -> int:
        with self._trava:
            agora = self.relogio()
            falhas = self._descartar_expiradas(chave, agora)

            if falhas is None or len(falhas) < self.max_tentativas:
                return 0

            restante = self.janela_segundos - (agora - falhas[0])

            return max(1, int(restante + 0.999))

    def falhas(self, chave) -> int:
        with self._trava:
            falhas = self._descartar_expiradas(chave, self.relogio())
            return 0 if falhas is None else len(falhas)

    def limpar(self, chave):
        with self._trava:
            self._falhas.pop(chave, None)

    def limpar_tudo(self):
        with self._trava:
            self._falhas.clear()

    def quantidade_chaves(self) -> int:
        with self._trava:
            return len(self._falhas)
