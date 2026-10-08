import { api, montarQuery } from "../api.js";
import { cabecalho, campoFiltro, executar, formatar, h, paginacao, seletor, tabela } from "../ui.js";

const TAMANHO = 20;

export async function telaCompras(area) {
  const fornecedores = await api.get("/fornecedores");
  const filtros = { fornecedor_id: "", pagina: 1 };
  const lista = h("div");

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

  await carregar();
}
