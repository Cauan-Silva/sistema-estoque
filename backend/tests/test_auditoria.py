from backend.tests.apoio_compras import novo_cliente


def test_resposta_tem_id_da_requisicao(client):
    resposta = client.get("/health")

    assert len(resposta.headers["x-request-id"]) == 12


def test_alteracoes_ficam_na_auditoria(cliente_autenticado):
    cliente = cliente_autenticado
    eu = cliente.get("/usuarios/me").json()

    criada = cliente.post("/categorias", json={"nome": "Auditada"})
    negada = novo_cliente("CONSULTA").post("/categorias", json={"nome": "Negada"})

    assert criada.status_code == 201
    assert negada.status_code == 403

    dados = cliente.get("/auditoria").json()
    registros = [r for r in dados["itens"] if r["caminho"] == "/categorias"]

    sucesso = next(r for r in registros if r["status"] == 201)
    falha = next(r for r in registros if r["status"] == 403)

    assert sucesso["metodo"] == "POST"
    assert sucesso["usuario_id"] == eu["id"]
    assert sucesso["usuario"] == eu["nome"]
    assert sucesso["id_requisicao"] == criada.headers["x-request-id"]
    assert falha["usuario"] == "Usuario Consulta"


def test_leituras_nao_entram_na_auditoria(cliente_autenticado):
    cliente_autenticado.get("/produtos")
    cliente_autenticado.get("/categorias")

    dados = cliente_autenticado.get("/auditoria").json()

    assert all(r["metodo"] != "GET" for r in dados["itens"])


def test_filtros_da_auditoria(cliente_autenticado):
    cliente = cliente_autenticado

    cliente.post("/categorias", json={"nome": "Filtro A"})
    cliente.post("/categorias", json={"nome": "Filtro A"})

    falhas = cliente.get("/auditoria?somente_falhas=true").json()
    posts = cliente.get("/auditoria?metodo=POST").json()

    assert falhas["total"] >= 1
    assert all(r["status"] >= 400 for r in falhas["itens"])
    assert all(r["metodo"] == "POST" for r in posts["itens"])


def test_somente_administrador_ve_auditoria(cliente_autenticado):
    for perfil in ("COMPRADOR", "APROVADOR", "ALMOXARIFE", "CONSULTA"):
        assert novo_cliente(perfil).get("/auditoria").status_code == 403
