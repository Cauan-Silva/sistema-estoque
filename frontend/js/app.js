import { api, obterToken, removerToken } from "./api.js";
import { h, carregando, vazio } from "./ui.js";
import { seletorTema } from "./tema.js";
import { NOMES_PERFIS, definirUsuario, pode } from "./sessao.js";
import { telaUsuarios } from "./telas/usuarios.js";
import { telaAuditoria } from "./telas/auditoria.js";
import { telaEntrar } from "./telas/entrar.js";
import { telaPainel } from "./telas/painel.js";
import { telaProdutos } from "./telas/produtos.js";
import { telaCategorias } from "./telas/categorias.js";
import { telaMovimentacoes } from "./telas/movimentacoes.js";
import { telaFornecedores } from "./telas/fornecedores.js";
import { telaSolicitacoes } from "./telas/solicitacoes.js";
import { telaSolicitacao } from "./telas/solicitacao.js";
import { telaCompras } from "./telas/compras.js";
import { telaRelatorioCompras } from "./telas/relatorio_compras.js";
import { telaFormasPagamento } from "./telas/formas_pagamento.js";

const raiz = document.getElementById("app");

const MENU = [
  {
    grupo: "Estoque",
    itens: [
      { caminho: "#/painel", texto: "Painel", cor: "var(--fibra-azul)" },
      { caminho: "#/produtos", texto: "Produtos", cor: "var(--fibra-azul)" },
      { caminho: "#/categorias", texto: "Categorias", cor: "var(--fibra-azul)" },
      { caminho: "#/movimentacoes", texto: "Movimentações", cor: "var(--fibra-verde)" },
    ],
  },
  {
    grupo: "Compras",
    itens: [
      { caminho: "#/fornecedores", texto: "Fornecedores", cor: "var(--fibra-laranja)" },
      { caminho: "#/formas-pagamento", texto: "Formas de pagamento", cor: "var(--fibra-laranja)" },
      { caminho: "#/solicitacoes", texto: "Solicitações", cor: "var(--fibra-laranja)" },
      { caminho: "#/compras", texto: "Compras", cor: "var(--fibra-marrom)" },
      { caminho: "#/relatorio-compras", texto: "Relatório de compras", cor: "var(--fibra-agua)" },
    ],
  },
];

const ROTAS = [
  { padrao: /^#\/painel$/, tela: telaPainel },
  { padrao: /^#\/produtos$/, tela: telaProdutos },
  { padrao: /^#\/categorias$/, tela: telaCategorias },
  { padrao: /^#\/movimentacoes$/, tela: telaMovimentacoes },
  { padrao: /^#\/fornecedores$/, tela: telaFornecedores },
  { padrao: /^#\/solicitacoes$/, tela: telaSolicitacoes },
  { padrao: /^#\/solicitacoes\/(\d+)$/, tela: telaSolicitacao },
  { padrao: /^#\/compras$/, tela: telaCompras },
  { padrao: /^#\/relatorio-compras$/, tela: telaRelatorioCompras },
  { padrao: /^#\/formas-pagamento$/, tela: telaFormasPagamento },
  { padrao: /^#\/usuarios$/, tela: telaUsuarios, permissao: "usuarios.gerenciar" },
  { padrao: /^#\/auditoria$/, tela: telaAuditoria, permissao: "auditoria.ver" },
];

let usuarioAtual = null;
let estrutura = null;
let areaConteudo = null;

function marcaCabos() {
  return h(
    "span",
    { class: "marca-cabos", "aria-hidden": "true" },
    h("span", { style: { background: "var(--fibra-azul)" } }),
    h("span", { style: { background: "var(--fibra-laranja)" } }),
    h("span", { style: { background: "var(--fibra-verde)" } })
  );
}

function sair() {
  removerToken();
  usuarioAtual = null;
  definirUsuario(null);
  estrutura = null;
  window.location.hash = "#/entrar";
}

function montarEstrutura() {
  const menu = h(
    "nav",
    { class: "menu", "aria-label": "Principal" },
    [
      ...MENU,
      {
        grupo: "Administração",
        itens: [
          { caminho: "#/usuarios", texto: "Usuários", cor: "var(--fibra-ardosia)", permissao: "usuarios.gerenciar" },
          { caminho: "#/auditoria", texto: "Auditoria", cor: "var(--fibra-ardosia)", permissao: "auditoria.ver" },
        ],
      },
    ]
      .map((secao) => ({ ...secao, itens: secao.itens.filter((item) => !item.permissao || pode(item.permissao)) }))
      .filter((secao) => secao.itens.length)
      .map((secao) => [
      h("div", { class: "menu-grupo" }, secao.grupo),
      secao.itens.map((item) =>
        h(
          "a",
          {
            href: item.caminho,
            style: { "--cor-menu": item.cor },
            onClick: () => estrutura.classList.remove("menu-aberto"),
          },
          item.texto
        )
      ),
    ])
  );

  areaConteudo = h("main", { class: "conteudo", id: "conteudo", tabindex: "-1" });

  estrutura = h(
    "div",
    { class: "estrutura" },
    h(
      "div",
      { class: "topo-movel" },
      h("span", { class: "marca" }, marcaCabos(), "Estoque"),
      h(
        "button",
        {
          class: "pequeno",
          "aria-label": "Abrir menu",
          onClick: () => estrutura.classList.toggle("menu-aberto"),
        },
        "Menu"
      )
    ),
    h(
      "aside",
      { class: "lateral" },
      h("div", { class: "marca" }, marcaCabos(), "Estoque e Compras"),
      menu,
      h(
        "div",
        { class: "usuario" },
        h("strong", {}, usuarioAtual.nome),
        h("span", { class: "suave" }, usuarioAtual.email),
        h("span", { class: "perfil-usuario" }, NOMES_PERFIS[usuarioAtual.perfil] || usuarioAtual.perfil),
        h("div", {}, h("button", { class: "pequeno", onClick: sair }, "Sair")),
        seletorTema()
      )
    ),
    areaConteudo
  );

  raiz.replaceChildren(estrutura);
}

function marcarMenu(hash) {
  estrutura.querySelectorAll(".menu a").forEach((link) => {
    const ativo = hash === link.getAttribute("href") || hash.startsWith(`${link.getAttribute("href")}/`);
    if (ativo) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

async function navegar() {
  const hash = window.location.hash || "#/painel";

  if (!obterToken()) {
    usuarioAtual = null;
    estrutura = null;

    if (hash !== "#/entrar") {
      window.location.hash = "#/entrar";
      return;
    }

    telaEntrar(raiz, async () => {
      window.location.hash = "#/painel";
    });
    return;
  }

  if (hash === "#/entrar") {
    window.location.hash = "#/painel";
    return;
  }

  if (!usuarioAtual) {
    raiz.replaceChildren(carregando());

    try {
      usuarioAtual = await api.get("/usuarios/me");
      definirUsuario(usuarioAtual);
    } catch (falha) {
      if (falha.status !== 401) {
        raiz.replaceChildren(
          vazio(falha.message, h("button", { class: "primario", onClick: navegar }, "Tentar de novo"))
        );
      }
      return;
    }
  }

  if (!estrutura) {
    montarEstrutura();
  }

  marcarMenu(hash);

  const rota = ROTAS.find((item) => item.padrao.test(hash));

  if (rota?.permissao && !pode(rota.permissao)) {
    areaConteudo.replaceChildren(
      vazio("Seu perfil não tem acesso a esta página.", h("a", { class: "botao", href: "#/painel" }, "Ir para o painel"))
    );
    return;
  }

  if (!rota) {
    areaConteudo.replaceChildren(
      vazio("Esta página não existe.", h("a", { class: "botao", href: "#/painel" }, "Ir para o painel"))
    );
    return;
  }

  const parametros = hash.match(rota.padrao).slice(1);

  areaConteudo.replaceChildren(carregando());

  try {
    await rota.tela(areaConteudo, ...parametros);
  } catch (falha) {
    areaConteudo.replaceChildren(vazio(falha.message));
  }

  areaConteudo.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", navegar);
navegar();
