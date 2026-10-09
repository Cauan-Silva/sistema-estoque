import { api, montarQuery } from "../api.js";
import { pode } from "../sessao.js";
import { abrirDialogo, avisar, executar, formatar, h, tabela } from "../ui.js";

function linkMercadoLivre(termo) {
  return `https://lista.mercadolivre.com.br/${encodeURIComponent(termo.trim().replace(/\s+/g, "-"))}`;
}

function linkGoogleShopping(termo) {
  return `https://www.google.com/search?tbm=shop&q=${encodeURIComponent(termo.trim())}`;
}

function precoReferencia(valor) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(valor);
}

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
    return null;
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
      blocoMercado(dados)
    );
  }

  function blocoMercado(dados) {
    const termo = busca.value.trim() || produto.nome;
    const automaticas = dados.externas.map(fonteExterna).filter(Boolean);

    const atalhos = h(
      "div",
      { class: "atalhos-mercado" },
      h(
        "a",
        { class: "botao", href: linkMercadoLivre(termo), target: "_blank", rel: "noopener noreferrer" },
        `Ver "${termo}" no Mercado Livre ↗`
      ),
      h(
        "a",
        { class: "botao", href: linkGoogleShopping(termo), target: "_blank", rel: "noopener noreferrer" },
        "Google Shopping ↗"
      )
    );

    const valor = h("input", { type: "number", min: 0, step: "0.01", placeholder: "0,00" });
    const fonte = h("input", { value: "Mercado Livre", maxlength: 60 });
    const link = h("input", { type: "url", maxlength: 500, placeholder: "Cole o link do anúncio (opcional)" });
    const observacao = h("input", { maxlength: 300, placeholder: "Ex.: frete grátis, vendedor oficial" });

    async function anotar(evento) {
      evento?.preventDefault();
      const numero = Number(String(valor.value).replace(",", "."));
      if (valor.value === "" || !Number.isFinite(numero) || numero < 0) {
        avisar("Informe o preço encontrado.", "erro");
        valor.focus();
        return;
      }
      try {
        await api.post(`/precos/produtos/${produto.id}/referencias`, {
          valor: numero,
          fonte: fonte.value.trim() || "Mercado Livre",
          link: link.value.trim() || null,
          observacao: observacao.value.trim() || null,
        });
        avisar("Preço de referência anotado.");
        carregar();
      } catch (falha) {
        avisar(falha.message, "erro");
      }
    }

    async function remover(referencia) {
      try {
        await api.delete(`/precos/referencias/${referencia.id}`);
        avisar("Preço de referência removido.");
        carregar();
      } catch (falha) {
        avisar(falha.message, "erro");
      }
    }

    const podeAnotar = pode("solicitacoes.editar");

    return bloco(
      "Preços de mercado",
      h(
        "p",
        { class: "suave" },
        "Abra a busca na loja, veja os preços e anote aqui o que servir de referência para negociar."
      ),
      atalhos,
      automaticas,
      podeAnotar
        ? h(
            "div",
            {
              class: "form-referencia",
              role: "group",
              "aria-label": "Anotar preço de referência",
              onKeydown: (evento) => {
                if (evento.key === "Enter" && evento.target.tagName === "INPUT") anotar(evento);
              },
            },
            h("label", {}, "Preço (R$)", valor),
            h("label", {}, "Loja", fonte),
            h("label", { class: "largo" }, "Link", link),
            h("label", { class: "largo" }, "Observação", observacao),
            h("button", { type: "button", class: "primario", onClick: anotar }, "Anotar preço")
          )
        : null,
      tabela(
        [
          { titulo: "Data", classe: "numero", valor: (r) => formatar.data(r.data_registro) },
          {
            titulo: "Loja",
            valor: (r) => (r.link ? h("a", { href: r.link, target: "_blank", rel: "noopener noreferrer" }, r.fonte) : r.fonte),
          },
          { titulo: "Observação", valor: (r) => r.observacao || "—" },
          { titulo: "Anotado por", valor: (r) => r.usuario || "—" },
          { titulo: "Preço", classe: "direita numero", valor: (r) => precoReferencia(r.valor) },
          ...(podeAnotar
            ? [{
                titulo: h("span", { class: "oculto-visualmente" }, "Ações"),
                classe: "acoes",
                valor: (r) => h("button", { type: "button", class: "pequeno perigo", onClick: () => remover(r) }, "Remover"),
              }]
            : []),
        ],
        dados.referencias,
        { vazio: "Nenhum preço de referência anotado ainda." }
      )
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

    const mercado = dados.referencias[0]
      ? ` Mercado: ${precoReferencia(dados.referencias[0].valor)} (${dados.referencias[0].fonte}).`
      : "";

    if (!r.compras) return `Ainda não comprado pelo sistema.${mercado}`;

    return `Último pago ${formatar.moeda(r.ultimo_pago)}, média ${formatar.moeda(r.media_paga)}.${mercado}`;
  } catch {
    return "";
  }
}
