import { api, montarQuery } from "../api.js";
import { cabecalho, etiquetaStatus, formatar, h, tabela } from "../ui.js";

const LIMITE_ESTOQUE_BAIXO = 5;

export async function telaPainel(area) {
  const [resumo, maiorValor, estoqueBaixo, abertas, emCotacao, aprovadas, compradas] = await Promise.all([
    api.get(`/relatorios/resumo${montarQuery({ limite_estoque: LIMITE_ESTOQUE_BAIXO })}`),
    api.get("/relatorios/maior-valor?limite=5"),
    api.get(
      `/produtos${montarQuery({ estoque_baixo: true, limite_estoque: LIMITE_ESTOQUE_BAIXO, tamanho: 8 })}`
    ),
    api.get("/solicitacoes-compra?status=ABERTA&tamanho=100"),
    api.get("/solicitacoes-compra?status=EM_COTACAO&tamanho=100"),
    api.get("/solicitacoes-compra?status=APROVADA&tamanho=100"),
    api.get("/solicitacoes-compra?status=COMPRADA&tamanho=100"),
  ]);

  const indicador = (rotulo, valor, alerta = false) =>
    h("div", { class: `indicador ${alerta ? "alerta" : ""}` }, h("dt", {}, rotulo), h("dd", {}, valor));

  const pendentes = [...compradas, ...aprovadas, ...emCotacao, ...abertas].slice(0, 8);

  area.replaceChildren(
    cabecalho("Painel", "Situação do estoque e das compras em andamento."),
    h(
      "dl",
      { class: "indicadores" },
      indicador("Valor em estoque", formatar.moeda(resumo.valor_total_estoque)),
      indicador("Produtos", formatar.numero(resumo.total_produtos)),
      indicador("Unidades", formatar.numero(resumo.unidades_em_estoque)),
      indicador(
        `Com ${LIMITE_ESTOQUE_BAIXO} ou menos`,
        formatar.numero(resumo.produtos_estoque_baixo),
        resumo.produtos_estoque_baixo > 0
      ),
      indicador(
        "Compras em andamento",
        formatar.numero(abertas.length + emCotacao.length + aprovadas.length + compradas.length)
      ),
      indicador("Aguardando entrega", formatar.numero(compradas.length))
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
