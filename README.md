# Sistema de Gestão de Estoque

API REST para gerenciamento de estoque, fornecedores e processos relacionados, desenvolvida com Python, FastAPI e PostgreSQL.

O sistema permite gerenciar produtos e categorias, controlar entradas e saídas de estoque, consultar históricos, aplicar filtros, gerar relatórios e cadastrar fornecedores.

O projeto também possui autenticação de usuários com JWT, senhas protegidas com bcrypt, rotas autenticadas, paginação, banco PostgreSQL separado para testes e integração contínua com GitHub Actions.

## Funcionalidades

### Estoque

- Cadastro, consulta, atualização e exclusão de produtos
- Cadastro e gerenciamento de categorias
- Relacionamento entre produtos e categorias
- Busca de produtos por nome
- Filtro de produtos por categoria
- Controle de estoque baixo
- Limite configurável para estoque baixo
- Paginação de produtos
- Registro de entradas de estoque
- Registro de saídas de estoque
- Atualização automática da quantidade disponível
- Bloqueio de saídas com estoque insuficiente
- Histórico de movimentações
- Filtro de movimentações por produto
- Filtro de movimentações por tipo
- Filtro de movimentações por período
- Paginação de movimentações
- Validação de intervalos de datas

### Relatórios

- Resumo geral do estoque
- Cálculo do valor total armazenado
- Ranking de produtos por valor em estoque
- Indicadores de entradas e saídas

### Usuários e autenticação

- Cadastro de usuários
- Normalização de e-mail
- Proteção de senhas com bcrypt
- Login com e-mail e senha
- Autenticação utilizando JWT
- Tokens de acesso com tempo de expiração
- Autenticação via Bearer Token
- Identificação do usuário pelo ID armazenado no token
- Endpoint para consultar o usuário autenticado
- Bloqueio de acesso com token inválido
- Suporte a usuários ativos e inativos
- Todas as rotas de negócio protegidas por autenticação

### Fornecedores

- Cadastro de fornecedores
- Consulta de fornecedor por ID
- Listagem de fornecedores
- Dados de contato, telefone e e-mail
- CPF/CNPJ do fornecedor
- Site do fornecedor
- Atualização de fornecedores
- Controle de fornecedor ativo/inativo
- Filtro de fornecedores por status
- Vínculo opcional entre produto e fornecedor
- Filtro de produtos por fornecedor
- API de fornecedores protegida por JWT

### Solicitações de compra

- Criação de solicitações com um ou mais produtos
- Solicitante identificado pelo usuário autenticado
- Edição de observação e itens enquanto a solicitação está aberta
- Cancelamento de solicitações
- Filtro por status e pelas solicitações do próprio usuário
- Paginação de solicitações

### Cotações

- Registro de cotações por fornecedor para cada solicitação
- Preço unitário por produto, frete, prazo de entrega, validade e observação
- Cálculo automático de subtotal por item, valor dos itens e valor total
- Uma cotação por fornecedor em cada solicitação
- Atualização e exclusão de cotações
- Comparação de cotações por valor total, prazo, frete e preço por produto

### Aprovação e compras

- Aprovação de uma cotação completa e dentro da validade
- Reprovação de solicitações com justificativa obrigatória
- Registro de quem decidiu, quando e por quê
- Registro da compra a partir da solicitação aprovada
- Cópia dos valores aprovados no registro da compra
- Previsão de entrega calculada pelo prazo da cotação
- Consulta de compras com filtro por fornecedor e paginação

### Qualidade e infraestrutura

- Testes automatizados com Pytest
- Banco PostgreSQL separado para testes
- Integração contínua com GitHub Actions
- Validação de dados com Pydantic
- Persistência com PostgreSQL
- Documentação automática com Swagger

## Tecnologias

- Python
- FastAPI
- PostgreSQL
- Psycopg2
- Pydantic
- Uvicorn
- Pytest
- HTTPX
- bcrypt
- python-jose
- JWT
- Git
- GitHub
- GitHub Actions

## Estrutura do projeto

```text
sistema-estoque/
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── frontend/
│   ├── css/
│   │   └── app.css
│   ├── js/
│   │   ├── telas/
│   │   ├── api.js
│   │   ├── app.js
│   │   └── ui.js
│   └── index.html
│
├── backend/
│   ├── routes/
│   │   ├── categorias.py
│   │   ├── compras.py
│   │   ├── cotacoes.py
│   │   ├── fornecedores.py
│   │   ├── movimentacoes.py
│   │   ├── produtos.py
│   │   ├── relatorios.py
│   │   ├── solicitacoes_compra.py
│   │   └── usuarios.py
│   │
│   ├── schemas/
│   │   ├── categoria.py
│   │   ├── compra.py
│   │   ├── cotacao.py
│   │   ├── fornecedor.py
│   │   ├── movimentacao.py
│   │   ├── produto.py
│   │   ├── relatorio.py
│   │   ├── solicitacao_compra.py
│   │   └── usuario.py
│   │
│   ├── tests/
│   │   ├── apoio_compras.py
│   │   ├── conftest.py
│   │   ├── test_autenticacao.py
│   │   ├── test_aprovacao.py
│   │   ├── test_autorizacao.py
│   │   ├── test_categorias.py
│   │   ├── test_comparacao_cotacoes.py
│   │   ├── test_compras.py
│   │   ├── test_cotacoes.py
│   │   ├── test_fornecedores.py
│   │   ├── test_health.py
│   │   ├── test_movimentacoes.py
│   │   ├── test_produtos.py
│   │   ├── test_relatorios.py
│   │   ├── test_solicitacoes_compra.py
│   │   └── test_usuarios.py
│   │
│   ├── autenticacao.py
│   ├── database.py
│   ├── main.py
│   ├── produto.py
│   ├── repositorio.py
│   ├── repositorio_aprovacao.py
│   ├── repositorio_categoria.py
│   ├── repositorio_compra.py
│   ├── repositorio_cotacao.py
│   ├── repositorio_fornecedor.py
│   ├── repositorio_movimentacao.py
│   ├── repositorio_relatorio.py
│   ├── repositorio_solicitacao_compra.py
│   └── repositorio_usuario.py
│
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

## Configuração

Clone o repositório:

```bash
git clone https://github.com/Cauan-Silva/sistema-estoque.git
```

Entre na pasta:

```bash
cd sistema-estoque
```

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente no Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Banco de dados

O projeto utiliza PostgreSQL.

Crie o banco principal:

```text
sistema_estoque
```

Crie também um banco separado para os testes:

```text
sistema_estoque_test
```

Crie um arquivo `.env` na raiz do projeto:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sistema_estoque
DB_USER=postgres
DB_PASSWORD=sua_senha

JWT_SECRET_KEY=sua_chave_secreta
```

Uma chave JWT segura pode ser gerada com:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

O arquivo `.env` contém informações sensíveis e não deve ser enviado ao GitHub.

## Executando a API

```bash
python -m uvicorn backend.main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Frontend:

```text
http://127.0.0.1:8000/app/
```

## Frontend

O frontend fica na pasta `frontend/` e é servido pela própria API em `/app/`. Ele usa apenas HTML, CSS e JavaScript, sem etapa de build e sem dependências de npm.

Telas disponíveis:

- Entrar e criar conta
- Painel com valor em estoque, estoque baixo e compras em andamento
- Produtos, com filtros e registro rápido de entrada e saída
- Categorias
- Movimentações, com filtros por produto, tipo e período
- Fornecedores, com edição e ativação/inativação
- Solicitações de compra
- Detalhe da solicitação: itens, cotações, comparação, aprovação, reprovação e registro da compra
- Compras

O token de acesso fica salvo no navegador. Quando ele expira, o frontend volta para a tela de entrada.

Os status usam o código de cores da fibra óptica: azul para aberta, laranja para em cotação, verde para aprovada, marrom para comprada, ardósia para cancelada e vermelho para reprovada.

## Autenticação

Todas as rotas da API exigem um token JWT, exceto:

```text
GET  /
GET  /health
POST /usuarios
POST /usuarios/login
POST /usuarios/token
```

Fluxo de uso:

1. Cadastre um usuário em `POST /usuarios`
2. Faça login em `POST /usuarios/login` para receber o token
3. Envie o token no cabeçalho de cada requisição:

```text
Authorization: Bearer <token>
```

No Swagger (`/docs`), clique em **Authorize** e informe o e-mail no campo `username` e a senha no campo `password`. O Swagger obtém o token em `POST /usuarios/token` e passa a enviá-lo em todas as requisições.

Requisições sem token ou com token inválido retornam `401`. Usuários inativos recebem `403`.

## Endpoints

### Produtos

```text
GET    /produtos
GET    /produtos/{id_produto}
POST   /produtos
PUT    /produtos/{id_produto}
DELETE /produtos/{id_produto}
```

### Categorias

```text
GET    /categorias
GET    /categorias/{id_categoria}
POST   /categorias
PUT    /categorias/{id_categoria}
DELETE /categorias/{id_categoria}
```

### Movimentações

```text
GET  /movimentacoes
GET  /movimentacoes/{id_movimentacao}
POST /movimentacoes
```

### Relatórios

```text
GET /relatorios/resumo
GET /relatorios/maior-valor
```

### Usuários

```text
POST /usuarios
POST /usuarios/login
POST /usuarios/token
GET  /usuarios/me
```

`POST /usuarios/login` recebe JSON (`email` e `senha`). `POST /usuarios/token` recebe formulário (`username` e `password`) e é o endpoint usado pelo Swagger.

O endpoint `/usuarios/me` exige autenticação.

### Fornecedores

```text
POST  /fornecedores
GET   /fornecedores
GET   /fornecedores/{fornecedor_id}
PUT   /fornecedores/{fornecedor_id}
PATCH /fornecedores/{fornecedor_id}/status
```

As rotas de fornecedores exigem autenticação com JWT.

### Solicitações de compra

```text
POST  /solicitacoes-compra
GET   /solicitacoes-compra
GET   /solicitacoes-compra/{solicitacao_id}
PUT   /solicitacoes-compra/{solicitacao_id}
PATCH /solicitacoes-compra/{solicitacao_id}/cancelar
```

### Cotações

```text
POST   /solicitacoes-compra/{solicitacao_id}/cotacoes
GET    /solicitacoes-compra/{solicitacao_id}/cotacoes
GET    /solicitacoes-compra/{solicitacao_id}/cotacoes/{cotacao_id}
PUT    /solicitacoes-compra/{solicitacao_id}/cotacoes/{cotacao_id}
DELETE /solicitacoes-compra/{solicitacao_id}/cotacoes/{cotacao_id}
GET    /solicitacoes-compra/{solicitacao_id}/cotacoes/comparacao
```

### Aprovação

```text
PATCH /solicitacoes-compra/{solicitacao_id}/aprovar
PATCH /solicitacoes-compra/{solicitacao_id}/reprovar
```

### Compras

```text
POST /solicitacoes-compra/{solicitacao_id}/compra
GET  /solicitacoes-compra/{solicitacao_id}/compra
GET  /compras
GET  /compras/{compra_id}
```

## Produtos

Exemplo de cadastro:

```json
{
  "nome": "Switch Intelbras 8 Portas",
  "categoria_id": 1,
  "quantidade": 10,
  "preco": 189.90,
  "fornecedor_id": 1
}
```

O campo `fornecedor_id` é opcional. Um produto não pode ser vinculado a um fornecedor inexistente (`404`) ou inativo (`400`). Ao editar um produto, é possível manter o fornecedor atual mesmo que ele tenha sido inativado.

Busca por nome:

```text
GET /produtos?busca=Intelbras
```

Filtro por categoria:

```text
GET /produtos?categoria_id=1
```

Filtro por fornecedor:

```text
GET /produtos?fornecedor_id=1
```

Estoque baixo:

```text
GET /produtos?estoque_baixo=true&limite_estoque=5
```

Paginação:

```text
GET /produtos?pagina=1&tamanho=10
```

Os filtros podem ser combinados com os parâmetros de paginação.

## Movimentações de estoque

Entrada:

```json
{
  "produto_id": 1,
  "tipo": "ENTRADA",
  "quantidade": 10
}
```

Saída:

```json
{
  "produto_id": 1,
  "tipo": "SAIDA",
  "quantidade": 3
}
```

O sistema impede uma saída maior que o estoque disponível.

A alteração do estoque e o registro da movimentação são realizados na mesma transação.

## Filtros de movimentações

Por produto:

```text
GET /movimentacoes?produto_id=1
```

Por tipo:

```text
GET /movimentacoes?tipo=ENTRADA
```

Por período:

```text
GET /movimentacoes?data_inicio=2026-09-01T00:00:00&data_fim=2026-09-01T23:59:59
```

Paginação:

```text
GET /movimentacoes?pagina=1&tamanho=10
```

Os filtros podem ser combinados com a paginação.

## Relatórios

Resumo geral:

```text
GET /relatorios/resumo
```

Produtos com maior valor em estoque:

```text
GET /relatorios/maior-valor
```

O valor é calculado por:

```text
valor em estoque = quantidade × preço
```

## Autenticação

### Cadastro de usuário

```text
POST /usuarios
```

Exemplo:

```json
{
  "nome": "Usuario Teste",
  "email": "usuario@teste.com",
  "senha": "senha123"
}
```

As senhas não são armazenadas em texto puro. O sistema utiliza bcrypt para gerar o hash antes da persistência.

### Login

```text
POST /usuarios/login
```

Exemplo:

```json
{
  "email": "usuario@teste.com",
  "senha": "senha123"
}
```

Em caso de sucesso, a API retorna um token JWT:

```json
{
  "access_token": "token_jwt",
  "token_type": "bearer"
}
```

O token possui tempo de expiração e utiliza o ID do usuário no campo `sub`.

### Usuário autenticado

```text
GET /usuarios/me
```

A requisição deve utilizar:

```text
Authorization: Bearer <access_token>
```

Tokens inválidos ou expirados são rejeitados pela API.

## Fornecedores

O módulo de fornecedores é a primeira etapa da expansão do sistema para gerenciamento de compras e cotações.

Exemplo de fornecedor:

```json
{
  "nome": "Fornecedor Teste",
  "cpf_cnpj": "12345678000199",
  "contato": "João",
  "telefone": "48999999999",
  "email": "contato@fornecedor.com",
  "site": "https://fornecedor.com"
}
```

Rotas disponíveis:

```text
POST  /fornecedores
GET   /fornecedores
GET   /fornecedores/{fornecedor_id}
PUT   /fornecedores/{fornecedor_id}
PATCH /fornecedores/{fornecedor_id}/status
```

Todas essas rotas exigem autenticação.

Filtro por status:

```text
GET /fornecedores?ativo=true
```

Inativar ou reativar um fornecedor:

```json
{
  "ativo": false
}
```

Fornecedores não são excluídos, apenas inativados, para preservar o histórico dos produtos vinculados.

## Solicitações de compra

Uma solicitação de compra registra quais produtos precisam ser comprados e em que quantidade. O solicitante é o usuário autenticado que criou a solicitação.

Exemplo:

```json
{
  "observacao": "Reposição mensal",
  "itens": [
    { "produto_id": 1, "quantidade": 20 },
    { "produto_id": 2, "quantidade": 5 }
  ]
}
```

Filtros:

```text
GET /solicitacoes-compra?status=ABERTA
GET /solicitacoes-compra?apenas_minhas=true
GET /solicitacoes-compra?pagina=1&tamanho=10
```

Status:

| Status | Uso |
|---|---|
| `ABERTA` | Solicitação criada, pode ser editada ou cancelada |
| `EM_COTACAO` | Possui pelo menos uma cotação; os itens ficam congelados, mas ainda pode ser cancelada |
| `APROVADA` | Uma cotação foi aprovada; aguarda o registro da compra e ainda pode ser cancelada |
| `REPROVADA` | Solicitação reprovada, não pode mais ser alterada |
| `COMPRADA` | Compra registrada |
| `CANCELADA` | Solicitação cancelada, não pode mais ser alterada |
| `RECEBIDA` | Reservado para o recebimento dos materiais |

Fluxo completo:

```text
ABERTA → EM_COTACAO → APROVADA → COMPRADA

ABERTA ou EM_COTACAO            → REPROVADA
ABERTA, EM_COTACAO ou APROVADA  → CANCELADA
EM_COTACAO (sem cotações)       → ABERTA
```

## Cotações

Cada fornecedor pode registrar uma cotação para uma solicitação de compra, informando o preço unitário dos produtos solicitados, o frete e o prazo de entrega.

Exemplo:

```json
{
  "fornecedor_id": 1,
  "frete": 15.50,
  "prazo_entrega_dias": 7,
  "validade": "2026-12-31",
  "observacao": "Pagamento em 30 dias",
  "itens": [
    { "produto_id": 1, "preco_unitario": 2.35 },
    { "produto_id": 2, "preco_unitario": 1.10 }
  ]
}
```

A resposta inclui, para cada item, a quantidade solicitada e o subtotal, além de `valor_itens` e `valor_total`:

```text
subtotal    = quantidade solicitada × preço unitário
valor_total = soma dos subtotais + frete
```

Fluxo:

- A primeira cotação muda a solicitação de `ABERTA` para `EM_COTACAO`.
- Excluir a última cotação devolve a solicitação para `ABERTA`.
- Cotações só podem ser registradas, editadas ou excluídas enquanto a solicitação está `ABERTA` ou `EM_COTACAO`.

## Comparação de cotações

```text
GET /solicitacoes-compra/{solicitacao_id}/cotacoes/comparacao
```

A resposta traz:

- `cotacoes`: todas as cotações, primeiro as elegíveis, ordenadas por valor total e depois por prazo;
- `menor_valor_total`, `menor_prazo` e `menor_frete`: destaques entre as cotações elegíveis;
- `por_produto`: o melhor preço unitário de cada produto entre as cotações dentro da validade.

Uma cotação é **elegível** quando cobre todos os itens da solicitação e não está vencida. Cada cotação indica `cobre_todos_itens`, `vencida` e `elegivel`.

## Aprovação

Aprovar:

```json
{
  "cotacao_id": 2,
  "justificativa": "Menor valor total"
}
```

Reprovar:

```json
{
  "justificativa": "Valores acima do orçamento"
}
```

- Só solicitações `EM_COTACAO` podem ser aprovadas.
- A cotação aprovada precisa cobrir todos os itens e estar dentro da validade.
- Solicitações `ABERTA` ou `EM_COTACAO` podem ser reprovadas, sempre com justificativa.
- A resposta registra `cotacao_aprovada_id`, `decisao_por`, `data_decisao` e `justificativa_decisao`.

## Compras

Registrar a compra de uma solicitação aprovada:

```json
{
  "numero_pedido": "PED-001",
  "data_compra": "2026-10-01",
  "previsao_entrega": "2026-10-11",
  "observacao": "Pago via boleto"
}
```

Todos os campos são opcionais:

- `data_compra` usa a data atual quando não é informada;
- `previsao_entrega` usa a data da compra somada ao prazo da cotação aprovada.

A compra guarda uma cópia do fornecedor, dos itens, dos preços, do frete e do valor total da cotação aprovada. A solicitação passa para `COMPRADA`.

Consultas:

```text
GET /compras?fornecedor_id=1&pagina=1&tamanho=10
GET /compras/{compra_id}
GET /solicitacoes-compra/{solicitacao_id}/compra
```

## Testes automatizados

O projeto utiliza Pytest para validar o comportamento da aplicação.

Os testes utilizam um banco PostgreSQL separado:

```text
sistema_estoque_test
```

Isso evita alterar os dados do ambiente principal durante a execução dos testes.

Para executar todos os testes:

```bash
python -m pytest -v
```

A suíte cobre atualmente:

- health check
- CRUD de categorias
- CRUD de produtos
- relacionamento produto/categoria
- filtros de produtos
- paginação de produtos
- movimentações de entrada e saída
- bloqueio de estoque insuficiente
- filtros e paginação de movimentações
- relatórios
- cadastro de usuários
- hash e verificação de senhas
- login
- geração e validação de JWT
- autorização com Bearer Token
- acesso ao usuário autenticado
- repositório de fornecedores
- atualização, status e filtros de fornecedores
- vínculo entre produtos e fornecedores
- solicitações de compra
- cotações
- comparação de cotações
- aprovação e reprovação
- registro e consulta de compras
- validações da API

O resultado de cada execução fica disponível na aba **Actions** do GitHub.

## Integração contínua

O projeto utiliza GitHub Actions para executar automaticamente a suíte de testes.

O workflow é executado em:

- pushes para a branch `main`
- pull requests direcionados para a branch `main`

Durante a execução, o GitHub Actions:

1. prepara o ambiente Python;
2. inicia um serviço PostgreSQL;
3. instala as dependências;
4. configura as variáveis do ambiente de testes;
5. configura uma chave JWT exclusiva para o CI;
6. executa a suíte com Pytest.

O workflow está localizado em:

```text
.github/workflows/tests.yml
```

## Regras de negócio

- Cada produto pertence a uma categoria.
- Categorias vinculadas a produtos não podem ser excluídas.
- Entradas aumentam o estoque.
- Saídas reduzem o estoque.
- O estoque não pode ficar negativo.
- Toda movimentação gera histórico.
- Atualização do estoque e criação da movimentação usam a mesma transação.
- Movimentações podem ser filtradas por produto, tipo e período.
- Intervalos de datas inválidos são rejeitados.
- Produtos e movimentações possuem paginação.
- Senhas são armazenadas utilizando hash bcrypt.
- Login inválido não informa se o erro ocorreu no e-mail ou na senha.
- Tokens JWT possuem tempo de expiração.
- Usuários inativos não podem acessar rotas autenticadas.
- Todas as rotas de negócio exigem autenticação.
- Fornecedores são inativados em vez de excluídos.
- Produtos podem ter um fornecedor opcional.
- Novos vínculos só podem ser feitos com fornecedores ativos.
- Uma solicitação de compra precisa ter pelo menos um item.
- Cada produto aparece no máximo uma vez por solicitação.
- Apenas solicitações abertas podem ser editadas.
- Solicitações abertas ou em cotação podem ser canceladas.
- Cada fornecedor pode ter apenas uma cotação por solicitação.
- Cotações só aceitam fornecedores ativos e produtos da própria solicitação.
- Uma cotação pode cobrir apenas parte dos itens da solicitação.
- Só cotações completas e dentro da validade podem ser aprovadas.
- Reprovações exigem justificativa.
- Solicitações aprovadas ainda podem ser canceladas até o registro da compra.
- Cada solicitação aprovada gera no máximo uma compra.
- A compra guarda uma cópia dos valores aprovados.
- Produtos vinculados a solicitações de compra não podem ser excluídos.

## Próximas funcionalidades

O projeto está evoluindo do gerenciamento de estoque para um fluxo integrado de compras.

Próximas etapas:

1. ~~CRUD completo de fornecedores~~ (concluído)
2. ~~Solicitações de compra~~ (concluído)
3. ~~Registro de cotações por fornecedor~~ (concluído)
4. ~~Comparação de preços, frete e prazo~~ (concluído)
5. ~~Aprovação de compras~~ (concluído)
6. ~~Registro da compra realizada~~ (concluído)
7. Recebimento de materiais
8. Entrada automática dos materiais no estoque
9. Histórico e relatórios de compras
10. ~~Dashboard~~ (painel no frontend)
11. Exportação de dados para Excel/PDF
12. Controle de permissões por usuário
13. Logs da aplicação
14. Migrations com ferramenta dedicada
15. Dockerização da aplicação
16. Integração futura com APIs para consulta de preços