import { api, listarTodos } from "../api.js";
import {
  abrirDialogo,
  abrirFormulario,
  confirmar,
  etiquetaStatus,
  executar,
  corStatus,
  formatar,
  h,
  tabela,
  vazio,
} from "../ui.js";
import { formularioSolicitacao } from "./solicitacoes.js";
import { abrirRegistroCompra } from "./acoes_compra.js";

const PODE_EDITAR = ["ABERTA"];
const PODE_COTAR = ["ABERTA", "EM_COTACAO"];
const PODE_CANCELAR = ["ABERTA", "EM_COTACAO", "APROVADA"];
const PODE_REPROVAR = ["ABERTA", "EM_COTACAO"];

function etapas(solicitacao, totalCotacoes) {
  const { status } = solicitacao;
  const interrompida = status === "CANCELADA" || status === "REPROVADA";
  const ordem = ["ABERTA", "EM_COTACAO", "APROVADA", "COMPRADA"];
  const posicao = ordem.indexOf(status);

  const passos = [
    { titulo: "Solicitação", detalhe: formatar.data(solicitacao.data_criacao), feita: true },
    {
      titulo: "Cotações",
      detalhe: totalCotacoes ? `${totalCotacoes} recebida${totalCotacoes > 1 ? "s" : ""}` : "Nenhuma ainda",
      feita: totalCotacoes > 0 || posicao >= 2,
      atual: status === "ABERTA",
    },
    {
      titulo: "Aprovação",
      detalhe: solicitacao.data_decisao ? formatar.data(solicitacao.data_decisao) : "Aguardando",
      feita: posicao >= 2,
      atual: status === "EM_COTACAO",
    },
    {
      titulo: "Compra",
      detalhe: status === "COMPRADA" ? "Registrada" : "Aguardando",
      feita: status === "COMPRADA",
      atual: status === "APROVADA",
    },
  ];

  const corInterrupcao = status === "REPROVADA" ? "var(--fibra-vermelho)" : "var(--fibra-ardosia)";

  return h(
    "ol",
    { class: `etapas ${interrompida ? "interrompida" : ""}`, "aria-label": "Andamento da compra" },
    passos.map((passo) =>
      h(
        "li",
        {
          class: passo.feita ? "feita" : passo.atual && !interrompida ? "atual" : "",
          style: interrompida && passo.feita ? { "--cor-etapa": corInterrupcao } : undefined,
        },
        passo.titulo,
        h("small", {}, passo.detalhe)
      )
    )
  );
}

function ficha(itens) {
  return h(
    "dl",
    { class: "ficha" },
    itens
      .filter(Boolean)
      .map(([rotulo, valor, larga]) =>
        h("div", { class: larga ? "larga" : "" }, h("dt", {}, rotulo), h("dd", {}, valor))
      )
  );
}

export async function telaSolicitacao(area, id) {
  const [solicitacao, cotacoes, comparacao, produtos, fornecedores] = await Promise.all([
    api.get(`/solicitacoes-compra/${id}`),
    api.get(`/solicitacoes-compra/${id}/cotacoes`),
    api.get(`/solicitacoes-compra/${id}/cotacoes/comparacao`),
    listarTodos("/produtos"),
    api.get("/fornecedores?ativo=true"),
  ]);

  const compra =
    solicitacao.status === "COMPRADA" ? await api.get(`/solicitacoes-compra/${id}/compra`) : null;

  const recarregar = () => telaSolicitacao(area, id);
  const status = solicitacao.status;

  /* ---------- Ações da solicitação ---------- */

  function editar() {
    formularioSolicitacao({ produtos, solicitacao, aoSalvar: recarregar });
  }

  async function cancelar() {
    const ok = await confirmar({
      titulo: "Cancelar solicitação",
      mensagem: "A solicitação será encerrada e não poderá mais ser alterada.",
      textoAcao: "Cancelar solicitação",
      perigo: true,
    });

    if (ok) {
      await executar(() => api.patch(`/solicitacoes-compra/${id}/cancelar`), "Solicitação cancelada.");
      recarregar();
    }
  }

  function reprovar() {
    abrirFormulario({
      titulo: "Reprovar solicitação",
      descricao: "A solicitação será encerrada. Explique o motivo para quem pediu a compra.",
      campos: [{ nome: "justificativa", rotulo: "Motivo", tipo: "textarea", obrigatorio: true, minimo: 3, maximo: 500 }],
      textoAcao: "Reprovar solicitação",
      classeAcao: "perigo cheio",
      aoEnviar: async (dados) => {
        await api.patch(`/solicitacoes-compra/${id}/reprovar`, dados);
        recarregar();
      },
    });
  }

  function aprovar(cotacao) {
    abrirFormulario({
      titulo: "Aprovar cotação",
      descricao: `${cotacao.fornecedor}: ${formatar.moeda(cotacao.valor_total)}, entrega em ${formatar.dias(cotacao.prazo_entrega_dias)}.`,
      campos: [
        { nome: "justificativa", rotulo: "Justificativa (opcional)", tipo: "textarea", maximo: 500 },
      ],
      textoAcao: "Aprovar cotação",
      classeAcao: "sucesso",
      aoEnviar: async (dados) => {
        await api.patch(`/solicitacoes-compra/${id}/aprovar`, {
          cotacao_id: cotacao.cotacao_id,
          justificativa: dados.justificativa,
        });
        recarregar();
      },
    });
  }

  /* ---------- Cotações ---------- */

  function formularioCotacao(cotacao) {
    const jaCotaram = new Set(cotacoes.map((c) => c.fornecedor_id));
    const disponiveis = fornecedores.filter((f) => !jaCotaram.has(f.id));

    if (!cotacao && !disponiveis.length) {
      confirmar({
        titulo: "Nenhum fornecedor disponível",
        mensagem: fornecedores.length
          ? "Todos os fornecedores ativos já enviaram cotação para esta solicitação."
          : "Cadastre um fornecedor ativo para registrar cotações.",
        textoAcao: "Entendi",
      });
      return;
    }

    const precos = new Map((cotacao?.itens || []).map((item) => [item.produto_id, item.preco_unitario]));

    const fornecedor = cotacao
      ? h("p", {}, h("strong", {}, cotacao.fornecedor))
      : h(
          "label",
          {},
          "Fornecedor",
          h(
            "select",
            { name: "fornecedor_id", required: true },
            h("option", { value: "" }, "Escolha um fornecedor"),
            disponiveis.map((f) => h("option", { value: f.id }, f.nome))
          )
        );

    const camposPreco = solicitacao.itens.map((item) =>
      h(
        "label",
        {},
        `${item.produto} (${formatar.numero(item.quantidade)} un.)`,
        h("input", {
          type: "number",
          min: 0,
          step: "0.01",
          name: `preco_${item.produto_id}`,
          placeholder: "Preço unitário em R$, vazio se não cotou",
          value: precos.get(item.produto_id) ?? "",
        })
      )
    );

    const valorCampo = (nome, valor) =>
      h("input", { name: nome, type: "number", min: 0, step: nome === "frete" ? "0.01" : 1, required: nome !== "frete", value: valor ?? "" });

    abrirDialogo({
      titulo: cotacao ? "Editar cotação" : "Registrar cotação",
      conteudo: [
        fornecedor,
        h("h3", {}, "Preços"),
        camposPreco,
        h(
          "div",
          { class: "linha-campos" },
          h("label", {}, "Frete (R$)", valorCampo("frete", cotacao?.frete ?? 0)),
          h("label", {}, "Prazo de entrega (dias)", valorCampo("prazo_entrega_dias", cotacao?.prazo_entrega_dias))
        ),
        h("label", {}, "Válida até", h("input", { type: "date", name: "validade", value: cotacao?.validade ?? "" })),
        h("label", {}, "Observação", h("textarea", { name: "observacao", maxlength: "500" }, cotacao?.observacao ?? "")),
      ],
      textoAcao: cotacao ? "Salvar cotação" : "Registrar cotação",
      aoEnviar: async (formulario) => {
        const campos = formulario.elements;

        const itens = solicitacao.itens
          .map((item) => ({
            produto_id: item.produto_id,
            valor: campos[`preco_${item.produto_id}`].value.trim(),
          }))
          .filter((item) => item.valor !== "")
          .map((item) => ({ produto_id: item.produto_id, preco_unitario: Number(item.valor) }));

        if (!itens.length) {
          throw new Error("Informe o preço de pelo menos um produto.");
        }

        const corpo = {
          frete: Number(campos.frete.value || 0),
          prazo_entrega_dias: Number(campos.prazo_entrega_dias.value),
          validade: campos.validade.value || null,
          observacao: campos.observacao.value.trim() || null,
          itens,
        };

        if (cotacao) {
          await api.put(`/solicitacoes-compra/${id}/cotacoes/${cotacao.id}`, corpo);
        } else {
          await api.post(`/solicitacoes-compra/${id}/cotacoes`, {
            ...corpo,
            fornecedor_id: Number(campos.fornecedor_id.value),
          });
        }

        recarregar();
      },
    });
  }

  async function excluirCotacao(cotacao) {
    const ok = await confirmar({
      titulo: "Excluir cotação",
      mensagem: `A cotação de ${cotacao.fornecedor} será excluída.`,
      textoAcao: "Excluir cotação",
      perigo: true,
    });

    if (ok) {
      await executar(
        () => api.delete(`/solicitacoes-compra/${id}/cotacoes/${cotacao.id}`),
        "Cotação excluída."
      );
      recarregar();
    }
  }

  function cartaoCotacao(cotacao) {
    const aprovada = solicitacao.cotacao_aprovada_id === cotacao.id;
    const podeAlterar = PODE_COTAR.includes(status);

    return h(
      "article",
      { class: `cotacao ${aprovada ? "aprovada" : ""}` },
      h(
        "header",
        {},
        h(
          "div",
          {},
          h("h3", {}, cotacao.fornecedor, aprovada ? " " : "", aprovada ? etiquetaStatus("APROVADA") : null),
          h(
            "p",
            {},
            `Entrega em ${formatar.dias(cotacao.prazo_entrega_dias)}`,
            cotacao.validade ? `, válida até ${formatar.data(cotacao.validade)}` : "",
            cotacao.observacao ? `. ${cotacao.observacao}` : ""
          )
        ),
        podeAlterar
          ? h(
              "div",
              {},
              h("button", { class: "pequeno", onClick: () => formularioCotacao(cotacao) }, "Editar"),
              " ",
              h("button", { class: "pequeno perigo", onClick: () => excluirCotacao(cotacao) }, "Excluir")
            )
          : null
      ),
      tabela(
        [
          { titulo: "Produto", valor: (i) => i.produto },
          { titulo: "Quantidade", classe: "direita numero", valor: (i) => formatar.numero(i.quantidade) },
          { titulo: "Preço unitário", classe: "direita numero", valor: (i) => formatar.moeda(i.preco_unitario) },
          { titulo: "Subtotal", classe: "direita numero", valor: (i) => formatar.moeda(i.subtotal) },
        ],
        cotacao.itens,
        {
          rodape: [
            h("tr", {}, h("td", { colspan: 3 }, "Frete"), h("td", { class: "direita numero" }, formatar.moeda(cotacao.frete))),
            h("tr", {}, h("td", { colspan: 3 }, "Total"), h("td", { class: "direita numero" }, formatar.moeda(cotacao.valor_total))),
          ],
        }
      )
    );
  }

  /* ---------- Comparação ---------- */

  function blocoComparacao() {
    if (!comparacao.total_cotacoes) return null;

    const destaque = (rotulo, item, valor, cor) =>
      h(
        "div",
        { class: "destaque", style: { "--cor": cor } },
        h("span", {}, rotulo),
        item ? [h("strong", {}, item.fornecedor), h("div", { class: "numero" }, valor(item))] : h("strong", {}, "Sem cotação elegível")
      );

    const podeAprovar = status === "EM_COTACAO";

    const situacao = (c) => {
      if (c.vencida) return h("span", { class: "etiqueta" }, "Vencida");
      if (!c.cobre_todos_itens) return h("span", { class: "etiqueta" }, `Cobre ${c.itens_cotados} de ${solicitacao.itens.length} itens`);
      return h("span", { class: "etiqueta" }, "Completa");
    };

    return h(
      "section",
      { class: "secao", id: "comparacao" },
      h("h2", {}, "Comparação"),
      h(
        "p",
        { class: "suave" },
        "Só entram nos destaques e na aprovação as cotações que cobrem todos os itens e estão dentro da validade."
      ),
      h(
        "div",
        { class: "destaques" },
        destaque("Menor valor total", comparacao.menor_valor_total, (c) => formatar.moeda(c.valor_total), "var(--fibra-verde)"),
        destaque("Menor prazo", comparacao.menor_prazo, (c) => formatar.dias(c.prazo_entrega_dias), "var(--fibra-azul)"),
        destaque("Menor frete", comparacao.menor_frete, (c) => formatar.moeda(c.frete), "var(--fibra-laranja)")
      ),
      tabela(
        [
          { titulo: "Fornecedor", valor: (c) => c.fornecedor },
          { titulo: "Situação", valor: situacao },
          { titulo: "Itens", classe: "direita numero", valor: (c) => formatar.moeda(c.valor_itens) },
          { titulo: "Frete", classe: "direita numero", valor: (c) => formatar.moeda(c.frete) },
          { titulo: "Total", classe: "direita numero", valor: (c) => h("strong", {}, formatar.moeda(c.valor_total)) },
          { titulo: "Prazo", classe: "direita numero", valor: (c) => formatar.dias(c.prazo_entrega_dias) },
          podeAprovar
            ? {
                titulo: h("span", { class: "oculto-visualmente" }, "Ações"),
                classe: "acoes",
                valor: (c) =>
                  h("button", { class: "pequeno sucesso", disabled: !c.elegivel, onClick: () => aprovar(c) }, "Aprovar"),
              }
            : null,
        ].filter(Boolean),
        comparacao.cotacoes,
        { classeLinha: (c) => (c.elegivel ? "" : "inelegivel") }
      ),
      h("h3", { style: { margin: "20px 0 10px" } }, "Melhor preço por produto"),
      tabela(
        [
          { titulo: "Produto", valor: (p) => p.produto },
          { titulo: "Quantidade", classe: "direita numero", valor: (p) => formatar.numero(p.quantidade) },
          { titulo: "Melhor preço", classe: "direita numero", valor: (p) => formatar.moeda(p.melhor_preco_unitario) },
          { titulo: "Fornecedor", valor: (p) => p.fornecedor || "—" },
          { titulo: "Ofertas", classe: "direita numero", valor: (p) => p.quantidade_ofertas },
        ],
        comparacao.por_produto
      )
    );
  }

  /* ---------- Compra ---------- */

  function registrarCompra() {
    abrirRegistroCompra({
      solicitacaoId: id,
      cotacao: cotacoes.find((c) => c.id === solicitacao.cotacao_aprovada_id),
      aoConcluir: recarregar,
    });
  }

  function proximoPasso() {
    const passos = {
      ABERTA: [
        "Registre as cotações dos fornecedores para esta solicitação.",
        h("button", { class: "primario", onClick: () => formularioCotacao() }, "Registrar cotação"),
      ],
      EM_COTACAO: [
        "Compare as cotações abaixo e aprove a melhor. Só cotações completas e dentro da validade podem ser aprovadas.",
        h(
          "button",
          {
            class: "primario",
            onClick: () => document.getElementById("comparacao")?.scrollIntoView({ behavior: "smooth" }),
          },
          "Ver comparação"
        ),
      ],
      APROVADA: [
        "A cotação foi aprovada. Registre a compra quando o pedido for feito ao fornecedor.",
        h("button", { class: "primario", onClick: registrarCompra }, "Registrar compra"),
      ],
    };

    const passo = passos[status];
    if (!passo) return null;

    return h(
      "aside",
      { class: "proximo-passo", dataset: { cor: corStatus(status) } },
      h("div", {}, h("strong", {}, "Próximo passo"), h("p", {}, passo[0])),
      passo[1]
    );
  }

  function blocoCompra() {
    if (status === "APROVADA") {
      return h(
        "section",
        { class: "secao" },
        h("h2", {}, "Compra"),
        h(
          "div",
          { class: "quadro" },
          vazio(
            "A cotação foi aprovada. Registre a compra quando o pedido for feito ao fornecedor.",
            h("button", { class: "primario", onClick: registrarCompra }, "Registrar compra")
          )
        )
      );
    }

    if (!compra) return null;

    return h(
      "section",
      { class: "secao" },
      h("h2", {}, "Compra"),
      ficha([
        ["Fornecedor", compra.fornecedor],
        ["Número do pedido", compra.numero_pedido || "—"],
        ["Data da compra", formatar.data(compra.data_compra)],
        ["Previsão de entrega", formatar.data(compra.previsao_entrega)],
        ["Comprador", compra.comprador],
        ["Valor total", h("span", { class: "numero" }, formatar.moeda(compra.valor_total))],
        compra.observacao ? ["Observação", compra.observacao, true] : null,
      ])
    );
  }

  /* ---------- Montagem ---------- */

  const acoes = [
    PODE_EDITAR.includes(status) ? h("button", { onClick: editar }, "Editar itens") : null,
    PODE_REPROVAR.includes(status) ? h("button", { class: "perigo", onClick: reprovar }, "Reprovar") : null,
    PODE_CANCELAR.includes(status) ? h("button", { class: "perigo", onClick: cancelar }, "Cancelar") : null,
  ].filter(Boolean);

  const decisao =
    solicitacao.decisao_por && ["APROVADA", "COMPRADA", "REPROVADA"].includes(status)
      ? [
          [status === "REPROVADA" ? "Reprovada por" : "Aprovada por", solicitacao.decisao_por],
          ["Data da decisão", formatar.dataHora(solicitacao.data_decisao)],
          solicitacao.justificativa_decisao ? ["Justificativa", solicitacao.justificativa_decisao, true] : null,
        ]
      : [];

  area.replaceChildren(
    h("a", { class: "voltar", href: "#/solicitacoes" }, "Voltar para solicitações"),
    h(
      "header",
      { class: "cabecalho" },
      h(
        "div",
        {},
        h("h1", {}, `Solicitação Nº ${solicitacao.id}`),
        h("p", {}, etiquetaStatus(status))
      ),
      acoes.length ? h("div", { style: { display: "flex", gap: "8px", flexWrap: "wrap" } }, acoes) : null
    ),
    etapas(solicitacao, cotacoes.length),
    proximoPasso(),
    ficha([
      ["Solicitante", solicitacao.solicitante],
      ["Criada em", formatar.dataHora(solicitacao.data_criacao)],
      ["Última atualização", formatar.dataHora(solicitacao.data_atualizacao)],
      solicitacao.observacao ? ["Observação", solicitacao.observacao, true] : null,
      ...decisao,
    ]),
    h(
      "section",
      { class: "secao" },
      h("h2", {}, "Itens"),
      tabela(
        [
          { titulo: "Produto", valor: (i) => i.produto },
          { titulo: "Quantidade", classe: "direita numero", valor: (i) => formatar.numero(i.quantidade) },
        ],
        solicitacao.itens
      )
    ),
    blocoCompra(),
    blocoComparacao(),
    cotacoes.length || PODE_COTAR.includes(status)
      ? h(
          "section",
          { class: "secao" },
          h(
            "div",
            { class: "titulo-secao" },
            h("h2", {}, "Cotações"),
            PODE_COTAR.includes(status)
              ? h("button", { class: "primario", onClick: () => formularioCotacao() }, "Registrar cotação")
              : null
          ),
          cotacoes.length
            ? cotacoes.map(cartaoCotacao)
            : h(
                "div",
                { class: "quadro" },
                vazio("Peça preços aos fornecedores e registre cada cotação aqui para comparar.")
              )
        )
      : null
  );
}
