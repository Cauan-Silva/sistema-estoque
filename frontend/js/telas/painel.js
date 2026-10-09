import { api, listarTodos, montarQuery } from "../api.js";
import { anel, barras, cartaoIndicador, colunasAgrupadas, miniBarras, progresso } from "../graficos.js";
import { cabecalho, corStatus, etiquetaStatus, formatar, h, tabela } from "../ui.js";

const CORES_CATEGORIAS = 6;

function corDaCategoria(categoriaId) {
  return `var(--cor-${((Number(categoriaId) || 1) - 1) % CORES_CATEGORIAS + 1})`;
}

function variacaoMensal(atual, anterior) {
  if (!anterior) return null;

  const percentual = Math.round(((atual - anterior) / anterior) * 100);

  if (!percentual) return null;

  return {
    texto: `${Math.abs(percentual)}% vs mês anterior`,
    sentido: percentual > 0 ? "alta" : "baixa",
    tom: "neutro",
  };
}

const MESES_GRAFICO = 6;

function ultimosMeses(quantidade) {
  const hoje = new Date();
  return Array.from({ length: quantidade }, (_, indice) => {
    const data = new Date(hoje.getFullYear(), hoje.getMonth() - (quantidade - 1 - indice), 1);
    return {
      chave: `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, "0")}`,
      rotulo: data.toLocaleDateString("pt-BR", { month: "short" }).replace(".", ""),
    };
  });
}

function valorPorCategoria(produtos) {
  const totais = new Map();

  produtos.forEach((produto) => {
    const atual = totais.get(produto.categoria_id) || { rotulo: produto.categoria, valor: 0 };
    atual.valor += produto.quantidade * produto.preco;
    totais.set(produto.categoria_id, atual);
  });

  const ordenados = [...totais.entries()]
    .map(([id, item]) => ({ ...item, cor: corDaCategoria(id) }))
    .sort((a, b) => b.valor - a.valor);

  if (ordenados.length <= 7) return ordenados;

  const outras = ordenados.slice(6).reduce((soma, item) => soma + item.valor, 0);
  return [...ordenados.slice(0, 6), { rotulo: "Outras", valor: outras, cor: "var(--tinta-suave)" }];
}

function movimentosPorMes(movimentacoes, meses) {
  const entradas = new Map(meses.map((mes) => [mes.chave, 0]));
  const saidas = new Map(meses.map((mes) => [mes.chave, 0]));

  movimentacoes.forEach((movimentacao) => {
    const chave = movimentacao.data_movimentacao.slice(0, 7);
    const alvo = movimentacao.tipo === "ENTRADA" ? entradas : saidas;
    if (alvo.has(chave)) alvo.set(chave, alvo.get(chave) + movimentacao.quantidade);
  });

  return {
    entradas: meses.map((mes) => entradas.get(mes.chave)),
    saidas: meses.map((mes) => saidas.get(mes.chave)),
  };
}

const LIMITE_ESTOQUE_BAIXO = 5;

export async function telaPainel(area) {
  const meses = ultimosMeses(MESES_GRAFICO);

  const [resumo, maiorValor, estoqueBaixo, abertas, emCotacao, aprovadas, compradas, produtos, movimentacoes] = await Promise.all([
    api.get(`/relatorios/resumo${montarQuery({ limite_estoque: LIMITE_ESTOQUE_BAIXO })}`),
    api.get("/relatorios/maior-valor?limite=5"),
    api.get(
      `/produtos${montarQuery({ estoque_baixo: true, limite_estoque: LIMITE_ESTOQUE_BAIXO, tamanho: 8 })}`
    ),
    api.get("/solicitacoes-compra?status=ABERTA&tamanho=100"),
    api.get("/solicitacoes-compra?status=EM_COTACAO&tamanho=100"),
    api.get("/solicitacoes-compra?status=APROVADA&tamanho=100"),
    api.get("/solicitacoes-compra?status=COMPRADA&tamanho=100"),
    listarTodos("/produtos"),
    listarTodos("/movimentacoes", { data_inicio: `${meses[0].chave}-01T00:00:00` }),
  ]);

  const porMes = movimentosPorMes(movimentacoes, meses);
  const categorias = valorPorCategoria(produtos);

  const pendentes = [...compradas, ...aprovadas, ...emCotacao, ...abertas].slice(0, 8);

  area.replaceChildren(
    cabecalho("Painel", "Situação do estoque e das compras em andamento."),
    h(
      "div",
      { class: "cartoes-indicador" },
      cartaoIndicador({
        rotulo: "Valor em estoque",
        valor: formatar.moeda(resumo.valor_total_estoque),
        cor: "1",
        detalhe: `${formatar.numero(resumo.total_categorias)} categorias`,
        visual: miniBarras(categorias, formatar.moeda),
      }),
      cartaoIndicador({
        rotulo: "Unidades em estoque",
        valor: formatar.numero(resumo.unidades_em_estoque),
        cor: "4",
        detalhe: `em ${formatar.numero(resumo.total_produtos)} produtos`,
        variacao: variacaoMensal(porMes.entradas.at(-1), porMes.entradas.at(-2)),
        visual: miniBarras(
          meses.map((mes, indice) => ({ rotulo: mes.rotulo, valor: porMes.entradas[indice] })),
          (valor) => `${formatar.numero(valor)} un. de entrada`
        ),
      }),
      cartaoIndicador({
        rotulo: `Estoque baixo (${LIMITE_ESTOQUE_BAIXO} ou menos)`,
        valor: formatar.numero(resumo.produtos_estoque_baixo),
        cor: resumo.produtos_estoque_baixo > 0 ? "alerta" : "3",
        detalhe:
          resumo.produtos_estoque_baixo > 0
            ? `de ${formatar.numero(resumo.total_produtos)} produtos precisam de reposição`
            : "Nenhum produto precisa de reposição",
        visual: progresso(resumo.produtos_estoque_baixo, resumo.total_produtos, "Parte dos produtos com estoque baixo"),
      }),
      cartaoIndicador({
        rotulo: "Compras em andamento",
        valor: formatar.numero(abertas.length + emCotacao.length + aprovadas.length + compradas.length),
        cor: "2",
        detalhe: `${formatar.numero(compradas.length)} aguardando entrega`,
        visual: anel(
          [
            { nome: "Abertas", valor: abertas.length, cor: `var(--fibra-${corStatus("ABERTA")})` },
            { nome: "Em cotação", valor: emCotacao.length, cor: `var(--fibra-${corStatus("EM_COTACAO")})` },
            { nome: "Aprovadas", valor: aprovadas.length, cor: `var(--fibra-${corStatus("APROVADA")})` },
            { nome: "Compradas", valor: compradas.length, cor: `var(--fibra-${corStatus("COMPRADA")})` },
          ]
        ),
      })
    ),
    h(
      "div",
      { class: "graficos" },
      barras({
        titulo: "Valor em estoque por categoria",
        descricao: "Quantidade × preço de cada produto, somado por categoria.",
        itens: categorias,
        formatar: formatar.moeda,
        vazio: "Cadastre produtos para ver o valor por categoria.",
      }),
      colunasAgrupadas({
        titulo: "Entradas e saídas por mês",
        descricao: `Unidades movimentadas nos últimos ${MESES_GRAFICO} meses.`,
        categorias: meses.map((mes) => mes.rotulo),
        series: [
          { nome: "Entradas", cor: "var(--grafico-1)", valores: porMes.entradas },
          { nome: "Saídas", cor: "var(--grafico-2)", valores: porMes.saidas },
        ],
        formatar: (valor) => `${formatar.numero(valor)} un.`,
        vazio: "Nenhuma movimentação nos últimos meses.",
      })
    ),
    h(
      "div",
      { class: "colunas" },
      h(
        "section",
        { class: "secao" },
        h(
          "div",
          { class: "titulo-secao" },
          h("h2", {}, "Estoque baixo"),
          h("a", { href: "#/produtos" }, "Ver produtos")
        ),
        tabela(
          [
            { titulo: "Produto", valor: (p) => p.nome },
            { titulo: "Categoria", valor: (p) => p.categoria },
            { titulo: "Quantidade", classe: "direita numero", valor: (p) => formatar.numero(p.quantidade) },
          ],
          estoqueBaixo,
          { vazio: "Nenhum produto com estoque baixo." }
        )
      ),
      h(
        "section",
        { class: "secao" },
        h(
          "div",
          { class: "titulo-secao" },
          h("h2", {}, "Compras em andamento"),
          h("a", { href: "#/solicitacoes" }, "Ver solicitações")
        ),
        tabela(
          [
            {
              titulo: "Solicitação",
              valor: (s) => h("a", { href: `#/solicitacoes/${s.id}` }, `Nº ${s.id}`),
            },
            { titulo: "Itens", classe: "numero", valor: (s) => s.itens.length },
            { titulo: "Status", valor: (s) => etiquetaStatus(s.status) },
          ],
          pendentes,
          { vazio: "Nenhuma compra em andamento." }
        )
      )
    ),
    h(
      "section",
      { class: "secao" },
      h("h2", {}, "Maior valor em estoque"),
      tabela(
        [
          { titulo: "Produto", valor: (p) => p.nome },
          { titulo: "Categoria", valor: (p) => p.categoria },
          { titulo: "Quantidade", classe: "direita numero", valor: (p) => formatar.numero(p.quantidade) },
          { titulo: "Preço", classe: "direita numero", valor: (p) => formatar.moeda(p.preco) },
          { titulo: "Valor em estoque", classe: "direita numero", valor: (p) => formatar.moeda(p.valor_estoque) },
        ],
        maiorValor,
        { vazio: "Cadastre produtos para ver o valor em estoque." }
      )
    ),
    h(
      "p",
      { class: "suave" },
      `Unidades que entraram no estoque: ${formatar.numero(resumo.total_entradas)}. Unidades que saíram: ${formatar.numero(resumo.total_saidas)}.`
    )
  );
}
