import { api, listarTodos, montarQuery } from "../api.js";
import { pode } from "../sessao.js";
import {
  abrirDialogo,
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

const TAMANHO = 20;

const STATUS_FILTRO = ["ABERTA", "EM_COTACAO", "APROVADA", "COMPRADA", "REPROVADA", "CANCELADA"];

export function editorItens(produtos, itensIniciais = []) {
  const opcoes = [["", "Escolha um produto"], ...produtos.map((p) => [p.id, p.nome])];
  const container = h("div", { class: "itens-editaveis" });

  function adicionar(item = {}) {
    const linha = h(
      "div",
      { class: "item-editavel" },
      h("label", {}, "Produto", seletor(opcoes, item.produto_id, { required: true, name: "produto" })),
      h(
        "label",
        {},
        "Quantidade",
        h("input", { type: "number", min: 1, step: 1, required: true, name: "quantidade", value: item.quantidade ?? "" })
      ),
      h(
        "button",
        {
          type: "button",
          class: "pequeno perigo",
          "aria-label": "Remover item",
          onClick: () => {
            if (container.children.length > 1) linha.remove();
          },
        },
        "Remover"
      )
    );

    container.append(linha);
  }

  (itensIniciais.length ? itensIniciais : [{}]).forEach(adicionar);

  return {
    elemento: h(
      "div",
      {},
      h("h3", { style: { marginBottom: "8px" } }, "Itens"),
      container,
      h(
        "button",
        { type: "button", class: "pequeno", style: { marginTop: "8px" }, onClick: () => adicionar() },
        "Adicionar item"
      )
    ),
    ler() {
      return [...container.children].map((linha) => ({
        produto_id: Number(linha.querySelector("[name=produto]").value),
        quantidade: Number(linha.querySelector("[name=quantidade]").value),
      }));
    },
  };
}

export function formularioSolicitacao({ produtos, solicitacao, aoSalvar }) {
  const editor = editorItens(produtos, solicitacao?.itens || []);
  const observacao = h("textarea", { name: "observacao", maxlength: "500" }, solicitacao?.observacao || "");

  abrirDialogo({
    titulo: solicitacao ? `Editar solicitação Nº ${solicitacao.id}` : "Nova solicitação de compra",
    descricao: "Liste os produtos e as quantidades que precisam ser compradas.",
    conteudo: [editor.elemento, h("label", {}, "Observação", observacao)],
    textoAcao: solicitacao ? "Salvar alterações" : "Criar solicitação",
    aoEnviar: async () => {
      const itens = editor.ler();
      const ids = itens.map((item) => item.produto_id);

      if (new Set(ids).size !== ids.length) {
        throw new Error("Cada produto pode aparecer apenas uma vez.");
      }

      const corpo = { observacao: observacao.value.trim() || null, itens };
      const resultado = solicitacao
        ? await api.put(`/solicitacoes-compra/${solicitacao.id}`, corpo)
        : await api.post("/solicitacoes-compra", corpo);

      await aoSalvar(resultado);
    },
  });
}

export async function telaSolicitacoes(area) {
  const podeCriar = pode("solicitacoes.editar");
  const produtos = await listarTodos("/produtos");
  const filtros = { status: "", apenas_minhas: false, pagina: 1 };
  const lista = h("div");

  function nova() {
    formularioSolicitacao({
      produtos,
      aoSalvar: async (criada) => {
        window.location.hash = `#/solicitacoes/${criada.id}`;
      },
    });
  }

  async function carregar() {
    const solicitacoes = await executar(() =>
      api.get(
        `/solicitacoes-compra${montarQuery({
          status: filtros.status,
          apenas_minhas: filtros.apenas_minhas,
          pagina: filtros.pagina,
          tamanho: TAMANHO,
        })}`
      )
    );

    if (!solicitacoes) return;

    lista.replaceChildren(
      tabela(
        [
          {
            titulo: "Solicitação",
            valor: (s) => h("a", { href: `#/solicitacoes/${s.id}` }, `Nº ${s.id}`),
          },
          { titulo: "Criada em", classe: "numero", valor: (s) => formatar.dataHora(s.data_criacao) },
          { titulo: "Solicitante", valor: (s) => s.solicitante },
          {
            titulo: "Itens",
            valor: (s) =>
              s.itens
                .map((item) => `${item.produto} (${formatar.numero(item.quantidade)})`)
                .join(", "),
          },
          { titulo: "Status", valor: (s) => etiquetaStatus(s.status) },
        ],
        solicitacoes,
        {
          vazio: filtros.status || filtros.apenas_minhas
            ? "Nenhuma solicitação com esses filtros."
            : "Nenhuma solicitação de compra ainda.",
          acaoVazio: !podeCriar
            ? null
            : produtos.length
              ? h("button", { class: "primario", onClick: nova }, "Criar solicitação")
              : h("a", { class: "botao", href: "#/produtos" }, "Cadastre produtos primeiro"),
        }
      ),
      paginacao(filtros.pagina, solicitacoes.length, TAMANHO, (pagina) => {
        filtros.pagina = pagina;
        carregar();
      })
    );
  }

  area.replaceChildren(
    cabecalho(
      "Solicitações de compra",
      "Cada solicitação passa por cotação, aprovação e registro da compra.",
      podeCriar && pode("cotacoes.editar")
        ? h("a", { class: "botao", href: "#/solicitacoes/importar" }, "Importar orçamentos")
        : null,
      podeCriar ? h("button", { class: "primario", disabled: !produtos.length, onClick: nova }, "Criar solicitação") : null
    ),
    h(
      "div",
      { class: "filtros" },
      campoFiltro(
        "Status",
        seletor([["", "Todos"], ...STATUS_FILTRO.map((s) => [s, nomeStatus(s)])], "", {
          onChange: (evento) => {
            filtros.status = evento.target.value;
            filtros.pagina = 1;
            carregar();
          },
        })
      ),
      h(
        "label",
        { class: "marcador" },
        h("input", {
          type: "checkbox",
          onChange: (evento) => {
            filtros.apenas_minhas = evento.target.checked;
            filtros.pagina = 1;
            carregar();
          },
        }),
        "Só as minhas"
      )
    ),
    lista
  );

  await carregar();
}
