import { api, listarTodos, montarQuery } from "../api.js";
import {
  abrirFormulario,
  cabecalho,
  campoFiltro,
  etiquetaStatus,
  executar,
  formatar,
  h,
  paginacao,
  seletor,
  tabela,
} from "../ui.js";

const TAMANHO = 20;

export async function telaMovimentacoes(area) {
  const produtos = await listarTodos("/produtos");
  const opcoesProduto = produtos.map((p) => [p.id, p.nome]);

  const filtros = { produto_id: "", tipo: "", data_inicio: "", data_fim: "", pagina: 1 };
  const lista = h("div");

  function novaMovimentacao() {
    abrirFormulario({
      titulo: "Registrar movimentação",
      campos: [
        {
          nome: "produto_id",
          rotulo: "Produto",
          tipo: "select",
          numero: true,
          obrigatorio: true,
          opcoes: [["", "Escolha um produto"], ...opcoesProduto],
        },
        [
          {
            nome: "tipo",
            rotulo: "Tipo",
            tipo: "select",
            obrigatorio: true,
            opcoes: [
              ["ENTRADA", "Entrada"],
              ["SAIDA", "Saída"],
            ],
          },
          { nome: "quantidade", rotulo: "Quantidade", tipo: "number", min: 1, passo: 1, obrigatorio: true },
        ],
      ],
      textoAcao: "Registrar movimentação",
      aoEnviar: async (dados) => {
        await api.post("/movimentacoes", dados);
        carregar();
      },
    });
  }

  async function carregar() {
    const movimentacoes = await executar(() =>
      api.get(
        `/movimentacoes${montarQuery({
          produto_id: filtros.produto_id,
          tipo: filtros.tipo,
          data_inicio: filtros.data_inicio ? `${filtros.data_inicio}T00:00:00` : "",
          data_fim: filtros.data_fim ? `${filtros.data_fim}T23:59:59` : "",
          pagina: filtros.pagina,
          tamanho: TAMANHO,
        })}`
      )
    );

    if (!movimentacoes) return;

    lista.replaceChildren(
      tabela(
        [
          { titulo: "Data", classe: "numero", valor: (m) => formatar.dataHora(m.data_movimentacao) },
          { titulo: "Produto", valor: (m) => m.produto_nome },
          { titulo: "Tipo", valor: (m) => etiquetaStatus(m.tipo) },
          {
            titulo: "Origem",
            valor: (m) =>
              m.recebimento_id
                ? `Recebimento Nº ${m.recebimento_id}`
                : h("span", { class: "suave" }, "Manual"),
          },
          {
            titulo: "Quantidade",
            classe: "direita numero",
            valor: (m) => `${m.tipo === "SAIDA" ? "−" : "+"}${formatar.numero(m.quantidade)}`,
          },
        ],
        movimentacoes,
        {
          vazio: "Nenhuma movimentação encontrada.",
          acaoVazio: produtos.length
            ? h("button", { class: "primario", onClick: novaMovimentacao }, "Registrar movimentação")
            : null,
        }
      ),
      paginacao(filtros.pagina, movimentacoes.length, TAMANHO, (pagina) => {
        filtros.pagina = pagina;
        carregar();
      })
    );
  }

  function aoFiltrar(chave) {
    return (evento) => {
      filtros[chave] = evento.target.value;
      filtros.pagina = 1;
      carregar();
    };
  }

  area.replaceChildren(
    cabecalho(
      "Movimentações",
      "Histórico de entradas e saídas. Cada registro atualiza a quantidade do produto.",
      h(
        "button",
        { class: "primario", disabled: !produtos.length, onClick: novaMovimentacao },
        "Registrar movimentação"
      )
    ),
    h(
      "div",
      { class: "filtros" },
      campoFiltro(
        "Produto",
        seletor([["", "Todos"], ...opcoesProduto], "", { onChange: aoFiltrar("produto_id") })
      ),
      campoFiltro(
        "Tipo",
        seletor(
          [
            ["", "Todos"],
            ["ENTRADA", "Entradas"],
            ["SAIDA", "Saídas"],
          ],
          "",
          { onChange: aoFiltrar("tipo") }
        )
      ),
      campoFiltro("De", h("input", { type: "date", onChange: aoFiltrar("data_inicio") })),
      campoFiltro("Até", h("input", { type: "date", onChange: aoFiltrar("data_fim") }))
    ),
    lista
  );

  await carregar();
}
