import { api, montarQuery } from "../api.js";
import { barraEmpilhada, barras, colunas } from "../graficos.js";
import { botoesExportar, cabecalho, campoFiltro, executar, formatar, h, seletor, tabela } from "../ui.js";

function inicioDoAno() {
  return `${new Date().getFullYear()}-01-01`;
}

function nomeMes(mes) {
  const [ano, numero] = mes.split("-");
  const data = new Date(Number(ano), Number(numero) - 1, 1);
  const texto = data.toLocaleDateString("pt-BR", { month: "short", year: "numeric" });
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function barra(valor, maximo, cor) {
  const largura = maximo > 0 ? Math.max(2, Math.round((valor / maximo) * 100)) : 0;

  return h(
    "div",
    { class: "barra", "aria-hidden": "true" },
    h("span", { style: { width: `${largura}%`, background: cor } })
  );
}

export async function telaRelatorioCompras(area) {
  const fornecedores = await api.get("/fornecedores");
  const filtros = { data_inicio: inicioDoAno(), data_fim: "", fornecedor_id: "" };
  const conteudo = h("div");

  async function carregar() {
    const dados = await executar(() =>
      api.get(
        `/relatorios/compras${montarQuery({
          data_inicio: filtros.data_inicio,
          data_fim: filtros.data_fim,
          fornecedor_id: filtros.fornecedor_id,
        })}`
      )
    );

    if (!dados) return;

    const indicador = (rotulo, valor, alerta = false) =>
      h("div", { class: `indicador ${alerta ? "alerta" : ""}` }, h("dt", {}, rotulo), h("dd", {}, valor));

    const maiorMes = Math.max(0, ...dados.por_mes.map((m) => m.valor_total));
    const maiorFornecedor = Math.max(0, ...dados.por_fornecedor.map((f) => f.valor_total));

    conteudo.replaceChildren(
      h(
        "dl",
        { class: "indicadores" },
        indicador("Compras", formatar.numero(dados.total_compras)),
        indicador("Valor comprado", formatar.moeda(dados.valor_total)),
        indicador("Valor médio por compra", formatar.moeda(dados.ticket_medio)),
        indicador("Frete pago", formatar.moeda(dados.frete_total)),
        indicador(
          "Entregas no prazo",
          dados.percentual_no_prazo === null ? "—" : `${formatar.numero(dados.percentual_no_prazo)}%`
        ),
        indicador(
          "Tempo médio de entrega",
          dados.prazo_medio_entrega_dias === null
            ? "—"
            : `${formatar.numero(dados.prazo_medio_entrega_dias)} dias`
        ),
        indicador(
          "Atrasadas sem entrega",
          formatar.numero(dados.atrasadas_em_aberto),
          dados.atrasadas_em_aberto > 0
        )
      ),
      h(
        "div",
        { class: "graficos" },
        colunas({
          titulo: "Valor comprado por mês",
          itens: dados.por_mes.map((m) => ({ rotulo: nomeMes(m.mes), valor: m.valor_total })),
          formatar: formatar.moeda,
          vazio: "Nenhuma compra no período.",
        }),
        h(
          "div",
          { class: "pilha-graficos" },
          barraEmpilhada({
            titulo: "Situação das entregas",
            descricao: "Compras do período pela situação da entrega.",
            partes: [
              { nome: "No prazo", valor: dados.entregas_no_prazo, cor: "var(--grafico-1)" },
              { nome: "Com atraso", valor: dados.entregas_atrasadas, cor: "var(--grafico-2)" },
              {
                nome: "Ainda não entregues",
                valor: dados.compras_parciais + dados.compras_pendentes,
                cor: "var(--grafico-3)",
              },
            ],
            formatar: (valor) => `${formatar.numero(valor)} compra${valor === 1 ? "" : "s"}`,
            vazio: "Nenhuma compra no período.",
          }),
          barras({
            titulo: "Maiores fornecedores",
            itens: dados.por_fornecedor.slice(0, 5).map((f) => ({ rotulo: f.fornecedor, valor: f.valor_total })),
            formatar: formatar.moeda,
            cor: "var(--grafico-1)",
            vazio: "Nenhuma compra no período.",
          })
        )
      ),
      h(
        "p",
        { class: "suave" },
        `Entregas: ${dados.compras_recebidas} completas, ${dados.compras_parciais} parciais e ${dados.compras_pendentes} pendentes. ` +
          `Das completas, ${dados.entregas_no_prazo} chegaram no prazo e ${dados.entregas_atrasadas} com atraso.`
      ),
      h(
        "div",
        { class: "colunas" },
        h(
          "section",
          { class: "secao" },
          h("h2", {}, "Por mês"),
          tabela(
            [
              { titulo: "Mês", valor: (m) => nomeMes(m.mes) },
              { titulo: "Compras", classe: "direita numero", valor: (m) => formatar.numero(m.compras) },
              { titulo: "Valor", classe: "direita numero", valor: (m) => formatar.moeda(m.valor_total) },
              {
                titulo: h("span", { class: "oculto-visualmente" }, "Proporção"),
                classe: "coluna-barra",
                valor: (m) => barra(m.valor_total, maiorMes, "var(--fibra-azul)"),
              },
            ],
            dados.por_mes,
            { vazio: "Nenhuma compra no período." }
          )
        ),
        h(
          "section",
          { class: "secao" },
          h("h2", {}, "Por fornecedor"),
          tabela(
            [
              { titulo: "Fornecedor", valor: (f) => f.fornecedor },
              { titulo: "Compras", classe: "direita numero", valor: (f) => formatar.numero(f.compras) },
              { titulo: "Valor", classe: "direita numero", valor: (f) => formatar.moeda(f.valor_total) },
              {
                titulo: "No prazo",
                classe: "direita numero",
                valor: (f) => {
                  const total = f.entregas_no_prazo + f.entregas_atrasadas;
                  return total ? `${f.entregas_no_prazo} de ${total}` : "—";
                },
              },
              {
                titulo: h("span", { class: "oculto-visualmente" }, "Proporção"),
                classe: "coluna-barra",
                valor: (f) => barra(f.valor_total, maiorFornecedor, "var(--fibra-laranja)"),
              },
            ],
            dados.por_fornecedor,
            { vazio: "Nenhuma compra no período." }
          )
        )
      ),
      h(
        "section",
        { class: "secao" },
        h("h2", {}, "Por produto"),
        tabela(
          [
            { titulo: "Produto", valor: (p) => p.produto },
            { titulo: "Quantidade", classe: "direita numero", valor: (p) => formatar.numero(p.quantidade) },
            { titulo: "Valor", classe: "direita numero", valor: (p) => formatar.moeda(p.valor_total) },
            { titulo: "Preço médio", classe: "direita numero", valor: (p) => formatar.moeda(p.preco_medio) },
            { titulo: "Menor preço", classe: "direita numero", valor: (p) => formatar.moeda(p.menor_preco) },
            { titulo: "Maior preço", classe: "direita numero", valor: (p) => formatar.moeda(p.maior_preco) },
          ],
          dados.por_produto,
          { vazio: "Nenhum produto comprado no período." }
        )
      )
    );
  }

  function aoFiltrar(chave) {
    return (evento) => {
      filtros[chave] = evento.target.value;
      carregar();
    };
  }

  area.replaceChildren(
    cabecalho(
      "Relatório de compras",
      "Quanto foi comprado, de quem, e se as entregas chegaram no prazo. O período considera a data da compra.",
      botoesExportar("/exportacoes/relatorio-compras", () => ({ ...filtros }))
    ),
    h(
      "div",
      { class: "filtros filtros-soltos" },
      campoFiltro("De", h("input", { type: "date", value: filtros.data_inicio, onChange: aoFiltrar("data_inicio") })),
      campoFiltro("Até", h("input", { type: "date", onChange: aoFiltrar("data_fim") })),
      campoFiltro(
        "Fornecedor",
        seletor([["", "Todos"], ...fornecedores.map((f) => [f.id, f.nome])], "", { onChange: aoFiltrar("fornecedor_id") })
      )
    ),
    conteudo
  );

  await carregar();
}
