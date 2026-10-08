import { api } from "../api.js";
import { NOMES_PERFIS, usuario } from "../sessao.js";
import { avisar, cabecalho, confirmar, etiquetaStatus, executar, formatar, h, seletor, tabela } from "../ui.js";

const DESCRICOES = [
  ["Administrador", "Faz tudo, inclusive gerenciar usuários e ver a auditoria."],
  ["Comprador", "Cria solicitações, registra cotações e compras, cadastra fornecedores e formas de pagamento."],
  ["Aprovador", "Aprova ou reprova solicitações criadas por outras pessoas."],
  ["Almoxarife", "Cuida de produtos, categorias e movimentações, cria solicitações e registra recebimentos."],
  ["Consulta", "Vê todas as telas e exporta relatórios, sem alterar nada."],
];

export async function telaUsuarios(area) {
  const lista = h("div");
  const eu = usuario();

  async function alterarPerfil(pessoa, evento) {
    const perfil = evento.target.value;
    const atualizado = await executar(
      () => api.patch(`/usuarios/${pessoa.id}`, { perfil }),
      `${pessoa.nome} agora é ${NOMES_PERFIS[perfil]}.`
    );

    if (!atualizado) {
      evento.target.value = pessoa.perfil;
      return;
    }

    pessoa.perfil = atualizado.perfil;
  }

  async function alternarAtivo(pessoa) {
    const ativar = !pessoa.ativo;

    const ok = await confirmar({
      titulo: ativar ? "Reativar usuário" : "Desativar usuário",
      mensagem: ativar
        ? `${pessoa.nome} volta a conseguir entrar no sistema.`
        : `${pessoa.nome} não conseguirá mais entrar. O histórico continua salvo.`,
      textoAcao: ativar ? "Reativar" : "Desativar",
      perigo: !ativar,
    });

    if (ok) {
      await executar(
        () => api.patch(`/usuarios/${pessoa.id}`, { ativo: ativar }),
        ativar ? "Usuário reativado." : "Usuário desativado."
      );
      carregar();
    }
  }

  async function carregar() {
    const usuarios = await executar(() => api.get("/usuarios"));
    if (!usuarios) return;

    lista.replaceChildren(
      tabela(
        [
          {
            titulo: "Usuário",
            valor: (u) => [u.nome, u.id === eu?.id ? h("span", { class: "etiqueta" }, "Você") : null],
          },
          { titulo: "E-mail", valor: (u) => u.email },
          {
            titulo: "Perfil",
            valor: (u) =>
              seletor(Object.entries(NOMES_PERFIS), u.perfil, {
                "aria-label": `Perfil de ${u.nome}`,
                disabled: u.id === eu?.id,
                title: u.id === eu?.id ? "Peça a outro administrador para alterar o seu perfil." : undefined,
                onChange: (evento) => alterarPerfil(u, evento),
              }),
          },
          { titulo: "Situação", valor: (u) => etiquetaStatus(u.ativo ? "ATIVO" : "INATIVO") },
          { titulo: "Desde", classe: "numero", valor: (u) => formatar.data(u.data_criacao) },
          {
            titulo: h("span", { class: "oculto-visualmente" }, "Ações"),
            classe: "acoes",
            valor: (u) =>
              u.id === eu?.id
                ? null
                : h(
                    "button",
                    { class: `pequeno ${u.ativo ? "perigo" : ""}`, onClick: () => alternarAtivo(u) },
                    u.ativo ? "Desativar" : "Reativar"
                  ),
          },
        ],
        usuarios,
        { vazio: "Nenhum usuário cadastrado." }
      )
    );
  }

  area.replaceChildren(
    cabecalho(
      "Usuários",
      "Defina o perfil de cada pessoa. Quem cria uma conta nova entra como Consulta até receber um perfil."
    ),
    lista,
    h(
      "section",
      { class: "secao perfis" },
      h("h2", {}, "O que cada perfil pode fazer"),
      h(
        "dl",
        { class: "ficha" },
        DESCRICOES.map(([nome, descricao]) => h("div", { class: "larga" }, h("dt", {}, nome), h("dd", {}, descricao)))
      ),
      h("p", { class: "suave" }, "Ninguém pode aprovar ou reprovar uma solicitação que criou.")
    )
  );

  await carregar();
  if (!eu) avisar("Não foi possível identificar o usuário atual.", "erro");
}
