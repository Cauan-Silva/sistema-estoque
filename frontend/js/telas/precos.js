import { api, montarQuery } from "../api.js";
import { abrirDialogo, executar, formatar, h, tabela } from "../ui.js";

function bloco(titulo, ...conteudo) {
  return h("section", { class: "bloco-precos" }, h("h3", {}, titulo), conteudo);
}

function resumoHistorico(dados) {
  const r = dados.resumo;

  const item = (rotulo, valor) => h("div", {}, h("dt", {}, rotulo), h("dd", { class: "numero" }, formatar.moeda(valor)));

  return h(
    "dl",
    { class: "ficha" },
    item("Último pago", r.ultimo_pago),
    item("Média paga", r.media_paga),
    item("Menor pago", r.menor_pago),
    item("Maior pago", r.maior_pago),
    item("Preço no cadastro", dados.produto.preco_cadastro)
  );
}

function fonteExterna(fonte) {
  if (fonte.situacao !== "ok") {
    return h("p", { class: fonte.situacao === "erro" ? "erro" : "suave" }, `${fonte.fonte}: ${fonte.mensagem}`);
  }

  return [
    fonte.resumo
      ? h(
          "p",
          {},
          `${fonte.fonte}, busca "${fonte.termo}": de ${formatar.moeda(fonte.resumo.menor)} a ${formatar.moeda(fonte.resumo.maior)}, mediana ${formatar.moeda(fonte.resumo.mediana)} em ${fonte.resumo.quantidade} ofertas.`
        )
      : h("p", { class: "suave" }, `${fonte.fonte}: ${fonte.mensagem || "nenhuma oferta em reais."}`),
    tabela(
      [
        {
          titulo: "Oferta",
          valor: (o) => (o.link ? h("a", { href: o.link, target: "_blank", rel: "noopener noreferrer" }, o.titulo) : o.titulo),
        },
        { titulo: "Condição", valor: (o) => o.condicao || "—" },
        { titulo: "Vendedor", valor: (o) => o.vendedor || "—" },
        {
          titulo: "Preço",
          classe: "direita numero",
          valor: (o) => (o.moeda === "BRL" ? formatar.moeda(o.preco) : `${o.moeda} ${formatar.numero(o.preco)}`),
        },
      ],
      fonte.ofertas,
      { vazio: "Nenhuma oferta encontrada." }
    ),
  ];
}

export function abrirConsultaPrecos(produto) {
  const conteudo = h("div", { class: "consulta-precos" }, h("p", { class: "suave" }, "Consultando preços…"));
  const busca = h("input", { type: "search", value: produto.nome, minlength: "2", maxlength: "120", "aria-label": "Termo de busca" });

  async function carregar() {
    conteudo.replaceChildren(h("p", { class: "suave" }, "Consultando preços…"));

    const dados = await executar(() =>
      api.get(`/precos/produtos/${produto.id}${montarQuery({ busca: busca.value.trim() })}`)
    );

    if (!dados) {
      conteudo.replaceChildren(h("p", { class: "erro" }, "Não foi possível consultar os preços."));
      return;
    }

    conteudo.replaceChildren(
      bloco("O que já pagamos", resumoHistorico(dados)),
      bloco(
        "Últimas compras",
        tabela(
          [
            { titulo: "Data", classe: "numero", valor: (c) => formatar.data(c.data) },
            { titulo: "Fornecedor", valor: (c) => c.fornecedor },
            { titulo: "Quantidade", classe: "direita numero", valor: (c) => formatar.numero(c.quantidade) },
            { titulo: "Preço", classe: "direita numero", valor: (c) => formatar.moeda(c.preco_unitario) },
          ],
          dados.compras,
          { vazio: "Este produto ainda não foi comprado pelo sistema." }
        )
      ),
      bloco(
        "Últimas cotações",
        tabela(
          [
            { titulo: "Data", classe: "numero", valor: (c) => formatar.data(c.data) },
            { titulo: "Fornecedor", valor: (c) => c.fornecedor },
            { titulo: "Preço", classe: "direita numero", valor: (c) => formatar.moeda(c.preco_unitario) },
          ],
          dados.cotacoes,
          { vazio: "Nenhuma cotação registrada para este produto." }
        )
      ),
      bloco("Preços de mercado", dados.externas.map(fonteExterna))
    );
  }

  const dialogo = abrirDialogo({
    titulo: `Preços de ${produto.nome}`,
    descricao: "Referências para negociar: o histórico interno e ofertas encontradas em fontes externas.",
    conteudo: [
      h(
        "div",
        { class: "linha-busca" },
        h("label", {}, "Buscar no mercado por", busca),
        h("button", { type: "button", class: "pequeno", onClick: carregar }, "Buscar de novo")
      ),
      conteudo,
    ],
    textoAcao: "Fechar",
    aoEnviar: async () => {},
  });

  dialogo.classList.add("dialogo-largo");
  dialogo.querySelector(".rodape button[type=button]").hidden = true;

  busca.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter") {
      evento.preventDefault();
      carregar();
    }
  });

  carregar();
}

/* Texto curto com o histórico do produto, usado ao lado do campo de preço da cotação. */
export async function referenciaPreco(produtoId) {
  try {
    const dados = await api.get(`/precos/produtos/${produtoId}?externas=false&limite=1`);
    const r = dados.resumo;

    if (!r.compras) return "Ainda não comprado pelo sistema.";

    return `Último pago ${formatar.moeda(r.ultimo_pago)}, média ${formatar.moeda(r.media_paga)}.`;
  } catch {
    return "";
  }
}
