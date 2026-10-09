import { api, montarQuery } from "../api.js";
import { pode } from "../sessao.js";
import { abrirConsultaPrecos } from "./precos.js";
import {
  abrirFormulario,
  botoesExportar,
  cabecalho,
  campoFiltro,
  confirmar,
  executar,
  formatar,
  h,
  paginacao,
  seletor,
  tabela,
} from "../ui.js";

const TAMANHO = 20;

export async function telaProdutos(area) {
  const podeEditar = pode("estoque.editar");
  const [categorias, fornecedores] = await Promise.all([
    api.get("/categorias"),
    api.get("/fornecedores"),
  ]);

  const filtros = { busca: "", categoria_id: "", fornecedor_id: "", estoque_baixo: false, pagina: 1 };
  const lista = h("div");

  const opcoesCategoria = categorias.map((c) => [c.id, c.nome]);
  const opcoesFornecedor = fornecedores.map((f) => [f.id, f.ativo ? f.nome : `${f.nome} (inativo)`]);

  function campos(produto = {}) {
    return [
      { nome: "nome", rotulo: "Nome", obrigatorio: true, minimo: 2, maximo: 150, valor: produto.nome },
      {
        nome: "categoria_id",
        rotulo: "Categoria",
        tipo: "select",
        numero: true,
        obrigatorio: true,
        opcoes: [["", "Escolha uma categoria"], ...opcoesCategoria],
        valor: produto.categoria_id,
      },
      [
        {
          nome: "quantidade",
          rotulo: "Quantidade",
          tipo: "number",
          min: 0,
          passo: 1,
          obrigatorio: true,
          valor: produto.quantidade ?? 0,
        },
        {
          nome: "preco",
          rotulo: "Preço (R$)",
          tipo: "number",
          min: 0,
          passo: "0.01",
          obrigatorio: true,
          valor: produto.preco,
        },
        {
          nome: "estoque_minimo",
          rotulo: "Estoque mínimo (0 = compra avulsa, sem reposição)",
          tipo: "number",
          min: 0,
          passo: 1,
          obrigatorio: true,
          valor: produto.estoque_minimo ?? 5,
        },
      ],
      {
        nome: "fornecedor_id",
        rotulo: "Fornecedor",
        tipo: "select",
        numero: true,
        opcoes: [
          ["", "Sem fornecedor"],
          ...fornecedores
            .filter((f) => f.ativo || f.id === produto.fornecedor_id)
            .map((f) => [f.id, f.ativo ? f.nome : `${f.nome} (inativo)`]),
        ],
        valor: produto.fornecedor_id,
      },
    ];
  }

  function novoProduto() {
    if (!categorias.length) {
      confirmar({
        titulo: "Cadastre uma categoria primeiro",
        mensagem: "Todo produto precisa de uma categoria. Crie uma na tela de categorias.",
        textoAcao: "Entendi",
      });
      return;
    }

    abrirFormulario({
      titulo: "Novo produto",
      campos: campos(),
      textoAcao: "Cadastrar produto",
      aoEnviar: async (dados) => {
        await api.post("/produtos", dados);
        carregar();
      },
    });
  }

  function editar(produto) {
    abrirFormulario({
      titulo: `Editar ${produto.nome}`,
      campos: campos(produto),
      textoAcao: "Salvar alterações",
      aoEnviar: async (dados) => {
        await api.put(`/produtos/${produto.id}`, dados);
        carregar();
      },
    });
  }

  function movimentar(produto, tipo) {
    abrirFormulario({
      titulo: tipo === "ENTRADA" ? "Registrar entrada" : "Registrar saída",
      descricao: `${produto.nome}: ${formatar.numero(produto.quantidade)} em estoque.`,
      campos: [
        {
          nome: "quantidade",
          rotulo: "Quantidade",
          tipo: "number",
          min: 1,
          max: tipo === "SAIDA" ? produto.quantidade : undefined,
          passo: 1,
          obrigatorio: true,
        },
      ],
      textoAcao: tipo === "ENTRADA" ? "Registrar entrada" : "Registrar saída",
      aoEnviar: async (dados) => {
        await api.post("/movimentacoes", { produto_id: produto.id, tipo, quantidade: dados.quantidade });
        carregar();
      },
    });
  }

  async function excluir(produto) {
    const ok = await confirmar({
      titulo: "Excluir produto",
      mensagem: `${produto.nome} e o histórico de movimentações dele serão excluídos.`,
      textoAcao: "Excluir produto",
      perigo: true,
    });

    if (ok) {
      await executar(() => api.delete(`/produtos/${produto.id}`), "Produto excluído.");
      carregar();
    }
  }

  async function carregar() {
    const produtos = await executar(() =>
      api.get(
        `/produtos${montarQuery({
          busca: filtros.busca,
          categoria_id: filtros.categoria_id,
          fornecedor_id: filtros.fornecedor_id,
          estoque_baixo: filtros.estoque_baixo,
          pagina: filtros.pagina,
          tamanho: TAMANHO,
        })}`
      )
    );

    if (!produtos) return;

    lista.replaceChildren(
      tabela(
        [
          { titulo: "Produto", valor: (p) => p.nome },
          { titulo: "Categoria", valor: (p) => p.categoria },
          { titulo: "Fornecedor", valor: (p) => p.fornecedor || h("span", { class: "suave" }, "—") },
          {
            titulo: "Quantidade",
            classe: "direita numero",
            valor: (p) =>
              p.quantidade <= p.estoque_minimo
                ? h("span", { class: "abaixo-minimo", title: "No estoque mínimo ou abaixo" }, formatar.numero(p.quantidade))
                : formatar.numero(p.quantidade),
          },
          { titulo: "Mínimo", classe: "direita numero", valor: (p) => formatar.numero(p.estoque_minimo) },
          { titulo: "Preço", classe: "direita numero", valor: (p) => formatar.moeda(p.preco) },
          {
            titulo: h("span", { class: "oculto-visualmente" }, "Ações"),
            classe: "acoes",
            valor: (p) => [
              h("button", { class: "pequeno", onClick: () => abrirConsultaPrecos(p) }, "Preços"),
              ...(!podeEditar ? [] : [
              h("button", { class: "pequeno", onClick: () => movimentar(p, "ENTRADA") }, "Entrada"),
              h(
                "button",
                { class: "pequeno", disabled: p.quantidade === 0, onClick: () => movimentar(p, "SAIDA") },
                "Saída"
              ),
              h("button", { class: "pequeno", onClick: () => editar(p) }, "Editar"),
              h("button", { class: "pequeno perigo", onClick: () => excluir(p) }, "Excluir"),
              ]),
            ],
          },
        ],
        produtos,
        {
          vazio: filtros.busca || filtros.categoria_id || filtros.fornecedor_id || filtros.estoque_baixo
            ? "Nenhum produto encontrado com esses filtros."
            : "Nenhum produto cadastrado.",
          acaoVazio: podeEditar ? h("button", { class: "primario", onClick: novoProduto }, "Cadastrar produto") : null,
        }
      ),
      paginacao(filtros.pagina, produtos.length, TAMANHO, (pagina) => {
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

  let espera;
  const busca = h("input", {
    type: "search",
    placeholder: "Nome do produto",
    onInput: (evento) => {
      clearTimeout(espera);
      espera = setTimeout(() => aoFiltrar("busca")(evento), 300);
    },
  });

  area.replaceChildren(
    cabecalho(
      "Produtos",
      "Cadastro de produtos e registro rápido de entradas e saídas.",
      botoesExportar("/exportacoes/produtos", () => ({
        busca: filtros.busca,
        categoria_id: filtros.categoria_id,
        fornecedor_id: filtros.fornecedor_id,
        estoque_baixo: filtros.estoque_baixo,
      })),
      podeEditar ? h("button", { class: "primario", onClick: novoProduto }, "Cadastrar produto") : null
    ),
    h(
      "div",
      { class: "filtros" },
      campoFiltro("Buscar", busca),
      campoFiltro(
        "Categoria",
        seletor([["", "Todas"], ...opcoesCategoria], "", { onChange: aoFiltrar("categoria_id") })
      ),
      campoFiltro(
        "Fornecedor",
        seletor([["", "Todos"], ...opcoesFornecedor], "", { onChange: aoFiltrar("fornecedor_id") })
      ),
      h(
        "label",
        { class: "marcador" },
        h("input", { type: "checkbox", onChange: aoFiltrar("estoque_baixo") }),
        "Só estoque baixo (no mínimo ou abaixo)"
      )
    ),
    lista
  );

  await carregar();
}
