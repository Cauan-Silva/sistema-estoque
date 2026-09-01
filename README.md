# Sistema de Gestão de Estoque

API REST para gerenciamento de estoque desenvolvida com Python, FastAPI e PostgreSQL.

O sistema permite gerenciar produtos, categorias, entradas e saídas de estoque, consultar históricos, aplicar filtros, gerar relatórios e validar o comportamento da API através de testes automatizados.

## Funcionalidades

- Cadastro, consulta, atualização e exclusão de produtos
- Cadastro e gerenciamento de categorias
- Relacionamento entre produtos e categorias
- Busca de produtos por nome
- Filtro de produtos por categoria
- Controle de estoque baixo
- Limite configurável para estoque baixo
- Registro de entradas de estoque
- Registro de saídas de estoque
- Atualização automática da quantidade disponível
- Bloqueio de saídas com estoque insuficiente
- Histórico de movimentações
- Filtro de movimentações por produto
- Filtro de movimentações por tipo
- Filtro de movimentações por período
- Validação de intervalos de datas
- Resumo geral do estoque
- Cálculo do valor total armazenado
- Ranking de produtos por valor em estoque
- Indicadores de entradas e saídas
- Testes automatizados da API
- Banco PostgreSQL separado para testes
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
- Git
- GitHub

## Estrutura do projeto

```text
sistema-estoque/
│
├── backend/
│   ├── routes/
│   │   ├── categorias.py
│   │   ├── movimentacoes.py
│   │   ├── produtos.py
│   │   └── relatorios.py
│   │
│   ├── schemas/
│   │   ├── categoria.py
│   │   ├── movimentacao.py
│   │   ├── produto.py
│   │   └── relatorio.py
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_categorias.py
│   │   ├── test_health.py
│   │   ├── test_movimentacoes.py
│   │   ├── test_produtos.py
│   │   └── test_relatorios.py
│   │
│   ├── database.py
│   ├── main.py
│   ├── produto.py
│   ├── repositorio.py
│   ├── repositorio_categoria.py
│   ├── repositorio_movimentacao.py
│   └── repositorio_relatorio.py
│
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

Crie um arquivo `.env` na raiz do projeto:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sistema_estoque
DB_USER=postgres
DB_PASSWORD=sua_senha
```

O arquivo `.env` não deve ser enviado ao GitHub.

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

## Produtos

Exemplo de cadastro:

```json
{
  "nome": "Switch Intelbras 8 Portas",
  "categoria_id": 1,
  "quantidade": 10,
  "preco": 189.90
}
```

Busca por nome:

```text
GET /produtos?busca=Intelbras
```

Filtro por categoria:

```text
GET /produtos?categoria_id=1
```

Estoque baixo:

```text
GET /produtos?estoque_baixo=true&limite_estoque=5
```

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

Filtros podem ser combinados.

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

## Testes automatizados

O projeto utiliza Pytest para validar a API.

Os testes utilizam um banco PostgreSQL separado:

```text
sistema_estoque_test
```

Isso evita alterar os dados do ambiente principal durante a execução dos testes.

Para executar todos os testes:

```bash
pytest -v
```

A suíte cobre atualmente:

- health check
- CRUD de categorias
- CRUD de produtos
- relacionamento produto/categoria
- filtros de produtos
- movimentações de entrada
- movimentações de saída
- bloqueio de estoque insuficiente
- filtros de movimentações
- relatórios
- validações da API

Resultado atual:

```text
36 passed
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

## Próximas funcionalidades

- Paginação
- Autenticação de usuários
- Controle de permissões
- Dashboard
- Logs da aplicação
- Migrations com ferramenta dedicada
- CI/CD para execução automática dos testes