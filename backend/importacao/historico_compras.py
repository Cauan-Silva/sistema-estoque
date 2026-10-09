"""Importa o histórico de compras do sistema antigo (CSV "Itens do Pedido de Compra").

Uso (recomendado num banco separado, para não misturar com os dados atuais):

    python -m backend.importacao.historico_compras Itens_do_Pedido_de_Compra.csv \\
        --banco sistema_estoque_demo --email voce@empresa.com --senha "sua-senha"

Cada pedido passa pelas mesmas regras do sistema (solicitação, cotação,
aprovação, compra e recebimento), com as datas originais. Solicitantes e
aprovadores do arquivo viram usuários inativos (só para o histórico ficar
com os nomes certos). Fornecedores, categorias ("Grupo do Item"), produtos
e formas de pagamento que faltarem são criados.

Opções:
  --estoque-minimo   calcula o estoque mínimo dos itens de estoque pela compra
                     média mensal (metade dela); os demais ficam com 0 (avulsos)
  --simular-consumo  cria saídas de estoque simuladas depois de cada entrega,
                     para o painel e a sugestão de compra terem o que mostrar.
                     São dados inventados: use só em banco de demonstração.
"""

import argparse
import collections
import getpass
import os
import random
import re
import secrets
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta

GRUPOS_DE_ESTOQUE = {
    "Estoque", "ONU", "Roteadores", "GBIC", "Cabos", "Splitter", "Fontes",
    "Equipamento de proteção individual",
}
DOMINIO_HISTORICO = "@historico.sistema-estoque.app"
MARCA_PEDIDO = "Pedido % do sistema antigo%"

# Saídas simuladas: sem usuário, sem recebimento e com hora cheia.
CONDICAO_CONSUMO_SIMULADO = """
    tipo = 'SAIDA' AND usuario_id IS NULL AND recebimento_id IS NULL
    AND data_movimentacao = date_trunc('hour', data_movimentacao)
"""


def desfazer_importacao(conexao) -> tuple[int, int]:
    """Apaga as solicitações importadas, as entradas dos recebimentos delas e o
    consumo simulado, devolvendo o estoque ao que era. Cadastros (produtos,
    fornecedores, categorias, formas de pagamento e usuários) ficam."""
    cursor = conexao.cursor()
    cursor.execute(
        "CREATE TEMP TABLE hist_solicitacoes ON COMMIT DROP AS "
        "SELECT id FROM solicitacoes_compra WHERE observacao LIKE %s;",
        (MARCA_PEDIDO,),
    )
    cursor.execute(
        f"""
        CREATE TEMP TABLE hist_movimentos ON COMMIT DROP AS
        SELECT m.id, m.produto_id, m.tipo, m.quantidade
        FROM movimentacoes m
        JOIN recebimentos r ON r.id = m.recebimento_id
        JOIN compras c ON c.id = r.compra_id
        WHERE c.solicitacao_id IN (SELECT id FROM hist_solicitacoes)
        UNION
        SELECT id, produto_id, tipo, quantidade FROM movimentacoes WHERE {CONDICAO_CONSUMO_SIMULADO};
        """
    )
    cursor.execute(
        """
        UPDATE produtos p
        SET quantidade = GREATEST(0, p.quantidade - x.saldo)
        FROM (
            SELECT produto_id, SUM(CASE WHEN tipo = 'ENTRADA' THEN quantidade ELSE -quantidade END) AS saldo
            FROM hist_movimentos GROUP BY produto_id
        ) x
        WHERE p.id = x.produto_id;
        """
    )
    cursor.execute("DELETE FROM movimentacoes WHERE id IN (SELECT id FROM hist_movimentos);")
    movimentos = cursor.rowcount
    cursor.execute(
        "DELETE FROM recebimentos WHERE compra_id IN "
        "(SELECT id FROM compras WHERE solicitacao_id IN (SELECT id FROM hist_solicitacoes));"
    )
    cursor.execute("DELETE FROM compras WHERE solicitacao_id IN (SELECT id FROM hist_solicitacoes);")
    cursor.execute("UPDATE solicitacoes_compra SET cotacao_aprovada_id = NULL WHERE id IN (SELECT id FROM hist_solicitacoes);")
    cursor.execute("DELETE FROM solicitacoes_compra WHERE id IN (SELECT id FROM hist_solicitacoes);")
    solicitacoes = cursor.rowcount
    conexao.commit()
    return solicitacoes, movimentos


def _normalizar(texto: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper().split())


def _numero(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", "."))


def _data(texto: str) -> date:
    return datetime.strptime(texto[:10], "%d/%m/%Y").date()


def _criar_banco_se_preciso(nome: str):
    import psycopg2

    conexao = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), database="postgres",
    )
    conexao.autocommit = True
    cursor = conexao.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (nome,))
    if cursor.fetchone() is None:
        cursor.execute(f'CREATE DATABASE "{nome}";')
        print(f"Banco {nome} criado.")
    conexao.close()


class Importador:
    def __init__(self, cliente, saida=print):
        self.cliente = cliente
        self.saida = saida
        self.erros = []
        # O login vale 30 minutos e a importação pode demorar mais que isso em
        # máquinas lentas: o token vencido é trocado por um novo e a chamada é
        # repetida. Quem guardou o token antigo continua usando-o como chave.
        self.donos = {}
        self.substitutos = {}

    # ---------- chamadas à API ----------

    def _vigente(self, token):
        while token in self.substitutos:
            token = self.substitutos[token]
        return token

    def _renovar(self, token):
        from backend.autenticacao import criar_token_acesso

        novo = criar_token_acesso(*self.donos[token])
        self.donos[novo] = self.donos[token]
        self.substitutos[token] = novo
        return novo

    def _registrar(self, token, usuario_id, email):
        self.donos[token] = (usuario_id, email)
        return token

    def chamar(self, metodo, caminho, token, esperado=(200, 201, 204), **kw):
        token = self._vigente(token)
        resposta = self.cliente.request(metodo, caminho, headers={"Authorization": f"Bearer {token}"}, **kw)
        if resposta.status_code == 401 and token in self.donos:
            token = self._renovar(token)
            resposta = self.cliente.request(metodo, caminho, headers={"Authorization": f"Bearer {token}"}, **kw)
        if resposta.status_code not in esperado:
            self.erros.append(f"{metodo} {caminho}: {resposta.status_code} {resposta.text[:200]}")
        return resposta

    def entrar(self, email, senha):
        resposta = self.cliente.post("/usuarios/login", json={"email": email, "senha": senha})
        if resposta.status_code != 200:
            raise SystemExit(f"Não foi possível entrar com {email}: {resposta.json().get('detail')}")
        from jose import jwt

        token = resposta.json()["access_token"]
        dados = jwt.get_unverified_claims(token)
        return self._registrar(token, int(dados["sub"]), dados["email"])

    def token_de(self, usuario_id, email):
        from backend.autenticacao import criar_token_acesso

        return self._registrar(criar_token_acesso(usuario_id, email), usuario_id, email)

    # ---------- passos ----------

    def preparar_administrador(self, email, senha, nome):
        resposta = self.cliente.post("/usuarios", json={"nome": nome, "email": email, "senha": senha})
        if resposta.status_code == 201:
            self.saida(f"Usuário {email} criado.")
        self.admin = self.entrar(email, senha)
        eu = self.chamar("GET", "/usuarios/me", self.admin).json()
        if eu["perfil"] != "ADMINISTRADOR":
            raise SystemExit(f"{email} precisa ser Administrador para importar (perfil atual: {eu['perfil']}).")
        self.admin_nome = eu["nome"]

    def preparar_pessoas(self, registros):
        """Solicitantes e aprovadores viram usuários; ficam inativos no fim."""
        solicitantes = {r["Solicitante"] for r in registros}
        aprovadores = {r["Aprovador"] for r in registros if r["Aprovador"]}
        existentes = {u["nome"].upper(): u for u in self.chamar("GET", "/usuarios", self.admin).json()}
        self.pessoas = {}
        self.criados = []

        for nome in sorted(solicitantes | aprovadores):
            if nome.upper() == self.admin_nome.upper():
                self.pessoas[nome] = (self.admin, True)
                continue
            perfil = "ADMINISTRADOR" if nome in solicitantes and nome in aprovadores else (
                "COMPRADOR" if nome in solicitantes else "APROVADOR")
            existente = existentes.get(nome.upper())
            if existente and existente["email"].endswith(DOMINIO_HISTORICO):
                # Criado numa importação anterior: reativa enquanto importa.
                self.chamar("PATCH", f"/usuarios/{existente['id']}", self.admin, json={"ativo": True, "perfil": perfil})
                self.pessoas[nome] = (self.token_de(existente["id"], existente["email"]), perfil == "ADMINISTRADOR")
                self.criados.append(existente["id"])
                continue
            if existente:
                # Usuário de verdade com o mesmo nome: as ações dele são feitas pelo administrador.
                self.pessoas[nome] = (self.admin, True)
                continue
            email = re.sub(r"[^a-z0-9.]", "", _normalizar(nome).lower().replace(" ", ".")) + DOMINIO_HISTORICO
            senha = secrets.token_urlsafe(18)
            criado = self.cliente.post("/usuarios", json={"nome": nome.title(), "email": email, "senha": senha})
            if criado.status_code != 201:
                self.pessoas[nome] = (self.admin, True)
                continue
            usuario_id = criado.json()["id"]
            self.chamar("PATCH", f"/usuarios/{usuario_id}", self.admin, json={"perfil": perfil})
            self.pessoas[nome] = (self.entrar(email, senha), perfil == "ADMINISTRADOR")
            self.criados.append(usuario_id)

        self.saida(f"Pessoas do histórico: {len(self.pessoas)} ({len(self.criados)} usuários criados).")

    def cadastros(self, registros):
        formas = {f["titulo"].lower(): f["id"] for f in self.chamar("GET", "/formas-pagamento?tamanho=100", self.admin).json()["itens"]}
        codigos = {f["codigo"] for f in self.chamar("GET", "/formas-pagamento?tamanho=100", self.admin).json()["itens"]}
        self.formas = formas

        for condicao in sorted({r["Condicao de Pgto"] for r in registros if r["Condicao de Pgto"]}):
            if self.forma_id(condicao):
                continue
            parcelas = int(m.group(1)) if (m := re.search(r"(\d+)\s*x", condicao.lower())) else 1
            intervalo = int(m.group(1)) if (m := re.search(r"(\d+)\s*dias", condicao.lower())) else 30
            codigo = f"H{parcelas:02d}{intervalo:02d}"[:10]
            while codigo in codigos:
                codigo = f"H{secrets.token_hex(3)}"
            criada = self.chamar("POST", "/formas-pagamento", self.admin, json={
                "codigo": codigo, "titulo": condicao[:100], "tipo": "A_PRAZO" if "prazo" in condicao.lower() else "A_VISTA",
                "parcelas": parcelas, "intervalo_dias": intervalo if "prazo" in condicao.lower() else 0,
            })
            if criada.status_code == 201:
                formas[condicao.lower()] = criada.json()["id"]
                codigos.add(codigo)

        fornecedores = {_normalizar(f["nome"]): f["id"] for f in self.chamar("GET", "/fornecedores", self.admin).json()}
        for nome in sorted({r["Fornecedor"] for r in registros}):
            if _normalizar(nome[:150]) not in fornecedores:
                criado = self.chamar("POST", "/fornecedores", self.admin, json={"nome": nome[:150]})
                if criado.status_code == 201:
                    fornecedores[_normalizar(nome[:150])] = criado.json()["id"]
        self.fornecedores = fornecedores

        categorias = {_normalizar(c["nome"]): c["id"] for c in self.chamar("GET", "/categorias", self.admin).json()}
        for nome in sorted({r["Grupo do Item"] or "Sem grupo" for r in registros}):
            if _normalizar(nome) not in categorias:
                criada = self.chamar("POST", "/categorias", self.admin, json={"nome": nome[:100]})
                if criada.status_code == 201:
                    categorias[_normalizar(nome)] = criada.json()["id"]

        produtos = {}
        pagina = 1
        while True:
            lote = self.chamar("GET", f"/produtos?pagina={pagina}&tamanho=100", self.admin).json()
            produtos.update({_normalizar(p["nome"]): p["id"] for p in lote})
            if len(lote) < 100:
                break
            pagina += 1

        ultimo = {}
        for r in registros:
            ultimo[_normalizar(r["Item do Pedido"])] = r
        for chave, r in sorted(ultimo.items()):
            if chave in produtos:
                continue
            criado = self.chamar("POST", "/produtos", self.admin, json={
                "nome": r["Item do Pedido"].strip()[:150],
                "categoria_id": categorias[_normalizar(r["Grupo do Item"] or "Sem grupo")],
                "quantidade": 0,
                "preco": round(_numero(r["Valor Total"]) / max(int(r["Quatidade UN"]), 1), 2),
                "fornecedor_id": fornecedores.get(_normalizar(r["Fornecedor"][:150])),
                "estoque_minimo": 0,
            })
            if criado.status_code == 201:
                produtos[chave] = criado.json()["id"]
        self.produtos = produtos
        self.saida(f"Cadastros: {len(fornecedores)} fornecedores, {len(categorias)} categorias, {len(produtos)} produtos.")

    def forma_id(self, condicao):
        c = condicao.lower().strip()
        if c in ("a vista", "à vista"):
            return self.formas.get("à vista")
        if c in self.formas:
            return self.formas[c]
        m = re.fullmatch(r"a prazo (\d+)x", c)
        return self.formas.get(f"a prazo {int(m.group(1))}x") if m else None

    def pedidos(self, registros):
        agrupados = collections.OrderedDict()
        for r in sorted(registros, key=lambda r: (_data(r["Data do Pedido"]), int(r["Numero do Pedido"]))):
            agrupados.setdefault(r["Numero do Pedido"], []).append(r)

        hoje = date.today()
        importados = 0
        self.datas = []
        inicio = time.monotonic()

        for indice, (numero, itens) in enumerate(agrupados.items(), start=1):
            primeira = itens[0]
            quantidades, totais = collections.OrderedDict(), collections.defaultdict(float)
            for r in itens:
                pid = self.produtos.get(_normalizar(r["Item do Pedido"]))
                if pid is None:
                    continue
                quantidades[pid] = quantidades.get(pid, 0) + int(r["Quatidade UN"])
                totais[pid] += _numero(r["Valor Total"])
            if not quantidades:
                continue

            solicitante, _ = self.pessoas.get(primeira["Solicitante"], (self.admin, True))
            texto = f"Pedido {numero} do sistema antigo ({primeira['Local']}). {primeira['Observacao']}".strip()
            criada = self.chamar("POST", "/solicitacoes-compra", solicitante, json={
                "observacao": texto[:500],
                "itens": [{"produto_id": pid, "quantidade": q} for pid, q in quantidades.items()],
            })
            if criada.status_code != 201:
                continue
            sid = criada.json()["id"]

            data_pedido = _data(primeira["Data do Pedido"])
            previsao = _data(primeira["Previsao de Entrega"]) if primeira["Previsao de Entrega"] else None
            prazo = max((previsao - data_pedido).days, 0) if previsao else 7

            cotacao = self.chamar("POST", f"/solicitacoes-compra/{sid}/cotacoes", self.admin, json={
                "fornecedor_id": self.fornecedores[_normalizar(primeira["Fornecedor"][:150])],
                "frete": 0,
                "prazo_entrega_dias": prazo,
                "forma_pagamento_id": self.forma_id(primeira["Condicao de Pgto"]),
                "observacao": primeira["Condicao de Pgto"][:500] or None,
                "itens": [{"produto_id": pid, "preco_unitario": round(totais[pid] / q, 4)} for pid, q in quantidades.items()],
            })
            if cotacao.status_code != 201:
                continue

            aprovador, pode_proprio = self.pessoas.get(primeira["Aprovador"], (self.admin, True)) if primeira["Aprovador"] else (self.admin, True)
            if aprovador == solicitante and not pode_proprio:
                aprovador = self.admin
            aprovada = self.chamar("PATCH", f"/solicitacoes-compra/{sid}/aprovar", aprovador, esperado=(200, 403),
                                   json={"cotacao_id": cotacao.json()["id"]})
            if aprovada.status_code == 403:
                aprovada = self.chamar("PATCH", f"/solicitacoes-compra/{sid}/aprovar", self.admin, json={"cotacao_id": cotacao.json()["id"]})
            if aprovada.status_code != 200:
                continue

            entrega = min(data_pedido + timedelta(days=prazo), hoje)
            compra = self.chamar("POST", f"/solicitacoes-compra/{sid}/compra", self.admin, json={
                "numero_pedido": numero,
                "data_compra": data_pedido.isoformat(),
                "previsao_entrega": (data_pedido + timedelta(days=prazo)).isoformat(),
            })
            if compra.status_code != 201:
                continue

            if primeira["Status do Pedido"].lower().startswith("receb"):
                self.chamar("POST", f"/solicitacoes-compra/{sid}/compra/recebimentos", self.admin, json={
                    "data_recebimento": entrega.isoformat(), "nota_fiscal": f"Pedido {numero}"[:50],
                })

            self.datas.append((sid, data_pedido, entrega))
            importados += 1
            if indice % 50 == 0:
                self.saida(f"  {indice}/{len(agrupados)} pedidos ({time.monotonic() - inicio:.0f}s)")

        self.saida(f"Pedidos importados: {importados} de {len(agrupados)}.")

    def ajustar_datas(self):
        """O sistema grava a data em que cada ação foi feita; aqui voltam as datas do histórico."""
        from backend.database import conectar

        conexao = conectar()
        cursor = conexao.cursor()
        for sid, pedido, entrega in self.datas:
            cursor.execute(
                """
                UPDATE solicitacoes_compra
                SET data_criacao = %s::date + time '09:00',
                    data_decisao = %s::date + time '11:00',
                    data_atualizacao = %s::date + time '16:00'
                WHERE id = %s;
                UPDATE cotacoes SET data_criacao = %s::date + time '10:00', data_atualizacao = %s::date + time '10:00'
                WHERE solicitacao_id = %s;
                UPDATE compras SET data_criacao = data_compra + time '12:00' WHERE solicitacao_id = %s;
                """,
                (pedido, pedido, entrega, sid, pedido, pedido, sid, sid),
            )
        conexao.commit()
        conexao.close()

    def estoque_minimo(self, registros):
        compras = collections.defaultdict(int)
        grupo = {}
        for r in registros:
            chave = _normalizar(r["Item do Pedido"])
            compras[chave] += int(r["Quatidade UN"])
            grupo[chave] = r["Grupo do Item"]
        meses = max(1, len({r["Data do Pedido"][3:10] for r in registros}))
        alterados = 0
        for chave, pid in self.produtos.items():
            if chave not in grupo:
                continue
            minimo = max(1, round(compras[chave] / meses / 2)) if grupo[chave] in GRUPOS_DE_ESTOQUE else 0
            produto = self.chamar("GET", f"/produtos/{pid}", self.admin).json()
            corpo = {k: produto[k] for k in ("nome", "categoria_id", "quantidade", "preco", "fornecedor_id")}
            if self.chamar("PUT", f"/produtos/{pid}", self.admin, json=corpo | {"estoque_minimo": minimo}).status_code == 200:
                alterados += 1
        self.saida(f"Estoque mínimo calculado para {alterados} produtos (itens fora dos grupos de estoque ficam com 0).")

    def simular_consumo(self, registros):
        from backend.database import conectar

        aleatorio = random.Random(7)
        hoje = date.today()
        eventos = []
        for r in registros:
            chave = _normalizar(r["Item do Pedido"])
            pid = self.produtos.get(chave)
            if pid is None:
                continue
            dia = _data(r["Data do Pedido"])
            quantidade = int(r["Quatidade UN"])
            if r["Grupo do Item"] in GRUPOS_DE_ESTOQUE:
                partes = aleatorio.randint(2, 6)
                consumo = int(quantidade * aleatorio.uniform(0.75, 1.0))
                for _ in range(partes):
                    eventos.append((dia + timedelta(days=aleatorio.randint(5, 50)), pid, max(1, consumo // partes)))
            elif aleatorio.random() < 0.8:
                eventos.append((dia + timedelta(days=aleatorio.randint(3, 20)), pid, quantidade))

        saldo = {}
        criadas = []
        for dia, pid, quantidade in sorted(eventos):
            if dia > hoje:
                continue
            if pid not in saldo:
                saldo[pid] = self.chamar("GET", f"/produtos/{pid}", self.admin).json()["quantidade"]
            quantidade = min(quantidade, saldo[pid])
            if quantidade <= 0:
                continue
            saida = self.chamar("POST", "/movimentacoes", self.admin, json={"produto_id": pid, "tipo": "SAIDA", "quantidade": quantidade})
            if saida.status_code == 201:
                saldo[pid] -= quantidade
                criadas.append((saida.json()["id"], dia))

        conexao = conectar()
        cursor = conexao.cursor()
        for mid, dia in criadas:
            cursor.execute(
                "UPDATE movimentacoes SET data_movimentacao = %s::date + make_interval(hours => %s), usuario_id = NULL "
                "WHERE id = %s;",
                (dia, aleatorio.randint(8, 17), mid),
            )
        conexao.commit()
        conexao.close()
        self.saida(f"Consumo simulado: {len(criadas)} saídas de estoque.")

    def finalizar(self):
        for usuario_id in self.criados:
            self.chamar("PATCH", f"/usuarios/{usuario_id}", self.admin, json={"ativo": False})
        if self.criados:
            self.saida(f"{len(self.criados)} usuários do histórico ficaram inativos (só aparecem nos registros).")


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Importa o CSV \"Itens do Pedido de Compra\" do sistema antigo.")
    parser.add_argument("arquivo")
    parser.add_argument("--banco", help="Nome do banco (ex.: sistema_estoque_demo). É criado se não existir.")
    parser.add_argument("--email", required=True, help="Administrador que faz a importação (é criado se o banco estiver vazio).")
    parser.add_argument("--senha", help="Senha do administrador (se omitida, é perguntada).")
    parser.add_argument("--nome", default="Administrador", help="Nome do administrador, se ele for criado agora.")
    parser.add_argument("--estoque-minimo", action="store_true", help="Calcula o estoque mínimo pela compra média mensal.")
    parser.add_argument("--simular-consumo", action="store_true", help="Cria saídas simuladas (só para demonstração).")
    parser.add_argument("--forcar", action="store_true", help="Importa mesmo que o banco já tenha solicitações.")
    parser.add_argument("--desfazer", action="store_true",
                        help="Apaga antes o que uma importação anterior criou (pedidos, entradas e consumo simulado).")
    parser.add_argument("--so-desfazer", action="store_true", help="Só apaga a importação anterior, sem importar de novo.")
    args = parser.parse_args(argumentos)

    if args.banco:
        os.environ["DB_NAME"] = args.banco

    from dotenv import load_dotenv

    load_dotenv()
    senha = args.senha or getpass.getpass(f"Senha de {args.email}: ")

    from backend.importacao.csv_pedidos import ArquivoInvalido, ler_pedidos

    try:
        with open(args.arquivo, encoding="utf-8-sig") as arquivo:
            registros, problemas = ler_pedidos(arquivo.read())
    except (OSError, UnicodeDecodeError, ArquivoInvalido) as erro:
        raise SystemExit(f"Não foi possível ler o arquivo: {erro}")

    print(f"Arquivo: {len(registros)} itens em {len({r['Numero do Pedido'] for r in registros})} pedidos.")
    for problema in problemas[:10]:
        print("  ignorado:", problema)

    if args.banco:
        _criar_banco_se_preciso(args.banco)

    from fastapi.testclient import TestClient

    from backend.database import conectar
    from backend.main import app

    with TestClient(app) as cliente:
        conexao = conectar()
        if args.desfazer or args.so_desfazer:
            solicitacoes, movimentos = desfazer_importacao(conexao)
            print(f"Importação anterior desfeita: {solicitacoes} solicitações e {movimentos} movimentações apagadas.")
            if args.so_desfazer:
                conexao.close()
                return 0
        cursor = conexao.cursor()
        cursor.execute("SELECT COUNT(*) FROM solicitacoes_compra;")
        existentes = cursor.fetchone()[0]
        conexao.close()
        if existentes and not args.forcar:
            raise SystemExit(
                f"O banco {os.getenv('DB_NAME')} já tem {existentes} solicitações. "
                "Use um banco novo (--banco) ou --forcar para importar mesmo assim."
            )

        importador = Importador(cliente)
        importador.preparar_administrador(args.email, senha, args.nome)
        importador.preparar_pessoas(registros)
        importador.cadastros(registros)
        importador.pedidos(registros)
        importador.ajustar_datas()
        if args.estoque_minimo:
            importador.estoque_minimo(registros)
        if args.simular_consumo:
            importador.simular_consumo(registros)
        importador.finalizar()

    if importador.erros:
        print(f"\n{len(importador.erros)} chamadas com erro (primeiras 10):")
        for erro in importador.erros[:10]:
            print("  ", erro)
    print("\nPronto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
