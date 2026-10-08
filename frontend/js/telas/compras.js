import { api, montarQuery } from "../api.js";
import { cabecalho, campoFiltro, executar, formatar, h, paginacao, seletor, tabela } from "../ui.js";
import { abrirRegistroCompra } from "./acoes_compra.js";

const TAMANHO = 20;

export async function telaCompras(area) {
  const fornecedores = await api.get("/fornecedores");
  const filtros = { fornecedor_id: "", pagina: 1 };
  const lista = h("div");
  const aguardando = h("div");

  async function carregarAguardando() {
    const aprovadas = await executar(() => api.get("/solicitacoes-compra?status=APROVADA&tamanho=100"));
    if (!aprovadas) return;

    if (!aprovadas.length) {
      aguardando.replaceChildren();
      return;
    }

    const cotacoes = await Promise.all(
      aprovadas.map((s) =>
        api.get(`/solicitacoes-compra/${s.id}/cotacoes/${s.cotacao_aprovada_id}`).catch(() => null)
      )
    );

    const linhas = aprovadas.map((solicitacao, indice) => ({ solicitacao, cotacao: cotacoes[indice] }));

    aguardando.replaceChildren(
      h(
        "section",
        { class: "secao" },
        h("h2", {}, "Aguardando compra"),
        h(
          "p",
          { class: "suave" },
          "Solicitações aprovadas que ainda não tiveram a compra registrada."
        ),
        tabela(
          [
            {
              titulo: "Solicitação",
              valor: (l) => h("a", { href: `#/solicitacoes/${l.solicitacao.id}` }, `Nº ${l.solicitacao.id}`),
            },
            { titulo: "Aprovada em", classe: "numero", valor: (l) => formatar.data(l.solicitacao.data_decisao) },
            { titulo: "Fornecedor", valor: (l) => l.cotacao?.fornecedor || "—" },
            {
              titulo: "Valor aprovado",
              classe: "direita numero",
              valor: (l) => (l.cotacao ? formatar.moeda(l.cotacao.valor_total) : "—"),
            },
            {
              titulo: h("span", { class: "oculto-visualmente" }, "Ações"),
              classe: "acoes",
              valor: (l) =>
                h(
                  "button",
                  {
                    class: "pequeno primario",
                    onClick: () =>
                      abrirRegistroCompra({
                        solicitacaoId: l.solicitacao.id,
                        cotacao: l.cotacao,
                        aoConcluir: async () => {
                          await carregarAguardando();
                          await carregar();
                        },
                      }),
                  },
                  "Registrar compra"
                ),
            },
          ],
          linhas
        )
      )
    );
  }

  async function carregar() {
    const compras = await executar(() =>
      api.get(
        `/compras${montarQuery({
          fornecedor_id: filtros.fornecedor_id,
          pagina: filtros.pagina,
          tamanho: TAMANHO,
        })}`
      )
    );

    if (!compras) return;

    lista.replaceChildren(
      tabela(
        [
          { titulo: "Data", classe: "numero", valor: (c) => formatar.data(c.data_compra) },
          { titulo: "Pedido", valor: (c) => c.numero_pedido || h("span", { class: "suave" }, "—") },
          { titulo: "Fornecedor", valor: (c) => c.fornecedor },
          {
            titulo: "Solicitação",
            valor: (c) => h("a", { href: `#/solicitacoes/${c.solicitacao_id}` }, `Nº ${c.solicitacao_id}`),
          },
          { titulo: "Previsão de entrega", classe: "numero", valor: (c) => formatar.data(c.previsao_entrega) },
          { titulo: "Total", classe: "direita numero", valor: (c) => formatar.moeda(c.valor_total) },
        ],
        compras,
        {
          vazio: filtros.fornecedor_id
            ? "Nenhuma compra deste fornecedor."
            : "Nenhuma compra registrada. As compras aparecem aqui depois que uma solicitação aprovada é comprada.",
          acaoVazio: filtros.fornecedor_id
            ? null
            : h("a", { class: "botao", href: "#/solicitacoes" }, "Ver solicitações"),
        }
      ),
      paginacao(filtros.pagina, compras.length, TAMANHO, (pagina) => {
        filtros.pagina = pagina;
        carregar();
      })
    );
  }

  area.replaceChildren(
    cabecalho("Compras", "Pedidos feitos aos fornecedores a partir das solicitações aprovadas."),
    aguardando,
    h("h2", { style: { marginBottom: "12px" } }, "Compras registradas"),
    h(
      "div",
      { class: "filtros" },
      campoFiltro(
        "Fornecedor",
        seletor([["", "Todos"], ...fornecedores.map((f) => [f.id, f.nome])], "", {
          onChange: (evento) => {
            filtros.fornecedor_id = evento.target.value;
            filtros.pagina = 1;
            carregar();
          },
        })
      )
    ),
    lista
  );

  await Promise.all([carregarAguardando(), carregar()]);
}
