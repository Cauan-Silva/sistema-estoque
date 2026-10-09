import { api } from "./api.js";
import { icone } from "./icones.js";
import { h } from "./ui.js";

/*
 * Sino de notificações na barra do topo. As pendências vêm prontas da API
 * (GET /notificacoes) e somem quando alguém age; a lista é atualizada a cada
 * minuto e a cada troca de tela.
 */

const INTERVALO = 60000;

const ROTULOS = {
  repor: "Repor",
  receber: "Receber",
  aprovar: "Aprovar",
  comprar: "Comprar",
  cotar: "Cotar",
};

let contador;
let lista;
let temporizador;

function desenhar(resposta) {
  const dados = { total: Number(resposta?.total) || 0, itens: Array.isArray(resposta?.itens) ? resposta.itens : [] };
  const total = dados.total;
  contador.textContent = total > 99 ? "99+" : String(total);
  contador.hidden = total === 0;
  contador.parentElement.setAttribute("aria-label", total ? `Notificações: ${total} pendência(s)` : "Notificações: nada pendente");

  lista.replaceChildren(
    ...(dados.itens.length
      ? dados.itens.map((item) =>
          h(
            "a",
            { class: `notificacao ${item.urgente ? "urgente" : ""}`, href: item.link, dataset: { tipo: item.tipo } },
            h("span", { class: "notificacao-tipo" }, ROTULOS[item.tipo] || item.tipo),
            h("strong", {}, item.titulo),
            h("span", { class: "notificacao-descricao" }, item.descricao)
          )
        )
      : [h("p", { class: "notificacoes-vazio" }, "Nada pendente para você agora.")])
  );
}

export async function atualizarNotificacoes() {
  if (!lista) return;
  try {
    desenhar(await api.get("/notificacoes"));
  } catch {
    /* sem conexão: mantém o que já estava na tela */
  }
}

export function sinoNotificacoes(grupo, aoNavegar) {
  contador = h("span", { class: "contador-notificacoes", hidden: true });
  lista = h("div", { class: "lista-notificacoes", onClick: (evento) => evento.target.closest("a") && aoNavegar() });

  const sino = grupo(
    h("span", { class: "sino", "aria-label": "Notificações" }, icone("sino"), contador),
    [h("div", { class: "notificacoes-topo" }, h("strong", {}, "Pendências"), h("span", { class: "suave" }, "o que precisa da sua ação")), lista],
    "notificacoes"
  );

  sino.addEventListener("toggle", () => {
    if (sino.open) atualizarNotificacoes();
  });

  clearInterval(temporizador);
  temporizador = setInterval(() => {
    if (!document.hidden) atualizarNotificacoes();
  }, INTERVALO);

  atualizarNotificacoes();
  return sino;
}

export function pararNotificacoes() {
  clearInterval(temporizador);
  lista = null;
}
