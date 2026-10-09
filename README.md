# Sistema de Gestão de Estoque e Compras

Sistema web para controlar o estoque e todo o ciclo de compras: da solicitação de compra às cotações, aprovação, pedido e recebimento, com entrada automática dos materiais no estoque.

O projeto é composto por uma API REST em **Python + FastAPI + PostgreSQL** e um **frontend em HTML, CSS e JavaScript**, servido pela própria API. Tem autenticação com JWT, perfis de permissão, notificações, anexos, sugestão automática de compra, leitura de orçamentos com IA, planilha de orçamento, auditoria, exportação para Excel e PDF, consulta de preços, migrations com Alembic, Docker e integração contínua no GitHub Actions.

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
- [Planilha de orçamento](#planilha-de-orçamento)
- [Leitura de orçamentos recebidos](#leitura-de-orçamentos-recebidos)
- [Notificações, anexos e sugestão de compra](#notificações-anexos-e-sugestão-de-compra)
- [Importar histórico de compras](#importar-histórico-de-compras)
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
- Painel no estilo dashboard: indicadores com ícones, gráfico de linhas das movimentações dos últimos 30 dias, rosca de produtos por categoria, últimas movimentações com o usuário que registrou e produtos abaixo do estoque mínimo
- Estoque mínimo por produto (padrão 5), usado no filtro de estoque baixo, no painel, nas notificações e na sugestão de compra; mínimo 0 marca compras avulsas, que nunca aparecem como estoque baixo
- Busca de produtos sem diferenciar acentos e maiúsculas, palavra por palavra (ex.: "cabo optico" acha "CABO ÓPTICO DROP")
- Importação do histórico de compras de um CSV do sistema antigo

**Compras**
- Fornecedores (ativos e inativos) e formas de pagamento (à vista, dia específico, a prazo de 1X a 12X)
- Solicitações de compra com vários itens
- Cotações por fornecedor, com preços por item, frete, prazo, validade e forma de pagamento
- Planilha de orçamento: modelo padrão em Excel com os itens da solicitação, importação da planilha preenchida como cotação e exportação das cotações em Excel ou PDF
- Solicitação a partir de orçamentos: envie os PDFs, prints ou XML de NF-e recebidos dos fornecedores; o sistema lê cada um, sugere fornecedor e produtos (e lembra as associações para a próxima vez), e a solicitação já nasce com as cotações
- Notificações: o sino no topo mostra o que cada perfil precisa fazer (cotar, aprovar, comprar, receber, repor estoque), com entregas atrasadas e estoque no mínimo em destaque
- Anexos na solicitação: notas fiscais, propostas, pedidos e boletos (PDF, imagem, XML, planilhas, até 10 MB); os orçamentos importados ficam anexados sozinhos
- Sugestão de compra: calcula o que repor pelo estoque mínimo, consumo médio, prazo de entrega e pedidos em aberto, e cria a solicitação com os itens escolhidos
- Comparação de cotações: menor total, menor prazo, menor frete e melhor preço de cada produto
- Aprovação e reprovação com justificativa; só o Administrador pode decidir sobre a própria solicitação
- Registro da compra com cópia dos valores aprovados
- Recebimento total ou parcial, com **entrada automática no estoque**
- Relatório de compras por período, fornecedor, produto e mês, com pontualidade das entregas
- Consulta de preços: histórico do que já foi pago e cotado, atalhos para o Mercado Livre e o Google Shopping e preços de referência anotados à mão
- Preço unitário com 4 casas decimais, para itens baratos comprados aos milhares

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
| Integração | HTTPX (Mercado Livre, Ollama e API da Anthropic) |
| Leitura de orçamentos | pypdfium2 (texto e imagem de PDFs), Pillow, XML de NF-e |
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

### Acesso pela internet (outra cidade)

Sem abrir portas no roteador, com o túnel gratuito da Cloudflare:

```powershell
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8000
```

O terminal mostra um endereço `https://...trycloudflare.com`; quem tiver o link acessa `.../app/`. O endereço muda toda vez que o túnel é reiniciado e só funciona enquanto o PC e o terminal estiverem ligados. Para um endereço fixo, é preciso um domínio próprio na Cloudflare e um túnel nomeado.

Antes de passar o link, lembre que qualquer pessoa com ele vê a tela de entrada: novos cadastros entram como **Consulta**, e o administrador decide o perfil em **Usuários**.

## Configuração (.env)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Sim | Conexão com o PostgreSQL |
| `JWT_SECRET_KEY` | Sim | Chave dos tokens de login. Gere com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `LOG_LEVEL` | Não | `DEBUG`, `INFO` (padrão), `WARNING` ou `ERROR` |
| `LOG_DIR` | Não | Pasta dos arquivos de log (padrão: `logs`) |
| `API_PORT` | Não | Porta da API no Docker (padrão: 8000) |
| `MERCADO_LIVRE_CLIENT_ID`, `MERCADO_LIVRE_CLIENT_SECRET`, `MERCADO_LIVRE_REDIRECT_URI` | Não | Consulta de preços no Mercado Livre |
| `OLLAMA_URL`, `OLLAMA_MODEL` | Não | Leitura de orçamentos em PDF e imagem com IA local e gratuita (Ollama). Modelo padrão `qwen2.5vl:7b` |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Não | Leitura de orçamentos pela API da Anthropic, paga por uso (modelo padrão `claude-sonnet-5-5`). Os arquivos são enviados à Anthropic |
| `LEITURA_ORCAMENTOS` | Não | `ollama` ou `anthropic`, quando as duas estão configuradas (padrão: `ollama`). Sem nenhuma, só XML de NF-e é lido |

O `.env` contém senhas e não vai para o GitHub. O modelo com todas as variáveis está em `.env.example`.

## Banco de dados e migrations

O esquema do banco é controlado pelo **Alembic**, na pasta `migrations/`. A API aplica as migrations pendentes sempre que inicia, então normalmente não é preciso rodar nada à mão.

| Migration | Conteúdo |
|---|---|
| `0001_esquema_inicial` | Todas as tabelas do sistema |
| `0002_credenciais_externas` | Tokens das APIs de preço |
| `0003_estoque_minimo_e_usuario` | Estoque mínimo por produto e usuário que registrou cada movimentação |
| `0004_referencias_fornecedor` | Como cada fornecedor chama nossos produtos (para a leitura de orçamentos) e preço unitário com 4 casas |
| `0005_precos_referencia` | Preços de referência anotados na tela de preços |
| `0006_anexos` | Anexos das solicitações, guardados no próprio banco (entram no backup) |

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

Telas: Entrar e criar conta, Painel, Produtos, Categorias, Movimentações, Fornecedores, Formas de pagamento, Sugestão de compra, Solicitações, Importar orçamentos, Detalhe da solicitação (com cotações, anexos e recebimentos), Compras, Relatório de compras, Usuários e Auditoria.

- **Painel**: indicadores de produtos, valor do estoque, estoque baixo e movimentações do mês (comparadas aos mesmos dias do mês anterior); valores grandes diminuem a fonte em vez de quebrar a linha.
- **Sino de notificações**: na barra do topo, com o número de pendências, atualizado a cada minuto e a cada troca de tela.
- **Relatório de compras**: mostra os 10 maiores de cada resumo, com botão para ver todos.

- **Visual**: barra de navegação escura, cartões brancos e cabeçalhos limpos (a serra ao entardecer fica na tela de entrada), títulos e números em *Roboto* e textos em *Open Sans*.
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
| Anexar arquivos à solicitação | ✓ | ✓ | | ✓ | |
| Criar solicitação pela sugestão de compra | ✓ | ✓ | | ✓ | |
| Gerenciar usuários e ver a auditoria | ✓ | | | | |

- O primeiro usuário de um banco novo é Administrador; os seguintes entram como Consulta.
- Ninguém aprova ou reprova uma solicitação criada por si, exceto o Administrador.
- Um administrador não pode remover o próprio acesso de administrador.
- Sem permissão, a API responde `403` e o frontend esconde o botão.

## Consulta de preços

O botão **Preços** de cada produto mostra:

- **Histórico interno**: último preço pago, média, menor e maior, últimas compras e últimas cotações. Funciona sempre.
- **Preços de mercado**: botões que abrem a busca do produto no Mercado Livre e no Google Shopping, e um campo para anotar o preço encontrado (loja, link e observação). Os preços anotados ficam no histórico do produto e aparecem ao lado do preço na cotação.
- **Consulta automática no Mercado Livre** (opcional): só funciona se o Mercado Livre liberar a busca para o seu aplicativo.

O formulário de cotação também mostra o último preço pago e a média ao lado de cada item.

### Ativar o Mercado Livre

1. Crie um aplicativo em [developers.mercadolivre.com.br](https://developers.mercadolivre.com.br). Cadastre como endereço de retorno (*redirect URI*) `https://httpbin.org/get`: ele mostra o código na tela. Evite `https://www.google.com.br`, porque o Google redireciona e apaga o código do endereço.
2. Preencha no `.env`: `MERCADO_LIVRE_CLIENT_ID`, `MERCADO_LIVRE_CLIENT_SECRET` e `MERCADO_LIVRE_REDIRECT_URI`.
3. Rode a autorização uma vez:

   ```bash
   python -m backend.precos.autorizar_mercado_livre
   # com Docker:
   docker compose exec api python -m backend.precos.autorizar_mercado_livre
   ```

   Abra o endereço que aparecer e autorize o aplicativo. A página do httpbin mostra `"code": "TG-..."`; cole esse código no terminal (vale por poucos minutos).

Desde 2025 o Mercado Livre bloqueia a busca pública de anúncios (`/sites/MLB/search`, erro 403) para a maioria dos aplicativos. Quando isso acontece, o sistema busca no **catálogo de produtos** (`/products/search`) e pega o menor preço dos anúncios de cada produto. Para ver o que está liberado para o seu aplicativo:

```bash
python -m backend.precos.diagnosticar_mercado_livre "switch 8 portas"
```

O token do Mercado Livre expira em poucas horas. O sistema renova sozinho e guarda o token novo no banco, na tabela `credenciais_externas`. Se a autorização for revogada, a tela de preços avisa para rodar o passo 3 de novo. Para um teste rápido sem OAuth, também é possível colocar um token pronto em `MERCADO_LIVRE_TOKEN`, mas ele para de funcionar quando expira.

### Adicionar outra fonte de preços

As fontes ficam em `backend/precos/`. Crie uma classe que herde de `FontePreco`, com `nome`, `configurada()` e `buscar(termo, limite)` devolvendo um `ResultadoFonte`, e acrescente uma instância à lista `FONTES` em `backend/precos/servico.py`. A tela de preços passa a mostrá-la automaticamente.
## Planilha de orçamento

No detalhe de uma solicitação, o comprador baixa o **modelo padrão em Excel** com os itens já preenchidos, envia ao fornecedor e importa a planilha devolvida como cotação. Importar de novo a planilha do mesmo fornecedor atualiza a cotação. Todas as cotações podem ser exportadas em Excel ou PDF, lado a lado, para comparar ou arquivar.

## Leitura de orçamentos recebidos

A tela **Solicitações > Importar orçamentos** cria a solicitação a partir dos orçamentos que chegam dos fornecedores:

1. Envie os arquivos: PDF, print/foto ou XML de NF-e.
2. O sistema lê fornecedor, itens, preços, frete e prazo, e sugere o fornecedor e os produtos cadastrados.
3. Você revisa e corrige as associações. Elas ficam guardadas: na próxima vez, o código ou a descrição do fornecedor já é reconhecido.
4. A solicitação nasce em cotação, com uma cotação por orçamento e os arquivos originais anexados.

O XML de NF-e é lido sem IA. PDFs e imagens precisam de uma das opções abaixo.

| Opção | Custo | Observação |
|---|---|---|
| **Ollama** (IA local) | Grátis | Roda no próprio PC; precisa de uma máquina razoável |
| **API da Anthropic** | Paga por uso | Mais precisa; os arquivos são enviados à Anthropic. Preencha `ANTHROPIC_API_KEY` |

Com as duas configuradas, `LEITURA_ORCAMENTOS` escolhe qual usar.

### Ollama

Para ler de graça e sem enviar os arquivos para fora da empresa:

1. Instale o [Ollama](https://ollama.com) no PC que roda a API (Windows, macOS ou Linux).
2. Baixe um modelo que entende imagens: `ollama pull qwen2.5vl:7b` (cerca de 6 GB; precisa de 16 GB de RAM, e uma placa de vídeo deixa bem mais rápido). Em máquinas mais fracas, `qwen2.5vl:3b` é menor e menos preciso.
3. No `.env`, preencha `OLLAMA_URL=http://localhost:11434` (ou `http://host.docker.internal:11434` se a API roda no Docker) e reinicie a API.

PDFs com texto são enviados ao modelo como texto, o que é rápido e funciona até com modelos só de texto. Prints, fotos e PDFs escaneados vão como imagem.

## Notificações, anexos e sugestão de compra

**Notificações**: o sino mostra só o que o perfil de cada um precisa fazer, calculado na hora a partir da situação atual (não há mensagens a marcar como lidas; a pendência some quando a tarefa é feita).

| Pendência | Quem vê |
|---|---|
| Solicitações abertas para cotar | Administrador e Comprador |
| Solicitações em cotação prontas para aprovar | Administrador e Aprovador |
| Aprovadas aguardando o registro da compra | Administrador e Comprador |
| Compras a receber (atrasadas em destaque) | Administrador e Almoxarife |
| Produtos no estoque mínimo ou abaixo | Administrador, Almoxarife e Comprador |

**Anexos**: cada solicitação guarda notas fiscais, propostas, pedidos, boletos e outros arquivos (PDF, imagens, XML, Excel, CSV e Word, até 10 MB). PDFs e imagens abrem no navegador; os demais são baixados. Quem enviou ou um administrador pode excluir.

**Sugestão de compra**: lista o que repor e quanto comprar, e cria a solicitação com os itens marcados.

- Consumo médio: saídas do período escolhido (30 dias a 12 meses) divididas pelo número de dias.
- Prazo de entrega: média das cotações aprovadas do produto; sem histórico, 7 dias.
- Em pedido: solicitações abertas, em cotação ou aprovadas, mais o comprado que ainda não chegou.
- Repor quando: estoque + em pedido ≤ mínimo + consumo durante o prazo de entrega.
- Quanto comprar: o mínimo mais o consumo do prazo e da cobertura escolhida, e pelo menos um lote do tamanho do mínimo.
- Produtos com estoque mínimo 0 são compras avulsas e não são sugeridos.

## Importar histórico de compras

Carrega um CSV de "Itens do Pedido de Compra" (exportado do sistema antigo) passando por todo o fluxo: solicitação, cotação, aprovação, compra e recebimento, com as datas originais. Fornecedores, categorias, produtos e formas de pagamento que faltarem são criados. Solicitantes e aprovadores do histórico viram usuários desativados.

```bash
pg_dump -U postgres sistema_estoque > backup.sql   # recomendado antes
python -m backend.importacao.historico_compras pedidos.csv --email seu@email.com --estoque-minimo --forcar
```

- `--estoque-minimo`: define o mínimo dos itens do grupo "Estoque" pela média de compras.
- `--simular-consumo`: cria saídas **fictícias** para o painel e a sugestão de compra terem dados. Use só para demonstração.
- `--forcar`: importa mesmo que o banco já tenha solicitações.
- `--banco nome`: importa em outro banco (criado se não existir), sem mexer no principal.

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
| Planilha de orçamento | `GET .../cotacoes/modelo`, `POST .../cotacoes/importar` (arquivo .xlsx; `substituir=true` atualiza a cotação do mesmo fornecedor), `GET .../cotacoes/exportar?formato=xlsx\|pdf`, `GET .../cotacoes/{cotacao_id}/planilha` |
| Orçamentos recebidos | `GET /orcamentos/configuracao`, `POST /orcamentos/ler` (PDF, imagem ou XML; não grava nada), `POST /orcamentos/solicitacao` (cria a solicitação e as cotações numa transação) |
| Notificações | `GET /notificacoes` (pendências do usuário logado, conforme o perfil) |
| Anexos | `GET/POST /solicitacoes-compra/{id}/anexos`, `GET/DELETE .../anexos/{anexo_id}` |
| Sugestão de compra | `GET /sugestoes-compra?dias_consumo=90&cobertura_dias=30&prazo_padrao=7&todos=false` |
| Compras | `POST/GET /solicitacoes-compra/{id}/compra`, `GET /compras`, `GET /compras/{id}` |
| Recebimentos | `POST/GET /solicitacoes-compra/{id}/compra/recebimentos` |
| Preços | `GET /precos/fontes`, `GET /precos/produtos/{id}`, `POST /precos/produtos/{id}/referencias`, `DELETE /precos/referencias/{referencia_id}` |
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
- Recebimentos com data passada entram no estoque com essa data.
- Anexos aceitam só tipos conhecidos e até 10 MB; só PDFs e imagens abrem no navegador.

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
│   ├── planilha_orcamento.py     modelo, importação e exportação de cotações
│   ├── busca.py                  busca sem acentos, palavra por palavra
│   ├── orcamentos/               leitura de orçamentos (NF-e, PDF, Ollama, Anthropic)
│   ├── precos/                   fontes de preço, histórico e preços de referência
│   ├── importacao/               importação do histórico de compras (CSV)
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

São cerca de 400 casos de teste, cobrindo estoque, todo o fluxo de compras, permissões, notificações, anexos, sugestão de compra, planilha e leitura de orçamentos, importação do histórico, auditoria, exportação, migrations e a consulta de preços. As chamadas ao Mercado Livre, ao Ollama e à Anthropic são simuladas, sem acessar a internet.

O sistema também foi testado com um histórico real de 509 pedidos: estoque, totais e datas conferiram com o CSV original.

O GitHub Actions roda dois jobs a cada push e pull request na `main`:

1. **tests**: sobe um PostgreSQL, instala as dependências e roda toda a suíte.
2. **docker**: constrói as imagens, sobe o `docker compose` e confere a API, o frontend, as migrations e o cadastro de usuário.

## Possíveis evoluções

Já concluídos: notificações para quem precisa agir, anexos de notas fiscais e propostas, sugestão automática de compra, leitura de orçamentos com IA, planilha de orçamento e importação do histórico. Ideias para o futuro:

- Recuperação de senha por e-mail
- Notificações por e-mail ou WhatsApp, além do sino
- Opção para desativar o cadastro público, quando o sistema estiver na internet
- Endereço fixo na internet (domínio próprio com túnel nomeado da Cloudflare)
- Outras fontes de preço automáticas além do Mercado Livre
