# Sistema de Gestão de Estoque e Compras

Sistema web para controlar o estoque e todo o ciclo de compras: da solicitação de compra às cotações, aprovação, pedido e recebimento, com entrada automática dos materiais no estoque.

O projeto é composto por uma API REST em **Python + FastAPI + PostgreSQL** e um **frontend em HTML, CSS e JavaScript**, servido pela própria API. Tem autenticação com JWT, perfis de permissão, auditoria, exportação para Excel e PDF, consulta de preços de mercado, migrations com Alembic, Docker e integração contínua no GitHub Actions.

## Sumário

- [Funcionalidades](#funcionalidades)
- [Fluxo de compras](#fluxo-de-compras)
- [Tecnologias](#tecnologias)
- [Como rodar](#como-rodar)
- [Configuração (.env)](#configuração-env)
- [Banco de dados e migrations](#banco-de-dados-e-migrations)
- [Frontend](#frontend)
- [Perfis e permissões](#perfis-e-permissões)
- [Consulta de preços](#consulta-de-preços)
- [Exportação](#exportação)
- [Logs e auditoria](#logs-e-auditoria)
- [API](#api)
- [Regras de negócio](#regras-de-negócio)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Testes e integração contínua](#testes-e-integração-contínua)

## Funcionalidades

**Estoque**
- Produtos e categorias, com busca, filtros (categoria, fornecedor, estoque baixo) e paginação
- Entradas e saídas de estoque, com bloqueio de saída maior que o disponível
- Histórico de movimentações com filtros por produto, tipo e período
- Painel com cartões de indicador coloridos (mini barras, anel e barra de progresso) e gráficos de valor por categoria e de entradas e saídas por mês

**Compras**
- Fornecedores (ativos e inativos) e formas de pagamento (à vista, dia específico, a prazo de 1X a 12X)
- Solicitações de compra com vários itens
- Cotações por fornecedor, com preços por item, frete, prazo, validade e forma de pagamento
- Comparação de cotações: menor total, menor prazo, menor frete e melhor preço de cada produto
- Aprovação e reprovação com justificativa, sem permitir aprovar a própria solicitação
- Registro da compra com cópia dos valores aprovados
- Recebimento total ou parcial, com **entrada automática no estoque**
- Relatório de compras por período, fornecedor, produto e mês, com pontualidade das entregas
- Consulta de preços: histórico do que já foi pago e cotado, e ofertas do Mercado Livre

**Administração e qualidade**
- Login com JWT, senhas com bcrypt e cinco perfis de permissão
- Administração de usuários e auditoria de todas as alterações
- Logs em arquivo com código de requisição para suporte
- Exportação para Excel e PDF
- Migrations com Alembic, Docker Compose e CI com testes e verificação do Docker

## Fluxo de compras

```text
ABERTA → EM_COTACAO → APROVADA → COMPRADA → RECEBIDA

ABERTA ou EM_COTACAO            → REPROVADA
ABERTA, EM_COTACAO ou APROVADA  → CANCELADA
EM_COTACAO (sem cotações)       → ABERTA
```

| Status | Significado |
|---|---|
| `ABERTA` | Solicitação criada; itens podem ser editados |
| `EM_COTACAO` | Recebeu pelo menos uma cotação; itens congelados |
| `APROVADA` | Uma cotação foi aprovada; aguarda o registro da compra |
| `COMPRADA` | Compra registrada; aguarda a entrega |
| `RECEBIDA` | Todos os itens chegaram e entraram no estoque |
| `REPROVADA` | Encerrada por um aprovador, com justificativa |
| `CANCELADA` | Encerrada antes da compra |

## Tecnologias

| Camada | Tecnologias |
|---|---|
| API | Python, FastAPI, Pydantic, Uvicorn |
| Banco | PostgreSQL, Psycopg2, Alembic, SQLAlchemy (só para as migrations) |
| Segurança | JWT (python-jose), bcrypt |
| Arquivos | openpyxl (Excel), fpdf2 (PDF) |
| Integração | HTTPX (Mercado Livre) |
| Frontend | HTML, CSS e JavaScript (módulos ES), sem build |
| Infra | Docker, Docker Compose, GitHub Actions |
| Testes | Pytest, TestClient do FastAPI |

## Como rodar

### Com Docker (recomendado)

Precisa apenas do [Docker](https://docs.docker.com/get-docker/).

```bash
git clone https://github.com/Cauan-Silva/sistema-estoque.git
cd sistema-estoque
cp .env.example .env
```

Edite o `.env` e defina pelo menos `DB_PASSWORD` e `JWT_SECRET_KEY`. Depois:

```bash
docker compose up -d --build
```

Acesse **http://localhost:8000/app/**. O primeiro usuário cadastrado vira administrador.

Comandos úteis:

```bash
docker compose logs -f api      # acompanhar os logs
docker compose down             # parar (os dados continuam no volume)
docker compose up -d --build    # atualizar depois de um git pull
```

### Sem Docker

Precisa de Python 3.12 ou mais novo e PostgreSQL.

```bash
git clone https://github.com/Cauan-Silva/sistema-estoque.git
cd sistema-estoque
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows (no Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env              # no Linux/macOS: cp .env.example .env
```

Crie o banco `sistema_estoque` no PostgreSQL, preencha o `.env` e rode:

```bash
python -m uvicorn backend.main:app --reload
```

As tabelas são criadas e atualizadas automaticamente na inicialização (veja [migrations](#banco-de-dados-e-migrations)).

| Endereço | O que é |
|---|---|
| http://127.0.0.1:8000/app/ | Sistema (frontend) |
| http://127.0.0.1:8000/docs | Documentação interativa da API (Swagger) |
| http://127.0.0.1:8000/health | Verificação de funcionamento |

### Acesso por outros computadores da rede

No computador que roda o sistema:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

No Windows, libere a porta (PowerShell como administrador):

```powershell
New-NetFirewallRule -DisplayName "Sistema Estoque" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

Nos outros computadores, abra `http://IP-DO-SERVIDOR:8000/app/`. Com Docker, a porta já fica disponível na rede.

## Configuração (.env)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Sim | Conexão com o PostgreSQL |
| `JWT_SECRET_KEY` | Sim | Chave dos tokens de login. Gere com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `LOG_LEVEL` | Não | `DEBUG`, `INFO` (padrão), `WARNING` ou `ERROR` |
| `LOG_DIR` | Não | Pasta dos arquivos de log (padrão: `logs`) |
| `API_PORT` | Não | Porta da API no Docker (padrão: 8000) |
| `MERCADO_LIVRE_CLIENT_ID`, `MERCADO_LIVRE_CLIENT_SECRET`, `MERCADO_LIVRE_REDIRECT_URI` | Não | Consulta de preços no Mercado Livre |

O `.env` contém senhas e não vai para o GitHub. O modelo com todas as variáveis está em `.env.example`.

## Banco de dados e migrations

O esquema do banco é controlado pelo **Alembic**, na pasta `migrations/`. A API aplica as migrations pendentes sempre que inicia, então normalmente não é preciso rodar nada à mão.

| Migration | Conteúdo |
|---|---|
| `0001_esquema_inicial` | Todas as tabelas do sistema |
| `0002_credenciais_externas` | Tokens das APIs de preço |

Bancos criados antes do Alembic são adotados sem perda de dados: a migração inicial só cria o que estiver faltando.

Comandos úteis (com o ambiente virtual ativo):

```bash
alembic current                          # versão atual do banco
alembic history                          # lista de migrations
alembic upgrade head                     # aplicar manualmente
alembic revision -m "descricao curta"     # criar uma migration nova
```

Para mudar o banco, crie uma migration nova e escreva as alterações em `upgrade()` e `downgrade()`. Nunca altere uma migration que já foi aplicada em produção.

## Frontend

O frontend fica em `frontend/` e é servido pela API em `/app/`. Não há etapa de build nem dependências de npm. O servidor envia os arquivos com `Cache-Control: no-cache`, então depois de uma atualização o navegador carrega a versão nova.

Telas: Entrar e criar conta, Painel, Produtos, Categorias, Movimentações, Fornecedores, Formas de pagamento, Solicitações, Detalhe da solicitação, Compras, Relatório de compras, Usuários e Auditoria.

- **Visual**: céu ao entardecer com serras em camadas no topo de cada tela, títulos e números em *Roboto* e textos em *Open Sans*.
- **Temas**: automático (segue o sistema), claro ou escuro, no menu da conta.
- **Status**: cores do código de fibra óptica, sempre acompanhadas do nome do status.
- **Gráficos**: feitos em HTML e CSS, com cores validadas para daltonismo nos dois temas.
- **Cores por módulo**: Estoque em verde-água, Compras em laranja, Relatórios em violeta e Administração em azul, aplicadas nos títulos, quadros e totais.
- **Detalhe da solicitação**: mostra as etapas, o próximo passo e quem é responsável por ele.
- **Responsivo**: funciona no celular, com menu recolhível.

## Perfis e permissões

| Ação | Administrador | Comprador | Aprovador | Almoxarife | Consulta |
|---|:-:|:-:|:-:|:-:|:-:|
| Ver todas as telas, consultar preços e exportar | ✓ | ✓ | ✓ | ✓ | ✓ |
| Produtos, categorias e movimentações | ✓ | | | ✓ | |
| Fornecedores e formas de pagamento | ✓ | ✓ | | | |
| Criar, editar e cancelar solicitações | ✓ | ✓ | | ✓ | |
| Cotações e registro da compra | ✓ | ✓ | | | |
| Aprovar e reprovar | ✓ | | ✓ | | |
| Registrar recebimento | ✓ | | | ✓ | |
| Gerenciar usuários e ver a auditoria | ✓ | | | | |

- O primeiro usuário de um banco novo é Administrador; os seguintes entram como Consulta.
- Ninguém aprova ou reprova uma solicitação criada por si.
- Um administrador não pode remover o próprio acesso de administrador.
- Sem permissão, a API responde `403` e o frontend esconde o botão.

## Consulta de preços

O botão **Preços** de cada produto mostra:

- **Histórico interno**: último preço pago, média, menor e maior, últimas compras e últimas cotações. Funciona sempre.
- **Preços de mercado**: ofertas do Mercado Livre, com menor preço, mediana e maior. É opcional.

O formulário de cotação também mostra o último preço pago e a média ao lado de cada item.

### Ativar o Mercado Livre

1. Crie um aplicativo em [developers.mercadolivre.com.br](https://developers.mercadolivre.com.br). Cadastre um endereço de retorno (*redirect URI*) com `https`, por exemplo `https://www.google.com.br`.
2. Preencha no `.env`: `MERCADO_LIVRE_CLIENT_ID`, `MERCADO_LIVRE_CLIENT_SECRET` e `MERCADO_LIVRE_REDIRECT_URI`.
3. Rode a autorização uma vez:

   ```bash
   python -m backend.precos.autorizar_mercado_livre
   # com Docker:
   docker compose exec api python -m backend.precos.autorizar_mercado_livre
   ```

   Abra o endereço que aparecer, autorize o aplicativo e cole o endereço de retorno (o que tem `?code=`).

O token do Mercado Livre expira em poucas horas. O sistema renova sozinho e guarda o token novo no banco, na tabela `credenciais_externas`. Se a autorização for revogada, a tela de preços avisa para rodar o passo 3 de novo. Para um teste rápido sem OAuth, também é possível colocar um token pronto em `MERCADO_LIVRE_TOKEN`, mas ele para de funcionar quando expira.

### Adicionar outra fonte de preços

As fontes ficam em `backend/precos/`. Crie uma classe que herde de `FontePreco`, com `nome`, `configurada()` e `buscar(termo, limite)` devolvendo um `ResultadoFonte`, e acrescente uma instância à lista `FONTES` em `backend/precos/servico.py`. A tela de preços passa a mostrá-la automaticamente.

## Exportação

Os botões **Excel** e **PDF** ficam no topo de Produtos, Movimentações, Fornecedores, Compras e Relatório de compras, e exportam exatamente o que está filtrado.

- **Excel**: cabeçalho formatado, filtros nas colunas, formatos de moeda e data e linha de totais. O relatório de compras sai com uma aba por resumo.
- **PDF**: horizontal, com título, período, data de geração e número de páginas.

```text
GET /exportacoes/{produtos|movimentacoes|fornecedores|compras|relatorio-compras}?formato=xlsx|pdf
```

## Logs e auditoria

**Logs**: vão para o console e para `logs/app.log`, com até 5 arquivos de 5 MB. Cada requisição registra método, endereço, resultado, tempo, usuário e um código, que também volta no cabeçalho `X-Request-ID`. Em erros inesperados, a mensagem mostra esse código, e basta procurá-lo no log para ver o rastreamento completo.

**Auditoria**: toda criação, alteração e exclusão (`POST`, `PUT`, `PATCH` e `DELETE`) fica na tabela `auditoria`, com usuário, endereço, resultado, IP e duração. Administradores consultam pela tela **Auditoria**, com filtros por usuário, tipo de ação, período e "só falhas".

## API

A documentação completa e interativa fica em **`/docs`** (Swagger). Lá, o botão **Authorize** faz o login com e-mail e senha.

### Autenticação

```text
POST /usuarios          criar conta
POST /usuarios/login    login com JSON {"email", "senha"}
POST /usuarios/token    login por formulário (usado pelo Swagger)
GET  /usuarios/me       usuário atual, perfil e permissões
```

As demais rotas exigem o cabeçalho `Authorization: Bearer <token>`.

### Rotas

| Área | Rotas |
|---|---|
| Produtos | `GET/POST /produtos`, `GET/PUT/DELETE /produtos/{id}` |
| Categorias | `GET/POST /categorias`, `GET/PUT/DELETE /categorias/{id}` |
| Movimentações | `GET/POST /movimentacoes`, `GET /movimentacoes/{id}` |
| Relatórios | `GET /relatorios/resumo`, `/relatorios/maior-valor`, `/relatorios/compras` |
| Fornecedores | `GET/POST /fornecedores`, `GET/PUT /fornecedores/{id}`, `PATCH /fornecedores/{id}/status` |
| Formas de pagamento | `GET/POST /formas-pagamento`, `GET/PUT /formas-pagamento/{id}`, `PATCH /formas-pagamento/{id}/status` |
| Solicitações | `GET/POST /solicitacoes-compra`, `GET/PUT /solicitacoes-compra/{id}`, `PATCH .../cancelar`, `.../aprovar`, `.../reprovar` |
| Cotações | `GET/POST /solicitacoes-compra/{id}/cotacoes`, `GET/PUT/DELETE .../cotacoes/{cotacao_id}`, `GET .../cotacoes/comparacao` |
| Compras | `POST/GET /solicitacoes-compra/{id}/compra`, `GET /compras`, `GET /compras/{id}` |
| Recebimentos | `POST/GET /solicitacoes-compra/{id}/compra/recebimentos` |
| Preços | `GET /precos/fontes`, `GET /precos/produtos/{id}` |
| Exportação | `GET /exportacoes/{recurso}?formato=xlsx\|pdf` |
| Usuários | `GET /usuarios`, `PATCH /usuarios/{id}` |
| Auditoria | `GET /auditoria` |

### Exemplos

Cotação:

```json
{
  "fornecedor_id": 1,
  "frete": 15.50,
  "prazo_entrega_dias": 7,
  "validade": "2026-12-31",
  "forma_pagamento_id": 5,
  "itens": [
    { "produto_id": 1, "preco_unitario": 2.35 },
    { "produto_id": 2, "preco_unitario": 1.10 }
  ]
}
```

Recebimento parcial (sem `itens`, recebe tudo o que está pendente):

```json
{
  "data_recebimento": "2026-10-05",
  "nota_fiscal": "NF-123",
  "itens": [{ "produto_id": 1, "quantidade": 6 }]
}
```

## Regras de negócio

**Estoque**
- Cada produto pertence a uma categoria, e categorias com produtos não podem ser excluídas.
- O estoque não fica negativo; cada movimentação atualiza a quantidade na mesma transação.
- Produtos ligados a solicitações de compra não podem ser excluídos.

**Fornecedores e cotações**
- Fornecedores e formas de pagamento são inativados, nunca excluídos.
- Novos vínculos só aceitam fornecedores e formas de pagamento ativos.
- Cada fornecedor tem no máximo uma cotação por solicitação, só com produtos da própria solicitação.
- Uma cotação pode cobrir só parte dos itens, mas só cotações completas e dentro da validade podem ser aprovadas.

**Solicitações e compras**
- Uma solicitação precisa de pelo menos um item, sem produtos repetidos.
- Só solicitações abertas têm os itens editados.
- Reprovações exigem justificativa.
- Cada solicitação aprovada gera no máximo uma compra, que guarda uma cópia dos valores aprovados.
- Recebimentos não passam da quantidade pendente e entram no estoque na mesma transação.
- A solicitação vira `RECEBIDA` quando todos os itens chegam.

**Segurança**
- Senhas guardadas com bcrypt; o login inválido não diz se o erro foi no e-mail ou na senha.
- Tokens de login expiram, e usuários inativos não acessam o sistema.

## Estrutura do projeto

```text
sistema-estoque/
├── .github/workflows/tests.yml   CI: testes e verificação do Docker
├── alembic.ini                   configuração do Alembic
├── migrations/                   migrations do banco
│   └── versions/
├── backend/
│   ├── main.py                   aplicação, middleware de logs e auditoria
│   ├── database.py               conexão e aplicação das migrations
│   ├── autenticacao.py           JWT
│   ├── permissoes.py             perfis e permissões
│   ├── logs.py                   configuração dos logs
│   ├── exportacao.py             geração de Excel e PDF
│   ├── precos/                   fontes de preço e histórico
│   ├── repositorio*.py           acesso ao banco
│   ├── routes/                   rotas da API
│   ├── schemas/                  validação com Pydantic
│   └── tests/                    testes automatizados
├── frontend/
│   ├── index.html
│   ├── css/app.css
│   └── js/                       app, api, componentes, gráficos e telas
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## Testes e integração contínua

Os testes usam um banco PostgreSQL separado, `sistema_estoque_test`:

```bash
python -m pytest -v
```

São cerca de 330 casos de teste, cobrindo estoque, todo o fluxo de compras, permissões, auditoria, exportação, migrations e a consulta de preços. As chamadas ao Mercado Livre são simuladas, sem acessar a internet.

O GitHub Actions roda dois jobs a cada push e pull request na `main`:

1. **tests**: sobe um PostgreSQL, instala as dependências e roda toda a suíte.
2. **docker**: constrói as imagens, sobe o `docker compose` e confere a API, o frontend, as migrations e o cadastro de usuário.

## Possíveis evoluções

Todos os itens planejados foram concluídos. Ideias para o futuro:

- Recuperação de senha por e-mail
- Notificações para quem precisa agir (aprovar, comprar, receber)
- Anexar notas fiscais e propostas às compras
- Sugestão automática de compra a partir do estoque mínimo e do consumo médio
- Outras fontes de preço além do Mercado Livre
