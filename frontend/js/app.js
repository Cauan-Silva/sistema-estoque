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

/* Cor de destaque por módulo (tokens --cor-N no CSS). */
function areaDaRota(hash) {
  if (/^#\/(produtos|categorias|movimentacoes)/.test(hash)) return "estoque";
  if (/^#\/(fornecedores|solicitacoes|compras|formas-pagamento)/.test(hash)) return "compras";
  if (/^#\/relatorio-compras/.test(hash)) return "relatorios";
  if (/^#\/(usuarios|auditoria)/.test(hash)) return "admin";
  return "painel";
}

function marca() {
  return h(
    "a",
    { class: "marca", href: "#/painel" },
    h(
      "span",
      { class: "marca-icone", "aria-hidden": "true" },
      h("span", { class: "marca-sol" })
    ),
    h("span", { class: "marca-nome" }, "Estoque", h("em", {}, " & Compras"))
  );
}

function sair() {
  removerToken();
  usuarioAtual = null;
  definirUsuario(null);
  estrutura = null;
  window.location.hash = "#/entrar";
}

function fecharMenus(excecao) {
  estrutura?.querySelectorAll("details[open]").forEach((detalhe) => {
    if (detalhe !== excecao) detalhe.open = false;
  });
}

function montarEstrutura() {
  const secoes = [
    ...MENU,
    {
      grupo: "Administração",
      itens: [
        { caminho: "#/usuarios", texto: "Usuários", permissao: "usuarios.gerenciar" },
        { caminho: "#/auditoria", texto: "Auditoria", permissao: "auditoria.ver" },
      ],
    },
  ]
    .map((secao) => ({ ...secao, itens: secao.itens.filter((item) => !item.permissao || pode(item.permissao)) }))
    .filter((secao) => secao.itens.length);

  const aoNavegar = () => {
    fecharMenus();
    estrutura.classList.remove("menu-aberto");
  };

  const grupo = (titulo, conteudo, classe = "") => {
    const detalhe = h(
      "details",
      { class: `grupo-menu ${classe}` },
      h("summary", {}, titulo),
      h("div", { class: "painel-menu" }, conteudo)
    );

    detalhe.addEventListener("toggle", () => {
      if (detalhe.open) fecharMenus(detalhe);
    });

    return detalhe;
  };

  const menu = h(
    "nav",
    { class: "menu", id: "menu-principal", "aria-label": "Principal" },
    h("a", { class: "link-menu", href: "#/painel", onClick: aoNavegar }, "Painel"),
    secoes.map((secao) =>
      grupo(
        secao.grupo,
        secao.itens.map((item) => h("a", { href: item.caminho, onClick: aoNavegar }, item.texto))
      )
    )
  );

  const conta = grupo(
    h(
      "span",
      { class: "conta-resumo" },
      h("span", { class: "conta-inicial", "aria-hidden": "true" }, usuarioAtual.nome.trim().charAt(0).toUpperCase()),
      h("span", { class: "conta-nome" }, usuarioAtual.nome)
    ),
    [
      h("strong", {}, usuarioAtual.nome),
      h("span", { class: "suave" }, usuarioAtual.email),
      h("span", { class: "perfil-usuario" }, NOMES_PERFIS[usuarioAtual.perfil] || usuarioAtual.perfil),
      h("span", { class: "rotulo-tema" }, "Tema"),
      seletorTema(),
      h("button", { class: "sair", onClick: sair }, "Sair"),
    ],
    "conta"
  );

  const botaoMenu = h(
    "button",
    {
      class: "botao-menu",
      "aria-controls": "menu-principal",
      "aria-expanded": "false",
      onClick: () => {
        const aberto = estrutura.classList.toggle("menu-aberto");
        botaoMenu.setAttribute("aria-expanded", String(aberto));
      },
    },
    "Menu"
  );

  areaConteudo = h("main", { class: "conteudo", id: "conteudo", tabindex: "-1" });

  estrutura = h(
    "div",
    { class: "estrutura" },
    h("a", { class: "pular", href: "#conteudo", onClick: (e) => { e.preventDefault(); areaConteudo.focus(); } }, "Pular para o conteúdo"),
    h("header", { class: "barra-topo" }, marca(), menu, h("div", { class: "barra-direita" }, conta, botaoMenu)),
    areaConteudo
  );

  document.addEventListener("click", (evento) => {
    if (estrutura && !evento.target.closest(".grupo-menu")) fecharMenus();
  });

  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") fecharMenus();
  });

  raiz.replaceChildren(estrutura);
}

function marcarMenu(hash) {
  estrutura.querySelectorAll(".menu .grupo-menu").forEach((grupo) => {
    let algumAtivo = false;

    grupo.querySelectorAll("a").forEach((link) => {
      const ativo = hash === link.getAttribute("href") || hash.startsWith(`${link.getAttribute("href")}/`);
      algumAtivo ||= ativo;

      if (ativo) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });

    grupo.classList.toggle("ativo", algumAtivo);
  });

  estrutura.querySelectorAll(".menu > a").forEach((link) => {
    if (hash === link.getAttribute("href")) {
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

  areaConteudo.dataset.area = areaDaRota(hash);
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
