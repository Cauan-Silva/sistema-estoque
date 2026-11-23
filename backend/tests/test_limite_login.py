from backend.limite_login import LimitadorTentativas


class RelogioFalso:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora

    def avancar(self, segundos):
        self.agora += segundos


def criar_limitador(**opcoes):
    relogio = RelogioFalso()
    limitador = LimitadorTentativas(relogio=relogio, **opcoes)
    return limitador, relogio


CHAVE = ("login@teste.com", "127.0.0.1")


def test_libera_ate_cinco_falhas_e_bloqueia_a_partir_da_quinta():
    limitador, _ = criar_limitador()

    for _ in range(4):
        limitador.registrar_falha(CHAVE)
        assert limitador.bloqueado(CHAVE) is False

    limitador.registrar_falha(CHAVE)

    assert limitador.bloqueado(CHAVE) is True


def test_sucesso_zera_as_falhas():
    limitador, _ = criar_limitador()

    for _ in range(4):
        limitador.registrar_falha(CHAVE)

    limitador.limpar(CHAVE)
    limitador.registrar_falha(CHAVE)

    assert limitador.bloqueado(CHAVE) is False


def test_bloqueio_expira_depois_da_janela_de_quinze_minutos():
    limitador, relogio = criar_limitador()

    for _ in range(5):
        limitador.registrar_falha(CHAVE)

    relogio.avancar(15 * 60 - 1)
    assert limitador.bloqueado(CHAVE) is True

    relogio.avancar(2)
    assert limitador.bloqueado(CHAVE) is False


def test_falhas_antigas_saem_da_janela():
    limitador, relogio = criar_limitador()

    for _ in range(4):
        limitador.registrar_falha(CHAVE)

    relogio.avancar(15 * 60 + 1)
    limitador.registrar_falha(CHAVE)

    assert limitador.bloqueado(CHAVE) is False


def test_chaves_diferentes_sao_independentes():
    limitador, _ = criar_limitador()

    for _ in range(5):
        limitador.registrar_falha(CHAVE)

    assert limitador.bloqueado(("login@teste.com", "10.0.0.2")) is False
    assert limitador.bloqueado(("outro@teste.com", "127.0.0.1")) is False


def test_segundos_restantes_do_bloqueio():
    limitador, relogio = criar_limitador()

    for _ in range(5):
        limitador.registrar_falha(CHAVE)

    relogio.avancar(60)

    assert limitador.segundos_restantes(CHAVE) == 15 * 60 - 60
    assert limitador.segundos_restantes(("x", "y")) == 0


def test_memoria_limitada_ao_numero_maximo_de_chaves():
    limitador, _ = criar_limitador(max_chaves=3)

    for indice in range(10):
        limitador.registrar_falha((f"u{indice}@teste.com", "127.0.0.1"))

    assert limitador.quantidade_chaves() <= 3


def test_chaves_expiradas_sao_descartadas_antes_das_recentes():
    limitador, relogio = criar_limitador(max_chaves=2)

    limitador.registrar_falha(("antigo@teste.com", "ip"))
    relogio.avancar(15 * 60 + 1)

    for _ in range(5):
        limitador.registrar_falha(CHAVE)

    limitador.registrar_falha(("novo@teste.com", "ip"))

    assert limitador.quantidade_chaves() <= 2
    assert limitador.bloqueado(CHAVE) is True


def test_falhas_por_chave_nao_crescem_sem_limite():
    limitador, _ = criar_limitador()

    for _ in range(1000):
        limitador.registrar_falha(CHAVE)

    assert limitador.falhas(CHAVE) <= 5
