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
  RECEBIDA: ["Recebida", "ardosia"],
  CANCELADA: ["Cancelada", "ardosia"],
  REPROVADA: ["Reprovada", "vermelho"],
  ENTRADA: ["Entrada", "verde"],
  SAIDA: ["Saída", "vermelho"],
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

export function cabecalho(titulo, descricao, ...acoes) {
  return h(
    "header",
    { class: "cabecalho" },
    h("div", {}, h("h1", {}, titulo), descricao ? h("p", {}, descricao) : null),
    acoes.length ? h("div", { class: "acoes-cabecalho" }, acoes) : null
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
