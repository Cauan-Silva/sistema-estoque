import { api, montarQuery } from "../api.js";
import { pode } from "../sessao.js";
import {
  botoesExportar,
  cabecalho,
  campoFiltro,
  etiquetaStatus,
  executar,
  formatar,
  h,
  nomeStatus,
  paginacao,
  seletor,
  tabela,
} from "../ui.js";
import { abrirRegistroCompra } from "./acoes_compra.js";

const TAMANHO = 20;

export async function telaCompras(area) {
  const fornecedores = await api.get("/fornecedores");
  const filtros = { fornecedor_id: "", situacao_recebimento: "", data_inicio: "", data_fim: "", pagina: 1 };
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
                !pode("compras.registrar") ? null : h(
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
          situacao_recebimento: filtros.situacao_recebimento,
          data_inicio: filtros.data_inicio,
          data_fim: filtros.data_fim,
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
          { titulo: "Entrega", valor: (c) => etiquetaStatus(c.situacao_recebimento) },
          { titulo: "Total", classe: "direita numero", valor: (c) => formatar.moeda(c.valor_total) },
          {
            titulo: h("span", { class: "oculto-visualmente" }, "Ações"),
            classe: "acoes",
            valor: (c) =>
              h(
                "a",
                { class: "botao pequeno", href: `#/solicitacoes/${c.solicitacao_id}` },
                c.situacao_recebimento !== "COMPLETO" && pode("recebimentos.registrar") ? "Receber" : "Ver"
              ),
          },
        ],
        compras,
        {
          vazio: filtros.fornecedor_id || filtros.situacao_recebimento || filtros.data_inicio || filtros.data_fim
            ? "Nenhuma compra com esses filtros."
            : "Nenhuma compra registrada. As compras aparecem aqui depois que uma solicitação aprovada é comprada.",
          acaoVazio: filtros.fornecedor_id || filtros.situacao_recebimento || filtros.data_inicio || filtros.data_fim
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

  function aoFiltrar(chave) {
    return (evento) => {
      filtros[chave] = evento.target.value;
      filtros.pagina = 1;
      carregar();
    };
  }

  area.replaceChildren(
    cabecalho(
      "Compras",
      "Pedidos feitos aos fornecedores a partir das solicitações aprovadas.",
      botoesExportar("/exportacoes/compras", () => ({
        fornecedor_id: filtros.fornecedor_id,
        situacao_recebimento: filtros.situacao_recebimento,
        data_inicio: filtros.data_inicio,
        data_fim: filtros.data_fim,
      }))
    ),
    aguardando,
    h("h2", { style: { marginBottom: "12px" } }, "Compras registradas"),
    h(
      "div",
      { class: "filtros" },
      campoFiltro(
        "Fornecedor",
        seletor([["", "Todos"], ...fornecedores.map((f) => [f.id, f.nome])], "", { onChange: aoFiltrar("fornecedor_id") })
      ),
      campoFiltro(
        "Entrega",
        seletor(
          [["", "Todas"], ...["PENDENTE", "PARCIAL", "COMPLETO"].map((s) => [s, nomeStatus(s)])],
          "",
          { onChange: aoFiltrar("situacao_recebimento") }
        )
      ),
      campoFiltro("Compradas de", h("input", { type: "date", onChange: aoFiltrar("data_inicio") })),
      campoFiltro("Até", h("input", { type: "date", onChange: aoFiltrar("data_fim") }))
    ),
    lista
  );

  await Promise.all([carregarAguardando(), carregar()]);
}
