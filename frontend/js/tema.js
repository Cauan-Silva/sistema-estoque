import { h } from "./ui.js";

const CHAVE_TEMA = "estoque.tema";
const OPCOES = [
  ["auto", "Automático"],
  ["claro", "Claro"],
  ["escuro", "Escuro"],
];

export function temaSalvo() {
  try {
    return localStorage.getItem(CHAVE_TEMA) || "auto";
  } catch {
    return "auto";
  }
}

export function aplicarTema(tema) {
  if (tema === "claro" || tema === "escuro") {
    document.documentElement.dataset.tema = tema;
  } else {
    delete document.documentElement.dataset.tema;
  }

  try {
    localStorage.setItem(CHAVE_TEMA, tema);
  } catch {
    /* sem armazenamento: vale só nesta sessão */
  }
}

export function seletorTema() {
  const grupo = h("div", { class: "tema", role: "group", "aria-label": "Tema" });

  function desenhar() {
    const atual = temaSalvo();

    grupo.replaceChildren(
      ...OPCOES.map(([valor, texto]) =>
        h(
          "button",
          {
            type: "button",
            "aria-pressed": String(valor === atual),
            onClick: () => {
              aplicarTema(valor);
              desenhar();
            },
          },
          texto
        )
      )
    );
  }

  desenhar();
  return grupo;
}
