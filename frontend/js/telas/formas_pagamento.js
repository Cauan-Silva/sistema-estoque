import { api, montarQuery } from "../api.js";
import {
  abrirFormulario,
  cabecalho,
  confirmar,
  etiquetaStatus,
  executar,
  formatar,
  h,
  seletor,
} from "../ui.js";

const TAMANHO = 10;

const TIPOS = {
  A_VISTA: "À vista",
  A_PRAZO: "A prazo",
};

export function descreverForma(forma) {
  return forma ? `${forma.codigo} - ${forma.titulo}` : "";
}

function resumoParcelas(forma) {
  if (forma.tipo === "A_VISTA") return "Pagamento único";
  if (forma.parcelas === 1 && !forma.intervalo_dias) return "Data combinada";
  const intervalo = forma.intervalo_dias ? ` a cada ${formatar.dias(forma.intervalo_dias)}` : "";
  return `${forma.parcelas} parcela${forma.parcelas > 1 ? "s" : ""}${intervalo}`;
}

/*
 * Grade com busca, ordenação por coluna e paginação.
 * modo "selecao": clicar numa linha escolhe a forma (só ativas).
 * modo "cadastro": mostra status e ações de edição.
 */
function criarGrade({ modo, aoSelecionar, acoes }) {
  const estado = { busca: "", ordem: "codigo", decrescente: false, pagina: 1, total: 0, ativo: modo === "selecao" ? true : "" };

  const corpo = h("tbody");
  const contagem = h("span", { class: "suave" });
  const campoPagina = h("input", {
    type: "number",
    min: 1,
    class: "campo-pagina",
    "aria-label": "Página",
    onChange: (evento) => irPara(Number(evento.target.value)),
  });
  const totalPaginas = h("span");

  const colunas = [
    ["codigo", "Código"],
    ["titulo", "Título"],
    ["tipo", "Tipo"],
  ];

  const cabecalhos = colunas.map(([chave, titulo]) =>
    h(
      "th",
      { scope: "col", dataset: { chave } },
      h(
        "button",
        {
          type: "button",
          class: "ordenar",
          onClick: () => {
            estado.decrescente = estado.ordem === chave ? !estado.decrescente : false;
            estado.ordem = chave;
            estado.pagina = 1;
            carregar();
          },
        },
        titulo,
        h("span", { class: "seta", "aria-hidden": "true" })
      )
    )
  );

  const navegacao = (rotulo, texto, destino) =>
    h("button", { type: "button", class: "pequeno", "aria-label": rotulo, onClick: () => irPara(destino()) }, texto);

  const paginas = () => Math.max(1, Math.ceil(estado.total / TAMANHO));

  function irPara(pagina) {
    const alvo = Math.min(Math.max(1, pagina || 1), paginas());
    if (alvo === estado.pagina) {
      campoPagina.value = alvo;
      return;
    }
    estado.pagina = alvo;
    carregar();
  }

  function linha(forma) {
    const celulas = [
      h("td", { class: "numero" }, forma.codigo),
      h("td", {}, forma.titulo, h("small", { class: "detalhe-forma" }, resumoParcelas(forma))),
      h("td", {}, TIPOS[forma.tipo]),
    ];

    if (modo === "cadastro") {
      celulas.push(
        h("td", {}, etiquetaStatus(forma.ativo ? "ATIVO" : "INATIVO")),
        h("td", { class: "acoes" }, acoes(forma))
      );

      return h("tr", {}, celulas);
    }

    return h(
      "tr",
      {
        class: "selecionavel",
        tabindex: "0",
        onClick: () => aoSelecionar(forma),
        onKeydown: (evento) => {
          if (evento.key === "Enter" || evento.key === " ") {
            evento.preventDefault();
            aoSelecionar(forma);
          }
        },
      },
      celulas
    );
  }

  async function carregar() {
    const resposta = await executar(() =>
      api.get(
        `/formas-pagamento${montarQuery({
          busca: estado.busca,
          ativo: estado.ativo,
          ordem: estado.ordem,
          decrescente: estado.decrescente,
          pagina: estado.pagina,
          tamanho: TAMANHO,
        })}`
      )
    );

    if (!resposta) return;

    estado.total = resposta.total;

    cabecalhos.forEach((th) => {
      const ativa = th.dataset.chave === estado.ordem;
      th.setAttribute("aria-sort", ativa ? (estado.decrescente ? "descending" : "ascending") : "none");
      th.querySelector(".seta").textContent = ativa ? (estado.decrescente ? "▼" : "▲") : "↕";
    });

    corpo.replaceChildren(
      ...(resposta.itens.length
        ? resposta.itens.map(linha)
        : [
            h(
              "tr",
              {},
              h(
                "td",
                { colspan: modo === "cadastro" ? 5 : 3, class: "vazio" },
                estado.busca ? "Nenhuma forma de pagamento encontrada." : "Nenhuma forma de pagamento cadastrada."
              )
            ),
          ])
    );

    contagem.textContent = `${formatar.numero(resposta.total)} registro${resposta.total === 1 ? "" : "s"}`;
    campoPagina.value = estado.pagina;
    campoPagina.max = paginas();
    totalPaginas.textContent = `de ${paginas()}`;
  }

  let espera;
  const busca = h("input", {
    type: "search",
    "aria-label": "Buscar forma de pagamento",
    placeholder: "Código ou título",
    onInput: (evento) => {
      clearTimeout(espera);
      espera = setTimeout(() => {
        estado.busca = evento.target.value.trim();
        estado.pagina = 1;
        carregar();
      }, 250);
    },
  });

  const filtros = [h("label", { class: "busca-grade" }, "Busca", busca)];

  if (modo === "cadastro") {
    filtros.push(
      h(
        "label",
        { class: "busca-grade" },
        "Status",
        seletor(
          [
            ["", "Todas"],
            ["true", "Ativas"],
            ["false", "Inativas"],
          ],
          "",
          {
            onChange: (evento) => {
              estado.ativo = evento.target.value;
              estado.pagina = 1;
              carregar();
            },
          }
        )
      )
    );
  }

  const cabecalhoExtra =
    modo === "cadastro"
      ? [h("th", { scope: "col" }, "Status"), h("th", { scope: "col", class: "acoes" }, h("span", { class: "oculto-visualmente" }, "Ações"))]
      : [];

  const elemento = h(
    "div",
    { class: "grade" },
    h("div", { class: "grade-busca" }, filtros),
    h("div", { class: "quadro grade-tabela" }, h("table", {}, h("thead", {}, h("tr", {}, cabecalhos, cabecalhoExtra)), corpo)),
    h(
      "div",
      { class: "grade-rodape" },
      contagem,
      h(
        "nav",
        { class: "grade-paginas", "aria-label": "Paginação" },
        navegacao("Primeira página", "⏮", () => 1),
        navegacao("Página anterior", "◀", () => estado.pagina - 1),
        h("span", {}, "Página"),
        campoPagina,
        totalPaginas,
        navegacao("Próxima página", "▶", () => estado.pagina + 1),
        navegacao("Última página", "⏭", () => paginas())
      )
    )
  );

  return { elemento, carregar, busca };
}

export function selecionarFormaPagamento(aoSelecionar) {
  let fechar;

  const grade = criarGrade({
    modo: "selecao",
    aoSelecionar: (forma) => {
      fechar();
      aoSelecionar(forma);
    },
  });

  const dialogo = h(
    "dialog",
    { class: "dialogo-selecao", "aria-labelledby": "titulo-selecao-pagamento" },
    h(
      "header",
      { class: "barra-dialogo" },
      h("h2", { id: "titulo-selecao-pagamento" }, "Selecione uma forma de pagamento"),
      h("button", { type: "button", class: "fechar", "aria-label": "Fechar", onClick: () => fechar() }, "✕")
    ),
    h("div", { class: "corpo-dialogo" }, grade.elemento)
  );

  fechar = () => dialogo.close();
  dialogo.addEventListener("close", () => dialogo.remove());
  document.body.append(dialogo);
  dialogo.showModal();
  grade.carregar();
  grade.busca.focus();
}

/* Campo de formulário: mostra a forma escolhida e abre o seletor. */
export function campoFormaPagamento(valorInicial) {
  let escolhida = valorInicial || null;

  const texto = h("span", { class: "forma-escolhida" });
  const limpar = h("button", { type: "button", class: "pequeno texto", onClick: () => definir(null) }, "Limpar");

  function definir(forma) {
    escolhida = forma;
    texto.textContent = forma ? forma.descricao || descreverForma(forma) : "Nenhuma";
    texto.classList.toggle("suave", !forma);
    limpar.hidden = !forma;
  }

  definir(escolhida);

  return {
    elemento: h(
      "div",
      { class: "campo-forma" },
      h("span", { class: "rotulo-campo" }, "Forma de pagamento"),
      h(
        "div",
        { class: "linha-forma" },
        texto,
        h("button", { type: "button", class: "pequeno", onClick: () => selecionarFormaPagamento(definir) }, "Selecionar"),
        limpar
      )
    ),
    valor: () => (escolhida ? escolhida.id : null),
  };
}

export async function telaFormasPagamento(area) {
  function campos(forma = {}) {
    return [
      [
        {
          nome: "codigo",
          rotulo: "Código",
          obrigatorio: true,
          maximo: 10,
          dica: "Ex.: 3.13",
          valor: forma.codigo,
        },
        {
          nome: "tipo",
          rotulo: "Tipo",
          tipo: "select",
          obrigatorio: true,
          opcoes: Object.entries(TIPOS),
          valor: forma.tipo || "A_PRAZO",
        },
      ],
      { nome: "titulo", rotulo: "Título", obrigatorio: true, minimo: 2, maximo: 100, valor: forma.titulo },
      [
        { nome: "parcelas", rotulo: "Parcelas", tipo: "number", min: 1, max: 48, passo: 1, obrigatorio: true, valor: forma.parcelas ?? 1 },
        {
          nome: "intervalo_dias",
          rotulo: "Dias entre parcelas",
          tipo: "number",
          min: 0,
          max: 365,
          passo: 1,
          obrigatorio: true,
          valor: forma.intervalo_dias ?? 30,
        },
      ],
    ];
  }

  function formulario(forma) {
    abrirFormulario({
      titulo: forma ? `Editar ${descreverForma(forma)}` : "Nova forma de pagamento",
      descricao: "Pagamento à vista tem sempre uma única parcela.",
      campos: campos(forma),
      textoAcao: forma ? "Salvar alterações" : "Cadastrar forma de pagamento",
      aoEnviar: async (dados) => {
        if (forma) {
          await api.put(`/formas-pagamento/${forma.id}`, dados);
        } else {
          await api.post("/formas-pagamento", dados);
        }
        grade.carregar();
      },
    });
  }

  async function alternar(forma) {
    const ativar = !forma.ativo;

    const ok = await confirmar({
      titulo: ativar ? "Reativar forma de pagamento" : "Inativar forma de pagamento",
      mensagem: ativar
        ? `${descreverForma(forma)} volta a aparecer na seleção das cotações.`
        : `${descreverForma(forma)} deixa de aparecer na seleção das cotações. Cotações e compras antigas continuam com ela.`,
      textoAcao: ativar ? "Reativar" : "Inativar",
      perigo: !ativar,
    });

    if (ok) {
      await executar(
        () => api.patch(`/formas-pagamento/${forma.id}/status`, { ativo: ativar }),
        ativar ? "Forma de pagamento reativada." : "Forma de pagamento inativada."
      );
      grade.carregar();
    }
  }

  const grade = criarGrade({
    modo: "cadastro",
    acoes: (forma) => [
      h("button", { class: "pequeno", onClick: () => formulario(forma) }, "Editar"),
      h(
        "button",
        { class: `pequeno ${forma.ativo ? "perigo" : ""}`, onClick: () => alternar(forma) },
        forma.ativo ? "Inativar" : "Reativar"
      ),
    ],
  });

  area.replaceChildren(
    cabecalho(
      "Formas de pagamento",
      "Condições de pagamento usadas nas cotações e copiadas para as compras.",
      h("button", { class: "primario", onClick: () => formulario() }, "Cadastrar forma de pagamento")
    ),
    grade.elemento
  );

  await grade.carregar();
}
