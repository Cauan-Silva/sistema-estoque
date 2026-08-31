# Sistema de Gestão de Estoque

API REST para gerenciamento de estoque desenvolvida com Python, FastAPI e PostgreSQL.

O projeto permite gerenciar produtos, categorias, entradas e saídas de estoque, além de consultar históricos e aplicar filtros.

## Funcionalidades

- Cadastro de produtos
- Listagem de produtos
- Consulta de produto por ID
- Atualização de produtos
- Exclusão de produtos
- Cadastro e gerenciamento de categorias
- Relacionamento entre produtos e categorias
- Busca de produtos por nome
- Filtro de produtos por categoria
- Identificação de produtos com estoque baixo
- Limite configurável para estoque baixo
- Registro de entrada de estoque
- Registro de saída de estoque
- Atualização automática da quantidade do produto
- Bloqueio de saída com estoque insuficiente
- Histórico de movimentações
- Filtro de movimentações por produto
- Filtro de movimentações por tipo
- Validação de dados com Pydantic
- Persistência de dados com PostgreSQL
- Documentação automática com Swagger

## Tecnologias

- Python
- FastAPI
- PostgreSQL
- Psycopg2
- Pydantic
- Uvicorn
- Git e GitHub

## Estrutura do projeto

```text
sistema-estoque/
│
├── backend/
│   ├── routes/
│   │   ├── categorias.py
│   │   ├── movimentacoes.py
│   │   └── produtos.py
│   │
│   ├── schemas/
│   │   ├── categoria.py
│   │   ├── movimentacao.py
│   │   └── produto.py
│   │
│   ├── database.py
│   ├── main.py
│   ├── produto.py
│   ├── repositorio.py
│   ├── repositorio_categoria.py
│   └── repositorio_movimentacao.py
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

Ative o ambiente virtual no Windows:

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

Depois crie um arquivo `.env` na raiz do projeto:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sistema_estoque
DB_USER=postgres
DB_PASSWORD=sua_senha
```

O arquivo `.env` não deve ser enviado ao GitHub.

## Executando a API

Com o ambiente virtual ativo:

```bash
python -m uvicorn backend.main:app --reload
```

A API ficará disponível em:

```text
http://127.0.0.1:8000
```

Documentação Swagger:

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

## Cadastro de produto

Exemplo:

```json
{
  "nome": "Switch Intelbras 8 Portas",
  "categoria_id": 1,
  "quantidade": 10,
  "preco": 189.90
}
```

## Busca e filtros de produtos

Buscar produtos pelo nome:

```text
GET /produtos?busca=Intelbras
```

Filtrar por categoria:

```text
GET /produtos?categoria_id=1
```

Buscar produtos com estoque baixo:

```text
GET /produtos?estoque_baixo=true
```

Definir limite personalizado:

```text
GET /produtos?estoque_baixo=true&limite_estoque=10
```

Combinar filtros:

```text
GET /produtos?busca=Intelbras&categoria_id=1&estoque_baixo=true&limite_estoque=10
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

A quantidade informada é adicionada ao estoque atual.

### Saída

```json
{
  "produto_id": 1,
  "tipo": "SAIDA",
  "quantidade": 3
}
```

A quantidade é removida do estoque atual.

O sistema impede uma saída maior que a quantidade disponível.

## Histórico de movimentações

Listar todas:

```text
GET /movimentacoes
```

Filtrar por produto:

```text
GET /movimentacoes?produto_id=1
```

Filtrar somente entradas:

```text
GET /movimentacoes?tipo=ENTRADA
```

Filtrar somente saídas:

```text
GET /movimentacoes?tipo=SAIDA
```

Combinar filtros:

```text
GET /movimentacoes?produto_id=1&tipo=SAIDA
```

## Regras de negócio

Cada produto pertence a uma categoria através de `categoria_id`.

Uma categoria com produtos vinculados não pode ser excluída.

Entradas aumentam automaticamente a quantidade em estoque.

Saídas reduzem automaticamente a quantidade em estoque.

Uma saída não pode deixar o estoque negativo.

Cada entrada ou saída gera um registro no histórico de movimentações.

A atualização do estoque e o registro da movimentação são realizados na mesma transação no PostgreSQL.

## Próximas funcionalidades

- Filtro de movimentações por período
- Relatórios de estoque
- Dashboard
- Autenticação de usuários
- Controle de permissões