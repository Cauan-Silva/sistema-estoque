import { api } from "../api.js";
import { abrirFormulario, cabecalho, confirmar, executar, h, tabela } from "../ui.js";

export async function telaCategorias(area) {
  const lista = h("div");

  function formulario(categoria) {
    abrirFormulario({
      titulo: categoria ? `Renomear ${categoria.nome}` : "Nova categoria",
      campos: [
        { nome: "nome", rotulo: "Nome", obrigatorio: true, minimo: 2, maximo: 100, valor: categoria?.nome },
      ],
      textoAcao: categoria ? "Salvar nome" : "Criar categoria",
      aoEnviar: async (dados) => {
        if (categoria) {
          await api.put(`/categorias/${categoria.id}`, dados);
        } else {
          await api.post("/categorias", dados);
        }
        carregar();
      },
    });
  }

  async function excluir(categoria) {
    const ok = await confirmar({
      titulo: "Excluir categoria",
      mensagem: `A categoria ${categoria.nome} será excluída. Categorias com produtos não podem ser excluídas.`,
      textoAcao: "Excluir categoria",
      perigo: true,
    });

    if (ok) {
      await executar(() => api.delete(`/categorias/${categoria.id}`), "Categoria excluída.");
      carregar();
    }
  }

  async function carregar() {
    const categorias = await executar(() => api.get("/categorias"));
    if (!categorias) return;

    lista.replaceChildren(
      tabela(
        [
          { titulo: "Categoria", valor: (c) => c.nome },
          {
            titulo: h("span", { class: "oculto-visualmente" }, "Ações"),
            classe: "acoes",
            valor: (c) => [
              h("button", { class: "pequeno", onClick: () => formulario(c) }, "Renomear"),
              h("button", { class: "pequeno perigo", onClick: () => excluir(c) }, "Excluir"),
            ],
          },
        ],
        categorias,
        {
          vazio: "Nenhuma categoria cadastrada.",
          acaoVazio: h("button", { class: "primario", onClick: () => formulario() }, "Criar categoria"),
        }
      )
    );
  }

  area.replaceChildren(
    cabecalho(
      "Categorias",
      "Agrupe os produtos por tipo para filtrar e organizar o estoque.",
      h("button", { class: "primario", onClick: () => formulario() }, "Criar categoria")
    ),
    lista
  );

  await carregar();
}
