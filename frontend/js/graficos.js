import { h } from "./ui.js";

/*
 * Gráficos em HTML e CSS, sem bibliotecas.
 * Cores vêm dos tokens --grafico-1..3 (validados para daltonismo nos dois temas).
 * Cada marca mostra uma dica ao passar o mouse ou focar pelo teclado,
 * e todo gráfico tem um resumo em texto para leitores de ecrã.
 */

let dica;

function obterDica() {
  if (!dica) {
    dica = h("div", { class: "dica-grafico", role: "tooltip", hidden: true });
    document.body.append(dica);
  }
  return dica;
}

function mostrarDica(evento, texto) {
  const caixa = obterDica();
  caixa.textContent = texto;
  caixa.hidden = false;

  const alvo = evento.currentTarget.getBoundingClientRect();
  const x = evento.clientX ?? alvo.left + alvo.width / 2;
  const y = evento.clientY ?? alvo.top;

  const largura = caixa.offsetWidth;
  const esquerda = Math.min(Math.max(8, x - largura / 2), window.innerWidth - largura - 8);

  caixa.style.left = `${esquerda}px`;
  caixa.style.top = `${Math.max(8, y - caixa.offsetHeight - 12)}px`;
}

function esconderDica() {
  if (dica) dica.hidden = true;
}

function comDica(elemento, texto) {
  elemento.setAttribute("tabindex", "0");
  elemento.setAttribute("role", "img");
  elemento.setAttribute("aria-label", texto);
  elemento.addEventListener("mousemove", (evento) => mostrarDica(evento, texto));
  elemento.addEventListener("mouseleave", esconderDica);
  elemento.addEventListener("focus", (evento) => mostrarDica(evento, texto));
  elemento.addEventListener("blur", esconderDica);
  return elemento;
}

function legenda(series) {
  return h(
    "ul",
    { class: "legenda-grafico" },
    series.map((serie) =>
      h(
        "li",
        {},
        h("span", { class: "amostra", style: { background: serie.cor }, "aria-hidden": "true" }),
        serie.texto ?? serie.nome
      )
    )
  );
}

function figura(titulo, descricao, conteudo, extra) {
  return h(
    "figure",
    { class: "grafico" },
    h("figcaption", {}, h("h3", {}, titulo), descricao ? h("p", { class: "suave" }, descricao) : null),
    extra || null,
    conteudo
  );
}

function vazioGrafico(texto) {
  return h("p", { class: "grafico-vazio suave" }, texto);
}

/* Colunas verticais, uma série, para valores ao longo do tempo. */
export function colunas({ titulo, descricao, itens, formatar, cor = "var(--grafico-1)", vazio = "Sem dados no período." }) {
  if (!itens.length || itens.every((item) => !item.valor)) {
    return figura(titulo, descricao, vazioGrafico(vazio));
  }

  const maximo = Math.max(...itens.map((item) => item.valor));
  const indiceMaior = itens.findIndex((item) => item.valor === maximo);

  return figura(
    titulo,
    descricao,
    h(
      "div",
      { class: "colunas-grafico", role: "list", style: { "--quantidade": itens.length } },
      itens.map((item, indice) => {
        const altura = maximo ? (item.valor / maximo) * 100 : 0;
        const texto = `${item.rotulo}: ${formatar(item.valor)}`;

        return h(
          "div",
          { class: "coluna-item", role: "listitem" },
          h(
            "div",
            { class: "coluna-area" },
            indice === indiceMaior || indice === itens.length - 1
              ? h("span", { class: "valor-coluna" }, formatar(item.valor))
              : null,
            comDica(
              h("div", {
                class: "coluna",
                style: { height: `${Math.max(altura, item.valor ? 2 : 0)}%`, background: cor },
              }),
              texto
            )
          ),
          h("span", { class: "rotulo-coluna" }, item.rotulo)
        );
      })
    )
  );
}

/* Colunas agrupadas, duas ou mais séries por categoria. */
export function colunasAgrupadas({ titulo, descricao, categorias, series, formatar, vazio = "Sem dados no período." }) {
  const valores = series.flatMap((serie) => serie.valores);

  if (!valores.length || valores.every((valor) => !valor)) {
    return figura(titulo, descricao, vazioGrafico(vazio), legenda(series));
  }

  const maximo = Math.max(...valores);

  return figura(
    titulo,
    descricao,
    h(
      "div",
      { class: "colunas-grafico agrupadas", role: "list", style: { "--quantidade": categorias.length } },
      categorias.map((categoria, indice) =>
        h(
          "div",
          { class: "coluna-item", role: "listitem" },
          h(
            "div",
            { class: "coluna-area grupo" },
            series.map((serie) => {
              const valor = serie.valores[indice];
              return comDica(
                h("div", {
                  class: "coluna",
                  style: {
                    height: `${valor ? Math.max((valor / maximo) * 100, 2) : 0}%`,
                    background: serie.cor,
                  },
                }),
                `${categoria}, ${serie.nome}: ${formatar(valor)}`
              );
            })
          ),
          h("span", { class: "rotulo-coluna" }, categoria)
        )
      )
    ),
    legenda(series)
  );
}

/* Barras horizontais, uma série, para comparar categorias. */
export function barras({ titulo, descricao, itens, formatar, cor = "var(--grafico-1)", vazio = "Sem dados." }) {
  if (!itens.length || itens.every((item) => !item.valor)) {
    return figura(titulo, descricao, vazioGrafico(vazio));
  }

  const maximo = Math.max(...itens.map((item) => item.valor));

  return figura(
    titulo,
    descricao,
    h(
      "div",
      { class: "barras-grafico", role: "list" },
      itens.map((item) =>
        h(
          "div",
          { class: "barra-item", role: "listitem" },
          h("span", { class: "rotulo-barra" }, item.rotulo),
          h(
            "div",
            { class: "barra-trilho" },
            h(
              "div",
              { class: "barra-area" },
              comDica(
                h("div", {
                  class: "barra-valor",
                  style: { width: `${Math.max((item.valor / maximo) * 100, item.valor ? 1 : 0)}%`, background: item.cor || cor },
                }),
                `${item.rotulo}: ${formatar(item.valor)}`
              )
            ),
            h("span", { class: "valor-barra" }, formatar(item.valor))
          )
        )
      )
    )
  );
}

/* Barra única empilhada, para partes de um todo. */
export function barraEmpilhada({ titulo, descricao, partes, formatar, vazio = "Sem dados." }) {
  const total = partes.reduce((soma, parte) => soma + parte.valor, 0);

  const series = partes.map((parte) => ({
    ...parte,
    texto: `${parte.nome}: ${formatar(parte.valor)}${total ? ` (${Math.round((parte.valor / total) * 100)}%)` : ""}`,
  }));

  if (!total) {
    return figura(titulo, descricao, vazioGrafico(vazio), legenda(series));
  }

  return figura(
    titulo,
    descricao,
    h(
      "div",
      { class: "empilhada", role: "img", "aria-label": series.map((s) => s.texto).join("; ") },
      partes
        .filter((parte) => parte.valor > 0)
        .map((parte) =>
          comDica(
            h("div", {
              class: "segmento",
              style: { flexGrow: parte.valor, background: parte.cor },
            }),
            series.find((s) => s.nome === parte.nome).texto
          )
        )
    ),
    legenda(series)
  );
}


/* ---------- Cartões de indicador com mini gráficos ---------- */

/*
 * cor: "1".."6" (paleta categórica) ou "alerta".
 * variacao: { texto, sentido: "alta" | "baixa", tom: "bom" | "ruim" | "neutro" }
 * visual: elemento de miniBarras, anel ou progresso.
 */
export function cartaoIndicador({ rotulo, valor, cor = "1", detalhe, variacao, visual }) {
  return h(
    "article",
    { class: "cartao-indicador", dataset: { cor } },
    h(
      "div",
      { class: "cartao-topo" },
      h("h3", {}, rotulo),
      variacao
        ? h(
            "span",
            { class: "variacao", dataset: { tom: variacao.tom || "neutro" } },
            h("span", { "aria-hidden": "true" }, variacao.sentido === "baixa" ? "▼" : "▲"),
            variacao.texto
          )
        : null
    ),
    h(
      "div",
      { class: "cartao-corpo" },
      h("div", {}, h("p", { class: "cartao-valor" }, valor), detalhe ? h("p", { class: "cartao-detalhe" }, detalhe) : null),
      visual || null
    )
  );
}

export function miniBarras(itens, formatar = String) {
  if (!itens.length || itens.every((item) => !item.valor)) {
    return h("div", { class: "mini-barras vazio-mini", "aria-hidden": "true" });
  }

  const maximo = Math.max(...itens.map((item) => item.valor));

  return h(
    "div",
    {
      class: "mini-barras",
      role: "img",
      "aria-label": itens.map((item) => `${item.rotulo}: ${formatar(item.valor)}`).join("; "),
    },
    itens.map((item, indice) =>
      comDica(
        h("span", {
          class: `mini-barra ${indice === itens.length - 1 ? "atual" : ""}`,
          style: { height: `${Math.max((item.valor / maximo) * 100, item.valor ? 6 : 2)}%`, ...(item.cor ? { background: item.cor } : {}) },
        }),
        `${item.rotulo}: ${formatar(item.valor)}`
      )
    )
  );
}

export function anel(partes, centro) {
  const total = partes.reduce((soma, parte) => soma + parte.valor, 0);
  let acumulado = 0;

  const fatias = total
    ? partes
        .filter((parte) => parte.valor > 0)
        .map((parte) => {
          const inicio = (acumulado / total) * 360;
          acumulado += parte.valor;
          const fim = (acumulado / total) * 360;
          return `${parte.cor} ${inicio}deg ${Math.max(inicio, fim - 2)}deg, var(--superficie) ${Math.max(inicio, fim - 2)}deg ${fim}deg`;
        })
        .join(", ")
    : "var(--linha) 0deg 360deg";

  return h(
    "div",
    { class: "anel-bloco" },
    h(
      "div",
      {
        class: "anel",
        role: "img",
        "aria-label": partes.map((parte) => `${parte.nome}: ${parte.valor}`).join("; "),
        style: { background: `conic-gradient(${fatias})` },
      },
      h("span", { class: "anel-centro" }, centro ?? String(total))
    ),
    h(
      "ul",
      { class: "legenda-anel" },
      partes.map((parte) =>
        h(
          "li",
          {},
          h("span", { class: "amostra", style: { background: parte.cor }, "aria-hidden": "true" }),
          h("span", {}, parte.nome),
          h("strong", { class: "numero" }, String(parte.valor))
        )
      )
    )
  );
}

export function progresso(valor, total, rotulo) {
  const percentual = total ? Math.min(100, Math.round((valor / total) * 100)) : 0;

  return h(
    "div",
    { class: "progresso-bloco" },
    h(
      "div",
      {
        class: "progresso",
        role: "progressbar",
        "aria-valuemin": "0",
        "aria-valuemax": "100",
        "aria-valuenow": String(percentual),
        "aria-label": rotulo,
      },
      h("span", { style: { width: `${percentual}%` } })
    ),
    h("span", { class: "progresso-texto numero" }, `${percentual}%`)
  );
}
