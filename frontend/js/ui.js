import { baixarArquivo, montarQuery } from "./api.js";

export function h(tag, atributos = {}, ...filhos) {
  const elemento = document.createElement(tag);

  Object.entries(atributos || {}).forEach(([chave, valor]) => {
    if (valor === undefined || valor === null || valor === false) {
      return;
    }

    if (chave.startsWith("on") && typeof valor === "function") {
      elemento.addEventListener(chave.slice(2).toLowerCase(), valor);
    } else if (chave === "class") {
      elemento.className = valor;
    } else if (chave === "dataset") {
      Object.assign(elemento.dataset, valor);
    } else if (chave === "style" && typeof valor === "object") {
      Object.entries(valor).forEach(([propriedade, conteudo]) => {
        if (propriedade.startsWith("--")) {
          elemento.style.setProperty(propriedade, conteudo);
        } else {
          elemento.style[propriedade] = conteudo;
        }
      });
    } else if (valor === true) {
      elemento.setAttribute(chave, "");
    } else if (chave in elemento && typeof valor !== "string") {
      elemento[chave] = valor;
    } else {
      elemento.setAttribute(chave, valor);
    }
  });

  adicionarFilhos(elemento, filhos);
  return elemento;
}

function adicionarFilhos(elemento, filhos) {
  filhos.flat(Infinity).forEach((filho) => {
    if (filho === undefined || filho === null || filho === false) {
      return;
    }

    elemento.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  });
}

const formatoMoeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const formatoNumero = new Intl.NumberFormat("pt-BR");

export const formatar = {
  moeda: (valor) => (valor === null || valor === undefined ? "—" : formatoMoeda.format(valor)),
  numero: (valor) => (valor === null || valor === undefined ? "—" : formatoNumero.format(valor)),
  data(valor) {
    if (!valor) return "—";
    const [ano, mes, dia] = String(valor).slice(0, 10).split("-");
    return `${dia}/${mes}/${ano}`;
  },
  dataHora(valor) {
    if (!valor) return "—";
    const data = new Date(valor);
    return data.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  },
  dias(valor) {
    return valor === 1 ? "1 dia" : `${valor} dias`;
  },
};

export function hojeISO() {
  const agora = new Date();
  const ajuste = agora.getTimezoneOffset() * 60000;
  return new Date(agora.getTime() - ajuste).toISOString().slice(0, 10);
}

/* ---------- Status ---------- */

const STATUS = {
  ABERTA: ["Aberta", "azul"],
  EM_COTACAO: ["Em cotação", "laranja"],
  APROVADA: ["Aprovada", "verde"],
  COMPRADA: ["Comprada", "marrom"],
  RECEBIDA: ["Recebida", "agua"],
  CANCELADA: ["Cancelada", "ardosia"],
  REPROVADA: ["Reprovada", "vermelho"],
  ENTRADA: ["Entrada", "verde"],
  SAIDA: ["Saída", "vermelho"],
  PENDENTE: ["Entrega pendente", "laranja"],
  PARCIAL: ["Entrega parcial", "amarelo"],
  COMPLETO: ["Entrega completa", "agua"],
  ATIVO: ["Ativo", "verde"],
  INATIVO: ["Inativo", "ardosia"],
};

export function nomeStatus(status) {
  return (STATUS[status] || [status])[0];
}

export function corStatus(status) {
  return (STATUS[status] || [null, "ardosia"])[1];
}

export function etiquetaStatus(status) {
  return h("span", { class: "status", dataset: { cor: corStatus(status) } }, nomeStatus(status));
}

/* ---------- Avisos ---------- */

export function avisar(mensagem, tipo = "sucesso") {
  const area = document.getElementById("avisos");
  const aviso = h("div", { class: `aviso ${tipo === "erro" ? "erro" : ""}` }, mensagem);
  area.append(aviso);
  setTimeout(() => aviso.remove(), tipo === "erro" ? 6000 : 3500);
}

/* ---------- Blocos ---------- */

const SVG = "http://www.w3.org/2000/svg";

function svg(tag, atributos = {}, ...filhos) {
  const elemento = document.createElementNS(SVG, tag);
  Object.entries(atributos).forEach(([chave, valor]) => elemento.setAttribute(chave, valor));
  filhos.forEach((filho) => elemento.append(filho));
  return elemento;
}

/*
 * Serras ao entardecer, em camadas. A camada da frente usa a cor de fundo
 * da página, então as montanhas "viram" o conteúdo logo abaixo.
 * variante "cena" é a versão alta usada na tela de entrada.
 */
export function paisagem(variante = "faixa") {
  const cena = variante === "cena";
  const altura = cena ? 420 : 160;

  const camadas = cena
    ? [
        ["monte-fundo", "M0 250 L120 190 L210 220 L330 120 L430 175 L520 140 L640 60 L760 150 L860 110 L980 170 L1100 95 L1210 160 L1330 120 L1440 170 L1440 420 L0 420 Z"],
        ["monte-meio", "M0 300 L140 250 L260 285 L380 215 L500 270 L620 235 L760 300 L900 240 L1040 290 L1180 230 L1300 270 L1440 245 L1440 420 L0 420 Z"],
        ["monte-perto", "M0 350 L180 320 L320 345 L470 305 L640 350 L820 315 L1000 355 L1160 320 L1320 345 L1440 325 L1440 420 L0 420 Z"],
        ["monte-chao", "M0 395 L240 380 L520 398 L800 382 L1080 400 L1300 385 L1440 395 L1440 420 L0 420 Z"],
      ]
    : [
        ["monte-fundo", "M0 95 L110 70 L200 82 L320 40 L420 66 L540 52 L660 18 L780 58 L900 44 L1010 66 L1130 32 L1250 60 L1360 46 L1440 62 L1440 160 L0 160 Z"],
        ["monte-meio", "M0 112 L150 92 L280 108 L420 80 L560 104 L700 88 L840 112 L980 90 L1120 110 L1260 86 L1380 100 L1440 94 L1440 160 L0 160 Z"],
        ["monte-chao", "M0 140 L220 128 L480 142 L760 126 L1040 142 L1280 130 L1440 138 L1440 160 L0 160 Z"],
      ];

  const passaros = cena
    ? [[560, 92], [592, 80], [620, 98], [648, 74], [684, 88], [716, 70]]
    : [[1040, 26], [1066, 18], [1092, 30]];

  return svg(
    "svg",
    {
      class: `paisagem paisagem-${variante}`,
      viewBox: `0 0 1440 ${altura}`,
      preserveAspectRatio: "xMidYMax slice",
      "aria-hidden": "true",
      focusable: "false",
    },
    ...camadas.map(([classe, d]) => svg("path", { class: classe, d })),
    ...passaros.map(([x, y]) =>
      svg("path", { class: "passaro", d: `M${x - 7} ${y - 3} Q${x - 3} ${y - 6} ${x} ${y} Q${x + 3} ${y - 6} ${x + 7} ${y - 3}` })
    )
  );
}

export function cabecalho(titulo, descricao, ...acoes) {
  return h(
    "header",
    { class: "cabecalho" },
    h(
      "div",
      { class: "cabecalho-conteudo" },
      h(
        "div",
        { class: "cabecalho-texto" },
        h("h1", {}, titulo),
        descricao ? h("p", {}, descricao) : null
      ),
      acoes.filter(Boolean).length ? h("div", { class: "acoes-cabecalho" }, acoes) : null
    ),
    paisagem()
  );
}

export function vazio(mensagem, acao) {
  return h("div", { class: "vazio" }, h("p", {}, mensagem), acao || null);
}

export function carregando() {
  return h("div", { class: "carregando" }, "Carregando…");
}

export function tabela(colunas, linhas, opcoes = {}) {
  if (!linhas.length) {
    return h("div", { class: "quadro" }, vazio(opcoes.vazio || "Nada por aqui ainda.", opcoes.acaoVazio));
  }

  return h(
    "div",
    { class: "quadro" },
    h(
      "table",
      {},
      h(
        "thead",
        {},
        h(
          "tr",
          {},
          colunas.map((coluna) => h("th", { class: coluna.classe || "", scope: "col" }, coluna.titulo))
        )
      ),
      h(
        "tbody",
        {},
        linhas.map((linha) =>
          h(
            "tr",
            { class: opcoes.classeLinha ? opcoes.classeLinha(linha) : "" },
            colunas.map((coluna) => h("td", { class: coluna.classe || "" }, coluna.valor(linha)))
          )
        )
      ),
      opcoes.rodape ? h("tfoot", {}, opcoes.rodape) : null
    )
  );
}

export function paginacao(pagina, quantidade, tamanho, aoMudar) {
  return h(
    "nav",
    { class: "paginacao", "aria-label": "Paginação" },
    h("button", { class: "pequeno", disabled: pagina <= 1, onClick: () => aoMudar(pagina - 1) }, "Anterior"),
    h("span", { class: "suave" }, `Página ${pagina}`),
    h(
      "button",
      { class: "pequeno", disabled: quantidade < tamanho, onClick: () => aoMudar(pagina + 1) },
      "Próxima"
    )
  );
}

export function campoFiltro(rotulo, controle) {
  return h("label", {}, rotulo, controle);
}

export function seletor(opcoes, valorAtual, atributos = {}) {
  return h(
    "select",
    atributos,
    opcoes.map(([valor, texto]) =>
      h("option", { value: valor, selected: String(valor) === String(valorAtual ?? "") }, texto)
    )
  );
}

/* ---------- Diálogos ---------- */

function criarCampo(campo) {
  const atributos = {
    name: campo.nome,
    required: campo.obrigatorio,
    min: campo.min,
    max: campo.max,
    step: campo.passo,
    minlength: campo.minimo,
    maxlength: campo.maximo,
    placeholder: campo.dica,
    autocomplete: campo.autocompletar,
  };

  let controle;

  if (campo.tipo === "select") {
    controle = seletor(campo.opcoes, campo.valor, atributos);
  } else if (campo.tipo === "textarea") {
    controle = h("textarea", atributos, campo.valor ?? "");
  } else if (campo.tipo === "checkbox") {
    controle = h("input", { ...atributos, type: "checkbox", checked: Boolean(campo.valor) });
    return h("label", { class: "marcador" }, controle, campo.rotulo);
  } else {
    controle = h("input", { ...atributos, type: campo.tipo || "text", value: campo.valor ?? "" });
  }

  return h("label", {}, campo.rotulo, controle);
}

export function lerFormulario(formulario, campos) {
  const dados = {};

  campos.flat().forEach((campo) => {
    const controle = formulario.elements[campo.nome];

    if (!controle) return;

    if (campo.tipo === "checkbox") {
      dados[campo.nome] = controle.checked;
      return;
    }

    const texto = controle.value.trim();

    if (texto === "") {
      dados[campo.nome] = null;
    } else if (campo.tipo === "number" || campo.numero) {
      dados[campo.nome] = Number(texto);
    } else {
      dados[campo.nome] = texto;
    }
  });

  return dados;
}

export function abrirDialogo({ titulo, descricao, conteudo, textoAcao = "Salvar", classeAcao = "primario", aoEnviar }) {
  const erro = h("p", { class: "erro", role: "alert", hidden: true });
  const botaoAcao = h("button", { type: "submit", class: classeAcao }, textoAcao);

  const formulario = h(
    "form",
    { method: "dialog", novalidate: false },
    h("h2", {}, titulo),
    descricao ? h("p", { class: "suave" }, descricao) : null,
    conteudo,
    erro,
    h(
      "div",
      { class: "rodape" },
      h("button", { type: "button", onClick: () => dialogo.close() }, "Cancelar"),
      botaoAcao
    )
  );

  const dialogo = h("dialog", {}, formulario);

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    erro.hidden = true;
    botaoAcao.disabled = true;

    try {
      await aoEnviar(formulario);
      dialogo.close();
    } catch (falha) {
      erro.textContent = falha.message;
      erro.hidden = false;
    } finally {
      botaoAcao.disabled = false;
    }
  });

  dialogo.addEventListener("close", () => dialogo.remove());
  document.body.append(dialogo);
  dialogo.showModal();

  const primeiro = formulario.querySelector("input, select, textarea");
  if (primeiro) primeiro.focus();

  return dialogo;
}

export function abrirFormulario({ titulo, descricao, campos, textoAcao, classeAcao, aoEnviar }) {
  const conteudo = campos.map((campo) =>
    Array.isArray(campo) ? h("div", { class: "linha-campos" }, campo.map(criarCampo)) : criarCampo(campo)
  );

  return abrirDialogo({
    titulo,
    descricao,
    conteudo,
    textoAcao,
    classeAcao,
    aoEnviar: (formulario) => aoEnviar(lerFormulario(formulario, campos), formulario),
  });
}

export function confirmar({ titulo, mensagem, textoAcao = "Confirmar", perigo = false }) {
  return new Promise((resolver) => {
    let confirmado = false;

    const dialogo = abrirDialogo({
      titulo,
      conteudo: h("p", {}, mensagem),
      textoAcao,
      classeAcao: perigo ? "perigo cheio" : "primario",
      aoEnviar: async () => {
        confirmado = true;
      },
    });

    dialogo.addEventListener("close", () => resolver(confirmado));
  });
}

export async function executar(acao, mensagemSucesso) {
  try {
    const resultado = await acao();
    if (mensagemSucesso) avisar(mensagemSucesso);
    return resultado;
  } catch (falha) {
    avisar(falha.message, "erro");
    return undefined;
  }
}


/* Botões "Excel" e "PDF" que baixam a exportação com os filtros atuais. */
export function botoesExportar(caminho, obterFiltros = () => ({})) {
  const exportar = (formato) => async (evento) => {
    const botao = evento.currentTarget;
    botao.disabled = true;

    try {
      const nome = await baixarArquivo(`${caminho}${montarQuery({ ...obterFiltros(), formato })}`);
      avisar(`Arquivo ${nome} baixado.`);
    } catch (falha) {
      avisar(falha.message, "erro");
    } finally {
      botao.disabled = false;
    }
  };

  return h(
    "div",
    { class: "exportar", role: "group", "aria-label": "Exportar" },
    h("span", { class: "suave" }, "Exportar"),
    h("button", { type: "button", class: "pequeno", onClick: exportar("xlsx") }, "Excel"),
    h("button", { type: "button", class: "pequeno", onClick: exportar("pdf") }, "PDF")
  );
}
