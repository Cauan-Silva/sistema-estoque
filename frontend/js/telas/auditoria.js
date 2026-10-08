import { api, montarQuery } from "../api.js";
import { cabecalho, campoFiltro, executar, formatar, h, paginacao, seletor, tabela } from "../ui.js";

const TAMANHO = 50;

const NOMES_METODOS = {
  POST: "Criação",
  PUT: "Alteração",
  PATCH: "Alteração",
  DELETE: "Exclusão",
};

function situacao(status) {
  if (status < 400) return h("span", { class: "status", dataset: { cor: "verde" } }, `${status} OK`);
  if (status === 401 || status === 403) return h("span", { class: "status", dataset: { cor: "laranja" } }, `${status} Negado`);
  if (status >= 500) return h("span", { class: "status", dataset: { cor: "vermelho" } }, `${status} Erro`);
  return h("span", { class: "status", dataset: { cor: "amarelo" } }, `${status} Recusado`);
}

export async function telaAuditoria(area) {
  const usuarios = await api.get("/usuarios");
  const filtros = { usuario_id: "", metodo: "", somente_falhas: false, data_inicio: "", data_fim: "", pagina: 1 };
  const lista = h("div");
  const total = h("p", { class: "suave" });

  async function carregar() {
    const dados = await executar(() =>
      api.get(`/auditoria${montarQuery({ ...filtros, tamanho: TAMANHO })}`)
    );

    if (!dados) return;

    total.textContent = `${formatar.numero(dados.total)} registro${dados.total === 1 ? "" : "s"}.`;

    lista.replaceChildren(
      tabela(
        [
          { titulo: "Data", classe: "numero", valor: (r) => formatar.dataHora(r.data_hora) },
          { titulo: "Usuário", valor: (r) => r.usuario || h("span", { class: "suave" }, "Sem login") },
          { titulo: "Ação", valor: (r) => `${NOMES_METODOS[r.metodo] || r.metodo} (${r.metodo})` },
          { titulo: "Endereço", valor: (r) => h("code", {}, r.caminho) },
          { titulo: "Resultado", valor: (r) => situacao(r.status) },
          { titulo: "Tempo", classe: "direita numero", valor: (r) => `${formatar.numero(r.duracao_ms)} ms` },
          { titulo: "Código", valor: (r) => h("code", { class: "suave" }, r.id_requisicao) },
        ],
        dados.itens,
        { vazio: "Nenhuma ação registrada com esses filtros." }
      ),
      paginacao(filtros.pagina, dados.itens.length, TAMANHO, (pagina) => {
        filtros.pagina = pagina;
        carregar();
      })
    );
  }

  function aoFiltrar(chave) {
    return (evento) => {
      filtros[chave] = evento.target.type === "checkbox" ? evento.target.checked : evento.target.value;
      filtros.pagina = 1;
      carregar();
    };
  }

  area.replaceChildren(
    cabecalho(
      "Auditoria",
      "Todas as criações, alterações e exclusões feitas no sistema, com quem fez e o resultado. Consultas não são registradas."
    ),
    h(
      "div",
      { class: "filtros" },
      campoFiltro("Usuário", seletor([["", "Todos"], ...usuarios.map((u) => [u.id, u.nome])], "", { onChange: aoFiltrar("usuario_id") })),
      campoFiltro(
        "Ação",
        seletor(
          [
            ["", "Todas"],
            ["POST", "Criação"],
            ["PUT", "Alteração (PUT)"],
            ["PATCH", "Alteração (PATCH)"],
            ["DELETE", "Exclusão"],
          ],
          "",
          { onChange: aoFiltrar("metodo") }
        )
      ),
      campoFiltro("De", h("input", { type: "date", onChange: aoFiltrar("data_inicio") })),
      campoFiltro("Até", h("input", { type: "date", onChange: aoFiltrar("data_fim") })),
      h("label", { class: "marcador" }, h("input", { type: "checkbox", onChange: aoFiltrar("somente_falhas") }), "Só falhas e acessos negados")
    ),
    lista,
    total
  );

  await carregar();
}
