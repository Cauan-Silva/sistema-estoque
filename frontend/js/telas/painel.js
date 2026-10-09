import { api, listarTodos } from "../api.js";
import { linhaArea, rosca } from "../graficos.js";
import { icone } from "../icones.js";
import { cabecalho, etiquetaStatus, formatar, h, tabela } from "../ui.js";

const DIAS_GRAFICO = 30;
const CATEGORIAS_ROSCA = 4;
const CORES_ROSCA = ["var(--cor-4)", "var(--cor-1)", "var(--cor-3)", "var(--cor-2)"];

function chaveDia(data) {
  return `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, "0")}-${String(data.getDate()).padStart(2, "0")}`;
}

function ultimosDias(quantidade) {
  const hoje = new Date();
  return Array.from({ length: quantidade }, (_, indice) => {
    const data = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() - (quantidade - 1 - indice));
    return {
      chave: chaveDia(data),
      rotulo: `${String(data.getDate()).padStart(2, "0")}/${String(data.getMonth() + 1).padStart(2, "0")}`,
    };
  });
}

function movimentosPorDia(movimentacoes, dias) {
  const entradas = new Map(dias.map((dia) => [dia.chave, 0]));
  const saidas = new Map(dias.map((dia) => [dia.chave, 0]));

  movimentacoes.forEach((movimentacao) => {
    const chave = movimentacao.data_movimentacao.slice(0, 10);
    const alvo = movimentacao.tipo === "ENTRADA" ? entradas : saidas;
    if (alvo.has(chave)) alvo.set(chave, alvo.get(chave) + movimentacao.quantidade);
  });

  return {
    entradas: dias.map((dia) => entradas.get(dia.chave)),
    saidas: dias.map((dia) => saidas.get(dia.chave)),
  };
}

function produtosPorCategoria(produtos) {
  const contagem = new Map();
  produtos.forEach((produto) => contagem.set(produto.categoria, (contagem.get(produto.categoria) || 0) + 1));

  const ordenadas = [...contagem.entries()].sort((a, b) => b[1] - a[1]);
  const principais = ordenadas.slice(0, CATEGORIAS_ROSCA).map(([nome, valor], indice) => ({
    nome,
    valor,
    cor: CORES_ROSCA[indice],
  }));
  const restantes = ordenadas.slice(CATEGORIAS_ROSCA).reduce((soma, [, valor]) => soma + valor, 0);

  return restantes ? [...principais, { nome: "Outras", valor: restantes, cor: "var(--linha-forte)" }] : principais;
}

function tendencia(atual, anterior) {
  if (!anterior) return null;
  const percentual = Math.round(((atual - anterior) / anterior) * 100);
  return { percentual, sentido: percentual >= 0 ? "alta" : "baixa" };
}

/* Valores grandes (R$ 4.501.762,99) diminuem a fonte em vez de quebrar a linha. */
export function tamanhoValor(texto) {
  const comprimento = String(texto).length;
  return comprimento > 15 ? "muito-longo" : comprimento > 11 ? "longo" : "normal";
}

function indicador({ nomeIcone, cor, rotulo, valor, variacao, legenda }) {
  return h(
    "article",
    { class: "kpi", dataset: { cor } },
    h("span", { class: "kpi-icone" }, icone(nomeIcone)),
    h(
      "div",
      { class: "kpi-texto" },
      h("h3", {}, rotulo),
      h("p", { class: "kpi-valor", dataset: { tamanho: tamanhoValor(valor) } }, valor),
      variacao
        ? h(
            "p",
            { class: "kpi-variacao", dataset: { sentido: variacao.sentido } },
            icone(variacao.sentido),
            `${variacao.percentual > 0 ? "+" : ""}${variacao.percentual}%`
          )
        : null,
      h("p", { class: "kpi-legenda" }, legenda)
    )
  );
}

function bloco(titulo, acao, ...conteudo) {
  return h(
    "section",
    { class: "bloco" },
    h("div", { class: "bloco-topo" }, h("h2", {}, titulo), acao || null),
    conteudo
  );
}

function verTodos(texto, destino) {
  return h("a", { class: "ver-todos", href: destino }, texto, icone("seta"));
}

function hojePorExtenso() {
  const texto = new Date().toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
  return h("p", { class: "data-hoje" }, icone("calendario"), `Hoje, ${texto}`);
}

export async function telaPainel(area) {
  const dias = ultimosDias(DIAS_GRAFICO);
  const hoje = new Date();
  const mesAtual = chaveDia(hoje).slice(0, 7);
  const inicioMesAnterior = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
  const mesAnterior = chaveDia(inicioMesAnterior).slice(0, 7);
  const inicioBusca = dias[0].chave < chaveDia(inicioMesAnterior) ? dias[0].chave : chaveDia(inicioMesAnterior);

  const [resumo, estoqueBaixo, ultimas, abertas, emCotacao, aprovadas, compradas, produtos, movimentacoes] =
    await Promise.all([
      api.get("/relatorios/resumo"),
      api.get("/produtos?estoque_baixo=true&tamanho=5"),
      api.get("/movimentacoes?tamanho=5"),
      api.get("/solicitacoes-compra?status=ABERTA&tamanho=100"),
      api.get("/solicitacoes-compra?status=EM_COTACAO&tamanho=100"),
      api.get("/solicitacoes-compra?status=APROVADA&tamanho=100"),
      api.get("/solicitacoes-compra?status=COMPRADA&tamanho=100"),
      listarTodos("/produtos"),
      listarTodos("/movimentacoes", { data_inicio: `${inicioBusca}T00:00:00` }),
    ]);

  const porDia = movimentosPorDia(movimentacoes, dias);
  // Compara com os mesmos dias do mês anterior (1 a hoje), e não com o mês anterior inteiro.
  const diaDeHoje = String(hoje.getDate()).padStart(2, "0");
  const noMes = movimentacoes.filter((m) => m.data_movimentacao.startsWith(mesAtual)).length;
  const noMesAnterior = movimentacoes.filter(
    (m) => m.data_movimentacao.startsWith(mesAnterior) && m.data_movimentacao.slice(8, 10) <= diaDeHoje
  ).length;
  const variacaoMes = tendencia(noMes, noMesAnterior);
  const pendentes = [...compradas, ...aprovadas, ...emCotacao, ...abertas].slice(0, 6);

  area.replaceChildren(
    cabecalho("Painel", "Visão geral do estoque, das movimentações e das compras.", hojePorExtenso()),
    h(
      "div",
      { class: "kpis" },
      indicador({
        nomeIcone: "pacote",
        cor: "4",
        rotulo: "Total de produtos",
        valor: formatar.numero(resumo.total_produtos),
        legenda: `Em ${formatar.numero(resumo.total_categorias)} categorias`,
      }),
      indicador({
        nomeIcone: "banco",
        cor: "3",
        rotulo: "Valor estimado do estoque",
        valor: formatar.moeda(resumo.valor_total_estoque),
        legenda: `${formatar.numero(resumo.unidades_em_estoque)} unidades em estoque`,
      }),
      indicador({
        nomeIcone: "alerta",
        cor: "alerta",
        rotulo: "Produtos com estoque baixo",
        valor: formatar.numero(resumo.produtos_estoque_baixo),
        legenda: resumo.produtos_estoque_baixo
          ? "No estoque mínimo ou abaixo dele"
          : "Nenhum produto abaixo do mínimo",
      }),
      indicador({
        nomeIcone: "trocas",
        cor: "1",
        rotulo: "Movimentações no mês",
        valor: formatar.numero(noMes),
        variacao: variacaoMes,
        legenda: variacaoMes
          ? `Em relação aos mesmos ${Number(diaDeHoje)} dias do mês anterior`
          : "Sem movimentações no mesmo período do mês anterior",
      })
    ),
    h(
      "div",
      { class: "blocos blocos-grafico" },
      bloco(
        "Movimentações no período",
        h(
          "ul",
          { class: "legenda-linha" },
          h("li", {}, h("span", { class: "ponto", style: { background: "var(--cor-4)" } }), "Entradas"),
          h("li", {}, h("span", { class: "ponto", style: { background: "var(--cor-3)" } }), "Saídas")
        ),
        h("p", { class: "bloco-descricao" }, `Unidades por dia nos últimos ${DIAS_GRAFICO} dias.`),
        linhaArea({
          rotulos: dias.map((dia) => dia.rotulo),
          series: [
            { nome: "Entradas", cor: "var(--cor-4)", valores: porDia.entradas },
            { nome: "Saídas", cor: "var(--cor-3)", valores: porDia.saidas },
          ],
          formatar: formatar.numero,
          vazio: `Nenhuma movimentação nos últimos ${DIAS_GRAFICO} dias.`,
        })
      ),
      bloco(
        "Produtos por categoria",
        null,
        produtos.length
          ? rosca(produtosPorCategoria(produtos), {
              centro: formatar.numero(produtos.length),
              legendaCentro: produtos.length === 1 ? "produto" : "produtos",
            })
          : h("p", { class: "grafico-vazio suave" }, "Cadastre produtos para ver a distribuição.")
      )
    ),
    h(
      "div",
      { class: "blocos blocos-tabela" },
      bloco(
        "Últimas movimentações",
        verTodos("Ver todas", "#/movimentacoes"),
        tabela(
          [
            { titulo: "Data", valor: (m) => formatar.data(m.data_movimentacao) },
            { titulo: "Produto", valor: (m) => m.produto_nome },
            {
              titulo: "Tipo",
              valor: (m) =>
                h(
                  "span",
                  { class: "chip-tipo", dataset: { tipo: m.tipo } },
                  m.tipo === "ENTRADA" ? "Entrada" : "Saída"
                ),
            },
            { titulo: "Quantidade", classe: "numero", valor: (m) => formatar.numero(m.quantidade) },
            {
              titulo: "Usuário",
              valor: (m) => m.usuario || (m.recebimento_id ? `Recebimento Nº ${m.recebimento_id}` : "—"),
            },
          ],
          ultimas,
          { vazio: "Nenhuma movimentação registrada." }
        )
      ),
      bloco(
        "Produtos com estoque baixo",
        verTodos("Ver todos", "#/produtos"),
        tabela(
          [
            {
              titulo: "Produto",
              valor: (p) => h("span", { class: "produto-celula" }, h("span", { class: "produto-icone" }, icone("pacote")), p.nome),
            },
            {
              titulo: "Estoque atual",
              classe: "numero",
              valor: (p) =>
                h(
                  "span",
                  { class: p.quantidade * 2 <= p.estoque_minimo ? "critico" : "" },
                  formatar.numero(p.quantidade)
                ),
            },
            {
              titulo: "Estoque mínimo",
              classe: "numero",
              valor: (p) => h("span", { class: "chip-minimo" }, formatar.numero(p.estoque_minimo)),
            },
          ],
          estoqueBaixo,
          { vazio: "Nenhum produto com estoque baixo." }
        )
      )
    ),
    bloco(
      "Compras em andamento",
      verTodos("Ver solicitações", "#/solicitacoes"),
      tabela(
        [
          { titulo: "Solicitação", valor: (s) => h("a", { href: `#/solicitacoes/${s.id}` }, `Nº ${s.id}`) },
          { titulo: "Itens", classe: "numero", valor: (s) => s.itens.length },
          { titulo: "Status", valor: (s) => etiquetaStatus(s.status) },
        ],
        pendentes,
        { vazio: "Nenhuma compra em andamento." }
      )
    )
  );
}
