# Sistema de Gestão de Estoque

API REST para gerenciamento de estoque desenvolvida com Python, FastAPI e PostgreSQL.

O projeto permite gerenciar produtos e categorias, consultar estoque e aplicar filtros para facilitar o controle dos itens armazenados.

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

O arquivo `.env` não deve ser enviado para o GitHub.

## Executando a API

Com o ambiente virtual ativo:

```bash
python -m uvicorn backend.main:app --reload
```

A API ficará disponível em:

```text
http://127.0.0.1:8000
```

A documentação Swagger:

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

O produto é relacionado à tabela de categorias através de `categoria_id`.

## Busca e filtros

Buscar produtos pelo nome:

```text
GET /produtos?busca=Intelbras
```

Filtrar pela categoria:

```text
GET /produtos?categoria_id=1
```

Buscar produtos com estoque baixo:

```text
GET /produtos?estoque_baixo=true
```

Definir o limite de estoque baixo:

```text
GET /produtos?estoque_baixo=true&limite_estoque=10
```

Também é possível combinar os filtros:

```text
GET /produtos?busca=Intelbras&categoria_id=1&estoque_baixo=true&limite_estoque=10
```

## Regras de categoria

Cada produto possui uma categoria relacionada através de uma chave estrangeira.

Uma categoria que possui produtos vinculados não pode ser excluída.

Ao alterar o nome de uma categoria, os produtos vinculados permanecem associados à mesma categoria.

## Próximas funcionalidades

- Movimentações de entrada de estoque
- Movimentações de saída de estoque
- Atualização automática da quantidade
- Histórico de movimentações
- Relatórios de estoque
- Autenticação de usuários