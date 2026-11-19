import bcrypt

from backend.autenticacao import validar_token_acesso
from backend.repositorio_usuario import (
    buscar_usuario_por_email,
    buscar_usuario_por_id,
    cadastrar_usuario,
    gerar_hash_senha,
    verificar_senha,
)


def test_gerar_hash_senha():
    senha = "senha123"

    senha_hash = gerar_hash_senha(senha)

    assert senha_hash != senha
    assert bcrypt.checkpw(
        senha.encode("utf-8"),
        senha_hash.encode("utf-8")
    )


def test_verificar_senha_correta():
    senha = "senha123"
    senha_hash = gerar_hash_senha(senha)

    resultado = verificar_senha(
        senha,
        senha_hash
    )

    assert resultado is True


def test_verificar_senha_incorreta():
    senha_hash = gerar_hash_senha("senha123")

    resultado = verificar_senha(
        "senha_errada",
        senha_hash
    )

    assert resultado is False


def test_cadastrar_usuario():
    usuario, erro = cadastrar_usuario(
        nome="Usuario Teste",
        email="usuario@teste.com",
        senha="senha123"
    )

    assert erro is None
    assert usuario is not None
    assert usuario[1] == "Usuario Teste"
    assert usuario[2] == "usuario@teste.com"
    assert usuario[3] is True


def test_buscar_usuario_por_email():
    cadastrar_usuario(
        nome="Usuario Busca",
        email="busca@teste.com",
        senha="senha123"
    )

    usuario = buscar_usuario_por_email(
        "busca@teste.com"
    )

    assert usuario is not None
    assert usuario[1] == "Usuario Busca"
    assert usuario[2] == "busca@teste.com"

    senha_hash = usuario[3]

    assert bcrypt.checkpw(
        "senha123".encode("utf-8"),
        senha_hash.encode("utf-8")
    )

def test_buscar_usuario_por_id():
    usuario_cadastrado, erro = cadastrar_usuario(
        nome="Usuario Busca ID",
        email="busca-id@teste.com",
        senha="senha123"
    )

    assert erro is None
    assert usuario_cadastrado is not None

    usuario = buscar_usuario_por_id(
        usuario_cadastrado[0]
    )

    assert usuario is not None
    assert usuario[0] == usuario_cadastrado[0]
    assert usuario[1] == "Usuario Busca ID"
    assert usuario[2] == "busca-id@teste.com"
    assert usuario[4] is True

def test_email_convertido_para_minusculo():
    usuario, erro = cadastrar_usuario(
        nome="Usuario Email",
        email="EMAIL@TESTE.COM",
        senha="senha123"
    )

    assert erro is None
    assert usuario[2] == "email@teste.com"


def test_email_duplicado():
    cadastrar_usuario(
        nome="Primeiro Usuario",
        email="duplicado@teste.com",
        senha="senha123"
    )

    usuario, erro = cadastrar_usuario(
        nome="Segundo Usuario",
        email="duplicado@teste.com",
        senha="outrasenha123"
    )

    assert usuario is None
    assert erro == "email_duplicado"


def test_api_cadastrar_usuario(client):
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Usuario API",
            "email": "api@teste.com",
            "senha": "senha123"
        }
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["nome"] == "Usuario API"
    assert dados["email"] == "api@teste.com"
    assert dados["ativo"] is True
    assert "id" in dados
    assert "data_criacao" in dados


def test_api_nao_retorna_senha(client):
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Usuario Seguro",
            "email": "seguro@teste.com",
            "senha": "senha123"
        }
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert "senha" not in dados
    assert "senha_hash" not in dados


def test_api_email_duplicado(client):
    dados = {
        "nome": "Usuario Duplicado",
        "email": "duplicado-api@teste.com",
        "senha": "senha123"
    }

    primeira_resposta = client.post(
        "/usuarios",
        json=dados
    )

    token = client.post(
        "/usuarios/login",
        json={"email": dados["email"], "senha": dados["senha"]}
    ).json()["access_token"]

    segunda_resposta = client.post(
        "/usuarios",
        json=dados,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert primeira_resposta.status_code == 201
    assert segunda_resposta.status_code == 409

    assert segunda_resposta.json() == {
        "detail": "E-mail já cadastrado."
    }


def test_api_email_invalido(client):
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Usuario Email Invalido",
            "email": "email-invalido",
            "senha": "senha123"
        }
    )

    assert resposta.status_code == 422


def test_api_senha_curta(client):
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Usuario Senha Curta",
            "email": "senha@teste.com",
            "senha": "123"
        }
    )

    assert resposta.status_code == 422


def test_login_com_sucesso(client):
    cadastro = client.post(
        "/usuarios",
        json={
            "nome": "Usuario Login",
            "email": "login@teste.com",
            "senha": "senha123"
        }
    )

    assert cadastro.status_code == 201

    usuario_id = cadastro.json()["id"]

    resposta = client.post(
        "/usuarios/login",
        json={
            "email": "login@teste.com",
            "senha": "senha123"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert "access_token" in dados
    assert dados["token_type"] == "bearer"

    token = dados["access_token"]

    assert isinstance(token, str)
    assert token != ""

    dados_token = validar_token_acesso(token)

    assert dados_token is not None
    assert dados_token["usuario_id"] == usuario_id
    assert dados_token["email"] == "login@teste.com"


def test_login_senha_incorreta(client):
    cadastro = client.post(
        "/usuarios",
        json={
            "nome": "Usuario Senha Errada",
            "email": "senha-errada@teste.com",
            "senha": "senha123"
        }
    )

    assert cadastro.status_code == 201

    resposta = client.post(
        "/usuarios/login",
        json={
            "email": "senha-errada@teste.com",
            "senha": "senhaerrada"
        }
    )

    assert resposta.status_code == 401

    assert resposta.json() == {
        "detail": "E-mail ou senha inválidos."
    }


def test_login_email_inexistente(client):
    resposta = client.post(
        "/usuarios/login",
        json={
            "email": "naoexiste@teste.com",
            "senha": "senha123"
        }
    )

    assert resposta.status_code == 401

    assert resposta.json() == {
        "detail": "E-mail ou senha inválidos."
    }

def test_token_formulario_com_sucesso(client):
    cadastro = client.post(
        "/usuarios",
        json={
            "nome": "Usuario Swagger",
            "email": "swagger@teste.com",
            "senha": "senha123"
        }
    )

    assert cadastro.status_code == 201

    resposta = client.post(
        "/usuarios/token",
        data={
            "username": "Swagger@Teste.com",
            "password": "senha123"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["token_type"] == "bearer"

    rota_protegida = client.get(
        "/produtos",
        headers={
            "Authorization": f"Bearer {dados['access_token']}"
        }
    )

    assert rota_protegida.status_code == 200


def test_token_formulario_senha_incorreta(client):
    client.post(
        "/usuarios",
        json={
            "nome": "Usuario Swagger",
            "email": "swagger@teste.com",
            "senha": "senha123"
        }
    )

    resposta = client.post(
        "/usuarios/token",
        data={
            "username": "swagger@teste.com",
            "password": "senhaerrada"
        }
    )

    assert resposta.status_code == 401

    assert resposta.json() == {
        "detail": "E-mail ou senha inválidos."
    }


def test_swagger_aponta_para_endpoint_de_token(client):
    esquema = client.get("/openapi.json").json()

    fluxo = esquema["components"]["securitySchemes"][
        "OAuth2PasswordBearer"
    ]["flows"]["password"]

    assert fluxo["tokenUrl"] == "/usuarios/token"


# ---------- Cadastro restrito a administradores ----------

def test_configuracao_inicial_indica_quando_nao_ha_usuarios(client):
    antes = client.get("/usuarios/configuracao-inicial")

    assert antes.status_code == 200
    assert antes.json() == {"precisa_configurar": True}

    client.post(
        "/usuarios",
        json={"nome": "Primeiro", "email": "primeiro@teste.com", "senha": "senha123"}
    )

    depois = client.get("/usuarios/configuracao-inicial")

    assert depois.json() == {"precisa_configurar": False}


def test_primeiro_cadastro_sem_login_cria_administrador(client):
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Primeiro Admin",
            "email": "admin@teste.com",
            "senha": "senha123",
            "perfil": "CONSULTA"
        }
    )

    assert resposta.status_code == 201
    assert resposta.json()["perfil"] == "ADMINISTRADOR"


def test_cadastro_sem_login_bloqueado_quando_ja_existe_usuario(client):
    client.post(
        "/usuarios",
        json={"nome": "Primeiro", "email": "primeiro@teste.com", "senha": "senha123"}
    )

    resposta = client.post(
        "/usuarios",
        json={"nome": "Intruso", "email": "intruso@teste.com", "senha": "senha123"}
    )

    assert resposta.status_code == 401
    assert resposta.json() == {
        "detail": "Entre como administrador para cadastrar usuários."
    }
    assert buscar_usuario_por_email("intruso@teste.com") is None


def test_cadastro_com_token_invalido_e_recusado(client):
    resposta = client.post(
        "/usuarios",
        json={"nome": "Alguem", "email": "alguem@teste.com", "senha": "senha123"},
        headers={"Authorization": "Bearer token.invalido.teste"}
    )

    assert resposta.status_code == 401
    assert buscar_usuario_por_email("alguem@teste.com") is None


def test_usuario_sem_permissao_nao_cadastra_usuarios(cliente_autenticado):
    from backend.tests.apoio_compras import novo_cliente

    consulta = novo_cliente("CONSULTA")

    resposta = consulta.post(
        "/usuarios",
        json={"nome": "Outro", "email": "outro@teste.com", "senha": "senha123"}
    )

    assert resposta.status_code == 403
    assert buscar_usuario_por_email("outro@teste.com") is None


def test_administrador_cadastra_usuario_como_consulta_por_padrao(cliente_autenticado):
    resposta = cliente_autenticado.post(
        "/usuarios",
        json={"nome": "Novo", "email": "novo@teste.com", "senha": "senha123"}
    )

    assert resposta.status_code == 201
    assert resposta.json()["perfil"] == "CONSULTA"


def test_administrador_cadastra_usuario_com_perfil(cliente_autenticado):
    resposta = cliente_autenticado.post(
        "/usuarios",
        json={
            "nome": "Compradora",
            "email": "compradora@teste.com",
            "senha": "senha123",
            "perfil": "COMPRADOR"
        }
    )

    assert resposta.status_code == 201
    assert resposta.json()["perfil"] == "COMPRADOR"


def test_administrador_recebe_409_para_email_duplicado(cliente_autenticado):
    resposta = cliente_autenticado.post(
        "/usuarios",
        json={
            "nome": "Repetido",
            "email": "usuario.testes@teste.com",
            "senha": "senha123"
        }
    )

    assert resposta.status_code == 409


def test_primeiro_administrador_concorrente_cria_apenas_um():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from backend.database import conectar

    quantidade = 8
    barreira = Barrier(quantidade)

    def cadastrar(indice):
        barreira.wait()
        return cadastrar_usuario(
            nome=f"Admin {indice}",
            email=f"admin{indice}@teste.com",
            senha="senha123",
            apenas_primeiro=True
        )

    with ThreadPoolExecutor(max_workers=quantidade) as executor:
        resultados = list(executor.map(cadastrar, range(quantidade)))

    sucessos = [usuario for usuario, erro in resultados if erro is None]
    recusas = [erro for usuario, erro in resultados if erro is not None]

    assert len(sucessos) == 1
    assert sucessos[0][5] == "ADMINISTRADOR"
    assert set(recusas) == {"ja_existem_usuarios"}

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios;")
    total = cursor.fetchone()[0]
    cursor.close()
    conexao.close()

    assert total == 1


# ---------- Proteção contra força bruta no login ----------

MENSAGEM_BLOQUEIO = (
    "Muitas tentativas de login sem sucesso. "
    "Aguarde 15 minutos e tente novamente."
)


def _criar_usuario_login(client):
    cadastro = client.post(
        "/usuarios",
        json={"nome": "Usuario Bloqueio", "email": "bloqueio@teste.com", "senha": "senha123"}
    )
    assert cadastro.status_code == 201


def _errar_senha(client, vezes):
    for _ in range(vezes):
        resposta = client.post(
            "/usuarios/login",
            json={"email": "bloqueio@teste.com", "senha": "senhaerrada"}
        )
        assert resposta.status_code == 401


def test_login_bloqueado_apos_cinco_falhas(client):
    _criar_usuario_login(client)
    _errar_senha(client, 5)

    resposta = client.post(
        "/usuarios/login",
        json={"email": "bloqueio@teste.com", "senha": "senha123"}
    )

    assert resposta.status_code == 429
    assert resposta.json() == {"detail": MENSAGEM_BLOQUEIO}
    assert int(resposta.headers["Retry-After"]) > 0


def test_login_bloqueado_vale_para_o_endpoint_de_formulario(client):
    _criar_usuario_login(client)
    _errar_senha(client, 5)

    resposta = client.post(
        "/usuarios/token",
        data={"username": "Bloqueio@Teste.com", "password": "senha123"}
    )

    assert resposta.status_code == 429


def test_login_com_sucesso_zera_as_falhas(client):
    _criar_usuario_login(client)
    _errar_senha(client, 4)

    sucesso = client.post(
        "/usuarios/login",
        json={"email": "bloqueio@teste.com", "senha": "senha123"}
    )
    assert sucesso.status_code == 200

    _errar_senha(client, 4)

    resposta = client.post(
        "/usuarios/login",
        json={"email": "bloqueio@teste.com", "senha": "senha123"}
    )

    assert resposta.status_code == 200


def test_bloqueio_de_login_expira_depois_de_quinze_minutos(client, monkeypatch):
    from backend.routes import usuarios as rotas_usuarios

    agora = [1000.0]
    monkeypatch.setattr(rotas_usuarios.limitador_login, "relogio", lambda: agora[0])

    _criar_usuario_login(client)
    _errar_senha(client, 5)

    agora[0] += 15 * 60 + 1

    resposta = client.post(
        "/usuarios/login",
        json={"email": "bloqueio@teste.com", "senha": "senha123"}
    )

    assert resposta.status_code == 200


def test_falhas_em_email_inexistente_tambem_bloqueiam(client):
    for _ in range(5):
        client.post(
            "/usuarios/login",
            json={"email": "fantasma@teste.com", "senha": "senhaerrada"}
        )

    resposta = client.post(
        "/usuarios/login",
        json={"email": "fantasma@teste.com", "senha": "senhaerrada"}
    )

    assert resposta.status_code == 429
