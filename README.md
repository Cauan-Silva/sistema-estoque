# Sistema de Gestão de Estoque

API REST para gerenciamento de estoque desenvolvida com Python, FastAPI e PostgreSQL.

O sistema permite gerenciar produtos, categorias, entradas e saídas de estoque, consultar históricos, aplicar filtros e gerar indicadores e relatórios.

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

Crie um banco chamado:

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

O arquivo `.env` contém informações locais e não deve ser enviado ao GitHub.

## Executando a API

Com o ambiente virtual ativo:

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

### Busca por nome

```text
GET /produtos?busca=Intelbras
```

### Filtro por categoria

```text
GET /produtos?categoria_id=1
```

### Estoque baixo

```text
GET /produtos?estoque_baixo=true
```

Com limite personalizado:

```text
GET /produtos?estoque_baixo=true&limite_estoque=10
```

## Movimentações de estoque

### Entrada

```json
{
  "produto_id": 1,
  "tipo": "ENTRADA",
  "quantidade": 10
}
```

### Saída

```json
{
  "produto_id": 1,
  "tipo": "SAIDA",
  "quantidade": 3
}
```

O sistema impede saídas maiores que o estoque disponível.

A alteração do estoque e o registro da movimentação são realizados dentro da mesma transação no PostgreSQL.

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

Filtros também podem ser combinados:

```text
GET /movimentacoes?produto_id=1&tipo=SAIDA&data_inicio=2026-09-01T00:00:00&data_fim=2026-09-30T23:59:59
```

O sistema rejeita intervalos em que `data_inicio` seja posterior a `data_fim`.

## Relatórios

### Resumo do estoque

```text
GET /relatorios/resumo
```

O relatório apresenta:

- total de produtos
- total de categorias
- quantidade total de unidades
- produtos com estoque baixo
- valor total do estoque
- total de entradas
- total de saídas

O limite considerado como estoque baixo pode ser configurado:

```text
GET /relatorios/resumo?limite_estoque=10
```

### Produtos com maior valor em estoque

```text
GET /relatorios/maior-valor
```

O valor de cada produto é calculado através de:

```text
valor em estoque = quantidade × preço
```

É possível definir quantos produtos serão retornados:

```text
GET /relatorios/maior-valor?limite=5
```

## Regras de negócio

- Cada produto pertence a uma categoria.
- Categorias vinculadas a produtos não podem ser excluídas.
- Entradas aumentam automaticamente o estoque.
- Saídas reduzem automaticamente o estoque.
- O estoque não pode ficar negativo.
- Cada entrada ou saída gera um registro no histórico.
- Atualização do estoque e criação da movimentação utilizam a mesma transação.
- Consultas de movimentações podem ser filtradas por produto, tipo e período.
- Intervalos de datas inválidos são rejeitados.

## Próximas funcionalidades

- Autenticação de usuários
- Controle de permissões
- Dashboard
- Testes automatizados
- Paginação
- Logs da aplicação
- Migrations de banco de dados