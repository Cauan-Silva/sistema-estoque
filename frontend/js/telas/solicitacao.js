import { api, baixarArquivo, listarTodos } from "../api.js";
import { icone } from "../icones.js";
import {
  abrirDialogo,
  avisar,
  botoesExportar,
  cabecalho,
  abrirFormulario,
  confirmar,
  etiquetaStatus,
  executar,
  corStatus,
  formatar,
  h,
  hojeISO,
  seletor,
  tabela,
  vazio,
} from "../ui.js";
import { formularioSolicitacao } from "./solicitacoes.js";
import { abrirRegistroCompra } from "./acoes_compra.js";
import { campoFormaPagamento } from "./formas_pagamento.js";
import { pode, usuario } from "../sessao.js";
import { referenciaPreco } from "./precos.js";

const PODE_EDITAR = ["ABERTA"];
const PODE_COTAR = ["ABERTA", "EM_COTACAO"];
const PODE_CANCELAR = ["ABERTA", "EM_COTACAO", "APROVADA"];
const PODE_REPROVAR = ["ABERTA", "EM_COTACAO"];

function etapas(solicitacao, totalCotacoes, compra) {
  const { status } = solicitacao;
  const interrompida = status === "CANCELADA" || status === "REPROVADA";
  const ordem = ["ABERTA", "EM_COTACAO", "APROVADA", "COMPRADA", "RECEBIDA"];
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
      detalhe: compra ? formatar.data(compra.data_compra) : "Aguardando",
      feita: posicao >= 3,
      atual: status === "APROVADA",
    },
    {
      titulo: "Recebimento",
      detalhe: !compra
        ? "Aguardando"
        : compra.situacao_recebimento === "COMPLETO"
          ? formatar.data(compra.ultimo_recebimento)
          : compra.situacao_recebimento === "PARCIAL"
            ? "Parcial"
            : `Previsto para ${formatar.data(compra.previsao_entrega)}`,
      feita: status === "RECEBIDA",
      atual: status === "COMPRADA",
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
  const [solicitacao, cotacoes, comparacao, produtos, fornecedores, anexos] = await Promise.all([
    api.get(`/solicitacoes-compra/${id}`),
    api.get(`/solicitacoes-compra/${id}/cotacoes`),
    api.get(`/solicitacoes-compra/${id}/cotacoes/comparacao`),
    listarTodos("/produtos"),
    api.get("/fornecedores?ativo=true"),
    api.get(`/solicitacoes-compra/${id}/anexos`),
  ]);

  const temCompra = ["COMPRADA", "RECEBIDA"].includes(solicitacao.status);

  const [compra, recebimentos] = temCompra
    ? await Promise.all([
        api.get(`/solicitacoes-compra/${id}/compra`),
        api.get(`/solicitacoes-compra/${id}/compra/recebimentos`),
      ])
    : [null, []];

  const recarregar = () => telaSolicitacao(area, id);
  const status = solicitacao.status;

  const propria = solicitacao.solicitante_id === usuario()?.id && usuario()?.perfil !== "ADMINISTRADOR";
  const permite = {
    editar: pode("solicitacoes.editar"),
    cotar: pode("cotacoes.editar"),
    decidir: pode("compras.aprovar") && !propria,
    comprar: pode("compras.registrar"),
    receber: pode("recebimentos.registrar"),
  };

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

    const camposPreco = solicitacao.itens.map((item) => {
      const referencia = h("small", { class: "referencia-preco" });
      referenciaPreco(item.produto_id).then((texto) => {
        referencia.textContent = texto;
      });

      return h(
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
        }),
        referencia
      );
    });

    const formaPagamento = campoFormaPagamento(
      cotacao?.forma_pagamento_id
        ? { id: cotacao.forma_pagamento_id, descricao: cotacao.forma_pagamento }
        : null
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
        formaPagamento.elemento,
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
          forma_pagamento_id: formaPagamento.valor(),
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

  /* ---------- Anexos ---------- */

  const TIPOS_ANEXO = [
    ["NOTA_FISCAL", "Nota fiscal"],
    ["PROPOSTA", "Proposta / orçamento"],
    ["PEDIDO", "Pedido de compra"],
    ["BOLETO", "Boleto"],
    ["OUTRO", "Outro"],
  ];
  const nomeTipoAnexo = (tipo) => (TIPOS_ANEXO.find(([valor]) => valor === tipo) || [tipo, tipo])[1];
  const podeAnexar = permite.editar || permite.cotar || permite.comprar || permite.receber;

  function tamanhoArquivo(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
  }

  function anexarArquivo() {
    const tipoSugerido = ["COMPRADA", "RECEBIDA"].includes(status) ? "NOTA_FISCAL" : "PROPOSTA";
    const arquivo = h("input", {
      type: "file",
      name: "arquivo",
      required: true,
      accept: ".pdf,.png,.jpg,.jpeg,.webp,.gif,.xml,.xlsx,.xls,.csv,.docx,.doc,.txt",
    });

    abrirDialogo({
      titulo: "Anexar arquivo",
      descricao: "PDF, imagem, XML, planilha, documento ou texto, até 10 MB.",
      conteudo: [
        h("label", {}, "Arquivo", arquivo),
        h("div", { class: "linha-campos" },
          h("label", {}, "Tipo", seletor(TIPOS_ANEXO, tipoSugerido, { name: "tipo" })),
          h("label", {}, "Fornecedor", seletor(
            [["", "Nenhum"], ...fornecedores.map((f) => [f.id, f.nome])],
            compra?.fornecedor_id ?? "",
            { name: "fornecedor_id" }
          ))
        ),
        h("label", {}, "Descrição", h("input", { name: "descricao", maxlength: 200, placeholder: "Ex.: NF 1234, primeira entrega" })),
      ],
      textoAcao: "Anexar",
      aoEnviar: async (formulario) => {
        const [escolhido] = arquivo.files;
        if (!escolhido) throw new Error("Escolha um arquivo.");
        await api.enviarArquivo(`/solicitacoes-compra/${id}/anexos`, escolhido, {
          tipo: formulario.elements.tipo.value,
          fornecedor_id: formulario.elements.fornecedor_id.value,
          descricao: formulario.elements.descricao.value.trim(),
        });
        avisar(`${escolhido.name} anexado.`);
        recarregar();
      },
    });
  }

  async function excluirAnexo(anexo) {
    const ok = await confirmar({
      titulo: "Excluir anexo",
      mensagem: `O arquivo ${anexo.nome_arquivo} será excluído.`,
      textoAcao: "Excluir anexo",
      perigo: true,
    });
    if (ok) {
      await executar(() => api.delete(`/solicitacoes-compra/${id}/anexos/${anexo.id}`), "Anexo excluído.");
      recarregar();
    }
  }

  function blocoAnexos() {
    const eu = usuario();
    return h(
      "section",
      { class: "secao" },
      h(
        "div",
        { class: "titulo-secao" },
        h("h2", {}, "Anexos"),
        podeAnexar ? h("button", { class: "primario", onClick: anexarArquivo }, icone("clipe"), "Anexar arquivo") : null
      ),
      tabela(
        [
          { titulo: "Tipo", valor: (a) => h("span", { class: "chip-anexo", dataset: { tipo: a.tipo } }, nomeTipoAnexo(a.tipo)) },
          {
            titulo: "Arquivo",
            valor: (a) =>
              h(
                "button",
                {
                  type: "button",
                  class: "link nome-anexo",
                  title: "Baixar",
                  onClick: (evento) => baixar(`/solicitacoes-compra/${id}/anexos/${a.id}`, evento),
                },
                a.nome_arquivo
              ),
          },
          { titulo: "Descrição", valor: (a) => a.descricao || h("span", { class: "suave" }, "—") },
          { titulo: "Fornecedor", valor: (a) => a.fornecedor || h("span", { class: "suave" }, "—") },
          { titulo: "Enviado", valor: (a) => `${formatar.dataHora(a.data_envio)}${a.usuario ? ` por ${a.usuario}` : ""}` },
          { titulo: "Tamanho", classe: "direita numero", valor: (a) => tamanhoArquivo(a.tamanho) },
          {
            titulo: h("span", { class: "oculto-visualmente" }, "Ações"),
            classe: "acoes",
            valor: (a) =>
              a.usuario_id === eu?.id || eu?.perfil === "ADMINISTRADOR"
                ? h("button", { class: "pequeno perigo", onClick: () => excluirAnexo(a) }, "Excluir")
                : null,
          },
        ],
        anexos,
        { vazio: "Nenhum arquivo anexado. Guarde aqui propostas, notas fiscais e boletos desta compra." }
      )
    );
  }

  /* ---------- Planilha de orçamento ---------- */

  async function baixar(caminho, evento) {
    const botao = evento?.currentTarget;
    if (botao) botao.disabled = true;
    try {
      const nome = await baixarArquivo(caminho);
      avisar(`Arquivo ${nome} baixado.`);
    } catch (falha) {
      avisar(falha.message, "erro");
    } finally {
      if (botao) botao.disabled = false;
    }
  }

  async function enviarPlanilha(arquivo, substituir = false) {
    const caminho = `/solicitacoes-compra/${id}/cotacoes/importar${substituir ? "?substituir=true" : ""}`;

    try {
      const cotacao = await api.enviarArquivo(caminho, arquivo);
      avisar(`Cotação de ${cotacao.fornecedor} ${substituir ? "atualizada" : "importada"}: ${formatar.moeda(cotacao.valor_total)}.`);
      recarregar();
    } catch (falha) {
      if (falha.status === 409 && !substituir && /já possui cotação/.test(falha.message)) {
        const ok = await confirmar({
          titulo: "Substituir cotação?",
          mensagem: `${falha.message} Deseja substituir os valores dela pelos da planilha?`,
          textoAcao: "Substituir cotação",
        });
        if (ok) await enviarPlanilha(arquivo, true);
        return;
      }
      avisar(falha.message, "erro");
    }
  }

  function importarPlanilha() {
    const escolha = h("input", {
      type: "file",
      accept: ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      hidden: true,
      onChange: () => {
        const [arquivo] = escolha.files;
        escolha.remove();
        if (arquivo) enviarPlanilha(arquivo);
      },
    });
    document.body.append(escolha);
    escolha.click();
  }

  function cartaoCotacao(cotacao) {
    const aprovada = solicitacao.cotacao_aprovada_id === cotacao.id;
    const podeAlterar = PODE_COTAR.includes(status) && permite.cotar;

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
            cotacao.forma_pagamento ? `, pagamento ${cotacao.forma_pagamento}` : "",
            cotacao.validade ? `, válida até ${formatar.data(cotacao.validade)}` : "",
            cotacao.observacao ? `. ${cotacao.observacao}` : ""
          )
        ),
        h(
          "div",
          { class: "acoes-cotacao" },
          h(
            "button",
            {
              class: "pequeno",
              title: "Baixar esta cotação no formato da planilha de orçamento",
              onClick: (evento) => baixar(`/solicitacoes-compra/${id}/cotacoes/${cotacao.id}/planilha`, evento),
            },
            "Planilha"
          ),
          podeAlterar ? h("button", { class: "pequeno", onClick: () => formularioCotacao(cotacao) }, "Editar") : null,
          podeAlterar ? h("button", { class: "pequeno perigo", onClick: () => excluirCotacao(cotacao) }, "Excluir") : null
        )
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

    const podeAprovar = status === "EM_COTACAO" && permite.decidir;

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
          { titulo: "Pagamento", valor: (c) => c.forma_pagamento || h("span", { class: "suave" }, "—") },
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
        permite.cotar
          ? h("button", { class: "primario", onClick: () => formularioCotacao() }, "Registrar cotação")
          : "Feito por: Comprador ou Administrador",
      ],
      EM_COTACAO: [
        propria && pode("compras.aprovar")
          ? "Compare as cotações abaixo. Como foi você quem criou esta solicitação, a aprovação precisa ser feita por outra pessoa."
          : permite.decidir
            ? "Compare as cotações abaixo e aprove a melhor. Só cotações completas e dentro da validade podem ser aprovadas."
            : "Compare as cotações abaixo. A aprovação é feita por um Aprovador ou Administrador.",
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
        permite.comprar
          ? h("button", { class: "primario", onClick: registrarCompra }, "Registrar compra")
          : "Feito por: Comprador ou Administrador",
      ],
      COMPRADA: [
        compra && compra.situacao_recebimento === "PARCIAL"
          ? "Parte dos materiais já chegou. Registre o restante quando for entregue."
          : `Registre o recebimento quando os materiais chegarem. Previsão: ${compra ? formatar.data(compra.previsao_entrega) : "—"}.`,
        permite.receber
          ? h("button", { class: "primario", onClick: () => registrarRecebimento() }, "Registrar recebimento")
          : "Feito por: Almoxarife ou Administrador",
      ],
    };

    const passo = passos[status];
    if (!passo) return null;

    return h(
      "aside",
      { class: "proximo-passo", dataset: { cor: corStatus(status) } },
      h("div", {}, h("strong", {}, "Próximo passo"), h("p", {}, passo[0])),
      typeof passo[1] === "string" ? h("span", { class: "responsavel" }, passo[1]) : passo[1]
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
            permite.comprar ? h("button", { class: "primario", onClick: registrarCompra }, "Registrar compra") : null
          )
        )
      );
    }

    if (!compra) return null;

    return h(
      "section",
      { class: "secao" },
      h(
        "div",
        { class: "titulo-secao" },
        h("h2", {}, "Compra e recebimento"),
        status === "COMPRADA" && permite.receber
          ? h("button", { class: "primario", onClick: () => registrarRecebimento() }, "Registrar recebimento")
          : null
      ),
      ficha([
        ["Fornecedor", compra.fornecedor],
        ["Número do pedido", compra.numero_pedido || "—"],
        ["Data da compra", formatar.data(compra.data_compra)],
        ["Previsão de entrega", formatar.data(compra.previsao_entrega)],
        ["Comprador", compra.comprador],
        ["Valor total", h("span", { class: "numero" }, formatar.moeda(compra.valor_total))],
        ["Forma de pagamento", compra.forma_pagamento || "—"],
        ["Entrega", etiquetaStatus(compra.situacao_recebimento)],
        compra.entregue_no_prazo === null
          ? null
          : ["Pontualidade", compra.entregue_no_prazo ? "Entregue no prazo" : "Entregue com atraso"],
        compra.observacao ? ["Observação", compra.observacao, true] : null,
      ]),
      tabela(
        [
          { titulo: "Produto", valor: (i) => i.produto },
          { titulo: "Comprado", classe: "direita numero", valor: (i) => formatar.numero(i.quantidade) },
          { titulo: "Recebido", classe: "direita numero", valor: (i) => formatar.numero(i.quantidade_recebida) },
          {
            titulo: "Pendente",
            classe: "direita numero",
            valor: (i) => (i.quantidade_pendente ? h("strong", {}, formatar.numero(i.quantidade_pendente)) : "0"),
          },
          { titulo: "Preço unitário", classe: "direita numero", valor: (i) => formatar.moeda(i.preco_unitario) },
          { titulo: "Subtotal", classe: "direita numero", valor: (i) => formatar.moeda(i.subtotal) },
        ],
        compra.itens
      ),
      recebimentos.length
        ? [
            h("h3", { style: { margin: "20px 0 10px" } }, "Recebimentos"),
            tabela(
              [
                { titulo: "Data", classe: "numero", valor: (r) => formatar.data(r.data_recebimento) },
                { titulo: "Nota fiscal", valor: (r) => r.nota_fiscal || "—" },
                {
                  titulo: "Itens",
                  valor: (r) =>
                    r.itens.map((i) => `${i.produto} (${formatar.numero(i.quantidade)})`).join(", "),
                },
                { titulo: "Recebido por", valor: (r) => r.recebedor },
                { titulo: "Observação", valor: (r) => r.observacao || "—" },
              ],
              recebimentos
            ),
          ]
        : null
    );
  }

  function registrarRecebimento() {
    const pendentes = compra.itens.filter((item) => item.quantidade_pendente > 0);

    const camposQuantidade = pendentes.map((item) =>
      h(
        "label",
        {},
        `${item.produto} (pendente: ${formatar.numero(item.quantidade_pendente)})`,
        h("input", {
          type: "number",
          min: 0,
          max: item.quantidade_pendente,
          step: 1,
          name: `quantidade_${item.produto_id}`,
          value: item.quantidade_pendente,
        })
      )
    );

    abrirDialogo({
      titulo: "Registrar recebimento",
      descricao: "Confira as quantidades que chegaram. Elas entram no estoque assim que você confirmar.",
      conteudo: [
        h("h3", {}, "Quantidades recebidas"),
        camposQuantidade,
        h(
          "div",
          { class: "linha-campos" },
          h("label", {}, "Data do recebimento", h("input", { type: "date", name: "data_recebimento", value: hojeISO() })),
          h("label", {}, "Nota fiscal", h("input", { name: "nota_fiscal", maxlength: "50" }))
        ),
        h("label", {}, "Observação", h("textarea", { name: "observacao", maxlength: "500" })),
      ],
      textoAcao: "Confirmar recebimento",
      aoEnviar: async (formulario) => {
        const campos = formulario.elements;

        const itens = pendentes
          .map((item) => ({
            produto_id: item.produto_id,
            quantidade: Number(campos[`quantidade_${item.produto_id}`].value || 0),
          }))
          .filter((item) => item.quantidade > 0);

        if (!itens.length) {
          throw new Error("Informe a quantidade recebida de pelo menos um produto.");
        }

        await api.post(`/solicitacoes-compra/${id}/compra/recebimentos`, {
          data_recebimento: campos.data_recebimento.value || null,
          nota_fiscal: campos.nota_fiscal.value.trim() || null,
          observacao: campos.observacao.value.trim() || null,
          itens,
        });

        recarregar();
      },
    });
  }

  /* ---------- Montagem ---------- */

  const acoes = [
    PODE_EDITAR.includes(status) && permite.editar ? h("button", { onClick: editar }, "Editar itens") : null,
    PODE_REPROVAR.includes(status) && permite.decidir ? h("button", { class: "perigo", onClick: reprovar }, "Reprovar") : null,
    PODE_CANCELAR.includes(status) && permite.editar ? h("button", { class: "perigo", onClick: cancelar }, "Cancelar") : null,
  ].filter(Boolean);

  const decisao =
    solicitacao.decisao_por && ["APROVADA", "COMPRADA", "RECEBIDA", "REPROVADA"].includes(status)
      ? [
          [status === "REPROVADA" ? "Reprovada por" : "Aprovada por", solicitacao.decisao_por],
          ["Data da decisão", formatar.dataHora(solicitacao.data_decisao)],
          solicitacao.justificativa_decisao ? ["Justificativa", solicitacao.justificativa_decisao, true] : null,
        ]
      : [];

  const topo = cabecalho(
    `Solicitação Nº ${solicitacao.id}`,
    etiquetaStatus(status),
    ...acoes
  );

  topo
    .querySelector(".cabecalho-texto")
    .prepend(h("a", { class: "voltar", href: "#/solicitacoes" }, "Voltar para solicitações"));

  const secoes = [
    topo,
    etapas(solicitacao, cotacoes.length, compra),
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
            h(
              "div",
              { class: "acoes-orcamento" },
              cotacoes.length ? botoesExportar(`/solicitacoes-compra/${id}/cotacoes/exportar`) : null,
              h(
                "button",
                {
                  title: "Planilha padrão com os itens desta solicitação, para o fornecedor preencher",
                  onClick: (evento) => baixar(`/solicitacoes-compra/${id}/cotacoes/modelo`, evento),
                },
                "Baixar modelo"
              ),
              PODE_COTAR.includes(status) && permite.cotar
                ? h("button", { onClick: importarPlanilha }, "Importar planilha")
                : null,
              PODE_COTAR.includes(status) && permite.cotar
                ? h("button", { class: "primario", onClick: () => formularioCotacao() }, "Registrar cotação")
                : null
            )
          ),
          cotacoes.length
            ? cotacoes.map(cartaoCotacao)
            : h(
                "div",
                { class: "quadro" },
                vazio("Peça preços aos fornecedores e registre cada cotação aqui para comparar.")
              )
        )
      : null,
    blocoAnexos(),
  ];

  area.replaceChildren(...secoes.filter(Boolean));
}
