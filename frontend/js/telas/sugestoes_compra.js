import { api, montarQuery } from "../api.js";
import { pode } from "../sessao.js";
import { avisar, cabecalho, campoFiltro, formatar, h, seletor } from "../ui.js";

/*
 * Sugestão de compra: o que repor, calculado pelo estoque mínimo, pelo
 * consumo médio, pelo prazo de entrega e pelo que já está em pedido.
 */

const PERIODOS = [[30, "30 dias"], [60, "60 dias"], [90, "90 dias"], [180, "6 meses"], [365, "12 meses"]];
const COBERTURAS = [[0, "Só o mínimo"], [15, "15 dias"], [30, "30 dias"], [45, "45 dias"], [60, "60 dias"], [90, "90 dias"]];

export async function telaSugestoesCompra(area) {
  const filtros = { dias_consumo: 90, cobertura_dias: 30, todos: false };
  const podeCriar = pode("solicitacoes.editar");
  let linhas = [];

  const resumo = h("div", { class: "resumo-sugestao" });
  const lista = h("div");
  const botaoCriar = h("button", { class: "primario", onClick: criar }, "Criar solicitação");

  function selecionadas() {
    return linhas.filter((linha) => linha.marcado && linha.quantidade > 0);
  }

  function atualizarResumo() {
    const escolhidas = selecionadas();
    const total = escolhidas.reduce((soma, linha) => soma + linha.quantidade * linha.preco_referencia, 0);
    const precisam = linhas.filter((linha) => linha.sugerido > 0).length;

    botaoCriar.disabled = !escolhidas.length;
    botaoCriar.textContent = escolhidas.length
      ? `Criar solicitação com ${escolhidas.length} ${escolhidas.length === 1 ? "item" : "itens"}`
      : "Criar solicitação";

    resumo.replaceChildren(
      h("div", {}, h("span", { class: "suave" }, "Produtos para repor"), h("strong", {}, formatar.numero(precisam))),
      h("div", {}, h("span", { class: "suave" }, "Selecionados"), h("strong", {}, formatar.numero(escolhidas.length))),
      h(
        "div",
        {},
        h("span", { class: "suave" }, "Valor estimado"),
        h("strong", {}, formatar.moeda(total)),
        h("span", { class: "dica-campo" }, "pelo último preço pago ou o do cadastro")
      )
    );
  }

  function linhaTabela(linha) {
    const abaixo = linha.estoque <= linha.estoque_minimo;

    return h(
      "tr",
      { class: linha.sugerido > 0 ? "" : "sem-necessidade" },
      podeCriar
        ? h(
            "td",
            {},
            h("input", {
              type: "checkbox",
              checked: linha.marcado,
              "aria-label": `Incluir ${linha.produto}`,
              onChange: (evento) => {
                linha.marcado = evento.target.checked;
                atualizarResumo();
              },
            })
          )
        : null,
      h(
        "td",
        {},
        h("strong", { class: "nome-sugestao" }, linha.produto),
        h("span", { class: "detalhe-sugestao" }, linha.categoria || ""),
        linha.motivo ? h("span", { class: "motivo-sugestao", dataset: { urgente: String(abaixo) } }, linha.motivo) : null
      ),
      h(
        "td",
        { class: "direita numero" },
        h("span", { class: abaixo ? "abaixo-minimo" : "" }, formatar.numero(linha.estoque)),
        h("span", { class: "detalhe-sugestao" }, `mín. ${formatar.numero(linha.estoque_minimo)}`)
      ),
      h("td", { class: "direita numero" }, linha.em_pedido ? formatar.numero(linha.em_pedido) : "—"),
      h(
        "td",
        { class: "direita numero" },
        formatar.numero(linha.consumo_mensal),
        h("span", { class: "detalhe-sugestao" }, "por mês")
      ),
      h(
        "td",
        { class: "direita numero" },
        linha.dias_restantes === null ? "—" : `${formatar.numero(linha.dias_restantes)} dias`
      ),
      h(
        "td",
        { class: "direita numero" },
        `${linha.prazo_entrega_dias} dias`,
        linha.prazo_estimado ? h("span", { class: "detalhe-sugestao" }, "estimado") : null
      ),
      h(
        "td",
        { class: "direita" },
        podeCriar
          ? h("input", {
              type: "number",
              min: 0,
              step: 1,
              class: "entrada-quantidade",
              "aria-label": `Quantidade de ${linha.produto}`,
              value: linha.quantidade,
              onInput: (evento) => {
                linha.quantidade = Math.max(0, Math.floor(Number(evento.target.value) || 0));
                if (linha.quantidade > 0 && !linha.marcado) {
                  linha.marcado = true;
                  evento.target.closest("tr").querySelector("input[type=checkbox]").checked = true;
                }
                atualizarResumo();
              },
            })
          : formatar.numero(linha.sugerido)
      ),
      h(
        "td",
        {},
        linha.ultimo_fornecedor || h("span", { class: "suave" }, "—"),
        h("span", { class: "detalhe-sugestao" }, `${formatar.moeda(linha.preco_referencia)} un.`)
      )
    );
  }

  function desenhar() {
    if (!linhas.length) {
      lista.replaceChildren(
        h(
          "div",
          { class: "quadro vazio" },
          h("p", {}, filtros.todos ? "Nenhum produto cadastrado." : "Nenhum produto precisa de reposição agora."),
          h("p", { class: "suave" }, "Os pedidos abertos e as compras a receber já cobrem o estoque mínimo e o consumo.")
        )
      );
      atualizarResumo();
      return;
    }

    lista.replaceChildren(
      h(
        "div",
        { class: "quadro" },
        h(
          "table",
          { class: "tabela-sugestao" },
          h(
            "thead",
            {},
            h(
              "tr",
              {},
              podeCriar ? h("th", {}, h("span", { class: "oculto-visualmente" }, "Incluir")) : null,
              h("th", {}, "Produto"),
              h("th", { class: "direita" }, "Estoque"),
              h("th", { class: "direita" }, "Em pedido"),
              h("th", { class: "direita" }, "Consumo"),
              h("th", { class: "direita" }, "Dura"),
              h("th", { class: "direita" }, "Prazo de entrega"),
              h("th", { class: "direita" }, "Comprar"),
              h("th", {}, "Último fornecedor")
            )
          ),
          h("tbody", {}, linhas.map(linhaTabela))
        )
      )
    );
    atualizarResumo();
  }

  async function carregar() {
    lista.replaceChildren(h("p", { class: "suave" }, "Calculando…"));
    try {
      const dados = await api.get(`/sugestoes-compra${montarQuery(filtros)}`);
      linhas = dados.map((item) => ({ ...item, marcado: item.sugerido > 0, quantidade: item.sugerido }));
      desenhar();
    } catch (falha) {
      lista.replaceChildren(h("p", { class: "erro" }, falha.message));
    }
  }

  async function criar() {
    const escolhidas = selecionadas();
    if (!escolhidas.length) return;

    botaoCriar.disabled = true;
    try {
      const solicitacao = await api.post("/solicitacoes-compra", {
        observacao: `Gerada pela sugestão de compra (consumo de ${filtros.dias_consumo} dias, cobertura de ${filtros.cobertura_dias} dias).`,
        itens: escolhidas.map((linha) => ({ produto_id: linha.produto_id, quantidade: linha.quantidade })),
      });
      avisar(`Solicitação Nº ${solicitacao.id} criada com ${escolhidas.length} item(ns).`);
      window.location.hash = `#/solicitacoes/${solicitacao.id}`;
    } catch (falha) {
      avisar(falha.message, "erro");
      botaoCriar.disabled = false;
    }
  }

  const aoMudar = (chave, conversor = Number) => (evento) => {
    filtros[chave] = conversor(evento.target.type === "checkbox" ? evento.target.checked : evento.target.value);
    carregar();
  };

  area.replaceChildren(
    cabecalho(
      "Sugestão de compra",
      "O que repor, pelo estoque mínimo, pelo consumo médio e pelo prazo de entrega. Pedidos abertos e compras a receber já são descontados.",
      podeCriar ? botaoCriar : null
    ),
    h(
      "div",
      { class: "filtros filtros-soltos" },
      campoFiltro("Consumo médio dos últimos", seletor(PERIODOS, filtros.dias_consumo, { onChange: aoMudar("dias_consumo") })),
      campoFiltro("Cobrir depois da entrega", seletor(COBERTURAS, filtros.cobertura_dias, { onChange: aoMudar("cobertura_dias") })),
      h(
        "label",
        { class: "marcador" },
        h("input", { type: "checkbox", onChange: aoMudar("todos", Boolean) }),
        "Mostrar todos os produtos"
      )
    ),
    resumo,
    lista,
    h(
      "details",
      { class: "explicacao-sugestao" },
      h("summary", {}, "Como a sugestão é calculada"),
      h(
        "ul",
        {},
        h("li", {}, "Consumo médio: saídas do período escolhido divididas pelo número de dias."),
        h("li", {}, "Prazo de entrega: média das cotações aprovadas do produto; sem histórico, usa 7 dias (estimado)."),
        h("li", {}, "Em pedido: solicitações abertas, em cotação ou aprovadas, mais o que foi comprado e ainda não chegou."),
        h("li", {}, "Repor quando: estoque + em pedido ≤ mínimo + consumo durante o prazo de entrega."),
        h("li", {}, "Quanto comprar: o suficiente para ter o mínimo mais o consumo do prazo e da cobertura escolhida, e pelo menos um lote do tamanho do mínimo.")
      )
    )
  );

  await carregar();
}
