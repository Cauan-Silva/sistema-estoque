import { api, listarTodos } from "../api.js";
import { icone } from "../icones.js";
import { pode } from "../sessao.js";
import { abrirFormulario, avisar, cabecalho, formatar, h, seletor } from "../ui.js";

/*
 * Nova solicitação a partir de orçamentos recebidos.
 * 1. O usuário envia PDFs, prints ou XML de NF-e.
 * 2. A API lê cada um e sugere fornecedor e produtos.
 * 3. O usuário revisa, associa os itens aos produtos e cria a solicitação
 *    já com uma cotação por orçamento.
 */

const ACEITOS = ".pdf,.png,.jpg,.jpeg,.webp,.xml,application/pdf,image/*,text/xml,application/xml";

let sequencia = 0;

function numero(valor) {
  const convertido = Number(String(valor ?? "").replace(",", "."));
  return Number.isFinite(convertido) ? convertido : null;
}

function precoUnitario(valor) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(valor);
}

export async function telaImportarOrcamentos(area) {
  const [configuracao, produtos, fornecedores, formasPagina, categorias] = await Promise.all([
    api.get("/orcamentos/configuracao"),
    listarTodos("/produtos"),
    api.get("/fornecedores"),
    api.get("/formas-pagamento?ativo=true&tamanho=100"),
    api.get("/categorias"),
  ]);

  const formas = formasPagina.itens || [];
  const ativos = () => fornecedores.filter((f) => f.ativo);
  const estado = { orcamentos: [], quantidades: new Map(), observacao: "" };

  const lista = h("div", { class: "lista-orcamentos" });
  const resumo = h("section", { class: "bloco resumo-orcamentos" });
  const botaoCriar = h("button", { class: "primario", onClick: criar }, "Criar solicitação");

  /* ---------- Envio dos arquivos ---------- */

  const seletorArquivos = h("input", {
    type: "file",
    multiple: true,
    accept: ACEITOS,
    class: "oculto-visualmente",
    onChange: () => {
      receber([...seletorArquivos.files]);
      seletorArquivos.value = "";
    },
  });

  const zona = h(
    "label",
    {
      class: "zona-envio",
      onDragover: (evento) => {
        evento.preventDefault();
        zona.classList.add("arrastando");
      },
      onDragleave: () => zona.classList.remove("arrastando"),
      onDrop: (evento) => {
        evento.preventDefault();
        zona.classList.remove("arrastando");
        receber([...evento.dataTransfer.files]);
      },
    },
    seletorArquivos,
    h("span", { class: "zona-icone" }, icone("pacote")),
    h("strong", {}, "Arraste os orçamentos aqui ou clique para escolher"),
    h(
      "span",
      { class: "suave" },
      configuracao.leitura_por_ia
        ? "PDF, print ou foto (PNG, JPG) e XML de NF-e. Pode enviar vários de uma vez."
        : "Somente XML de NF-e. Para ler PDF e imagens, configure uma IA no servidor (veja o aviso acima)."
    )
  );

  function receber(arquivos) {
    arquivos.forEach((arquivo) => {
      const orcamento = { id: (sequencia += 1), arquivo: arquivo.name, estado: "lendo" };
      estado.orcamentos.push(orcamento);
      ler(orcamento, arquivo);
    });
    desenhar();
  }

  async function ler(orcamento, arquivo) {
    try {
      const dados = await api.enviarArquivo("/orcamentos/ler", arquivo);
      Object.assign(orcamento, {
        estado: "pronto",
        origem: dados.origem,
        lido: dados,
        fornecedor_id: dados.fornecedor_sugerido?.id ?? "",
        frete: dados.frete ?? 0,
        prazo_entrega_dias: dados.prazo_entrega_dias ?? "",
        validade: dados.validade ?? "",
        forma_pagamento_id: dados.forma_pagamento_sugerida?.id ?? "",
        observacao: [dados.numero_documento ? `Orçamento ${dados.numero_documento}` : null, dados.observacao]
          .filter(Boolean)
          .join(". ")
          .slice(0, 500),
        itens: dados.itens.map((item) => ({
          ...item,
          produto_id: item.produto_sugerido?.id ?? "",
        })),
      });
    } catch (falha) {
      Object.assign(orcamento, { estado: "erro", erro: falha.message });
    }
    desenhar();
  }

  /* ---------- Cadastros rápidos ---------- */

  async function cadastrarFornecedor(orcamento) {
    try {
      const novo = await api.post("/fornecedores", {
        nome: orcamento.lido.fornecedor_nome.slice(0, 150),
        cpf_cnpj: orcamento.lido.fornecedor_cnpj || null,
      });
      fornecedores.push(novo);
      orcamento.fornecedor_id = novo.id;
      avisar(`Fornecedor ${novo.nome} cadastrado.`);
      desenhar();
    } catch (falha) {
      avisar(falha.message, "erro");
    }
  }

  function cadastrarProduto(item) {
    abrirFormulario({
      titulo: "Cadastrar produto",
      descricao: `A partir do item "${item.descricao}".`,
      campos: [
        { nome: "nome", rotulo: "Nome", obrigatorio: true, minimo: 2, maximo: 150, valor: item.descricao.slice(0, 150) },
        {
          nome: "categoria_id",
          rotulo: "Categoria",
          tipo: "select",
          numero: true,
          obrigatorio: true,
          opcoes: [["", "Escolha uma categoria"], ...categorias.map((c) => [c.id, c.nome])],
        },
        { nome: "estoque_minimo", rotulo: "Estoque mínimo", tipo: "number", min: 0, passo: 1, valor: 5 },
      ],
      textoAcao: "Cadastrar e associar",
      aoEnviar: async (dados) => {
        const novo = await api.post("/produtos", {
          ...dados,
          estoque_minimo: dados.estoque_minimo ?? 5,
          quantidade: 0,
          preco: Math.round(item.preco_unitario * 100) / 100,
        });
        produtos.push(novo);
        item.produto_id = novo.id;
        avisar(`Produto ${novo.nome} cadastrado.`);
        desenhar();
      },
    });
  }

  /* ---------- Revisão de cada orçamento ---------- */

  function remover(orcamento) {
    estado.orcamentos = estado.orcamentos.filter((o) => o !== orcamento);
    desenhar();
  }

  function campo(rotulo, controle, dica) {
    return h("label", {}, rotulo, controle, dica ? h("span", { class: "dica-campo" }, dica) : null);
  }

  function entrada(orcamento, chave, atributos = {}) {
    return h("input", {
      ...atributos,
      value: orcamento[chave] ?? "",
      onInput: (evento) => {
        orcamento[chave] = evento.target.value;
      },
    });
  }

  function seloSugestao(item) {
    const sugestao = item.produto_sugerido;
    if (!sugestao || String(sugestao.id) !== String(item.produto_id)) return null;
    return h(
      "span",
      { class: "selo-sugestao", dataset: { motivo: sugestao.motivo } },
      sugestao.motivo === "referencia" ? "Já usado antes" : `Parecido (${Math.round(sugestao.confianca * 100)}%)`
    );
  }

  function linhaItem(orcamento, item) {
    const opcoes = [["", "Não incluir"], ...produtos.map((p) => [p.id, p.nome])];

    return h(
      "tr",
      { class: item.produto_id ? "" : "item-ignorado" },
      h(
        "td",
        {},
        h("span", { class: "descricao-fornecedor" }, item.descricao),
        item.codigo ? h("span", { class: "codigo-fornecedor" }, `Cód. ${item.codigo}`) : null
      ),
      h("td", { class: "direita numero" }, `${formatar.numero(item.quantidade)}${item.unidade ? ` ${item.unidade}` : ""}`),
      h(
        "td",
        { class: "direita" },
        h("input", {
          type: "number",
          min: 0,
          step: "0.0001",
          class: "entrada-preco",
          "aria-label": `Preço unitário de ${item.descricao}`,
          value: item.preco_unitario,
          onInput: (evento) => {
            item.preco_unitario = numero(evento.target.value);
            desenharResumo();
          },
        })
      ),
      h(
        "td",
        { class: "celula-produto" },
        h(
          "div",
          { class: "escolha-produto" },
          seletor(opcoes, item.produto_id, {
            "aria-label": `Produto para ${item.descricao}`,
            onChange: (evento) => {
              item.produto_id = evento.target.value ? Number(evento.target.value) : "";
              desenhar();
            },
          }),
          pode("estoque.editar")
            ? h("button", { type: "button", class: "pequeno", title: "Cadastrar como produto novo", onClick: () => cadastrarProduto(item) }, "Novo")
            : null
        ),
        seloSugestao(item)
      )
    );
  }

  function cartao(orcamento) {
    const topo = h(
      "div",
      { class: "bloco-topo" },
      h(
        "div",
        { class: "titulo-orcamento" },
        h("h2", {}, orcamento.arquivo),
        orcamento.origem
          ? h("span", { class: "selo-origem" }, { xml: "XML da NF-e", ollama: "Lido por IA local", anthropic: "Lido por IA" }[orcamento.origem] || "Lido")
          : null
      ),
      h("button", { type: "button", class: "pequeno perigo", onClick: () => remover(orcamento) }, "Remover")
    );

    if (orcamento.estado === "lendo") {
      return h("section", { class: "bloco orcamento lendo" }, topo, h("p", { class: "lendo-texto" }, configuracao.provedor === "ollama" ? "Lendo o orçamento com a IA local… pode levar alguns minutos." : "Lendo o orçamento…"));
    }

    if (orcamento.estado === "erro") {
      return h("section", { class: "bloco orcamento com-erro" }, topo, h("p", { class: "erro-texto" }, orcamento.erro));
    }

    const lido = orcamento.lido;
    const semCadastro = !orcamento.fornecedor_id && lido.fornecedor_nome;

    return h(
      "section",
      { class: "bloco orcamento" },
      topo,
      lido.avisos.length ? h("ul", { class: "avisos-orcamento" }, lido.avisos.map((aviso) => h("li", {}, aviso))) : null,
      h(
        "div",
        { class: "campos-orcamento" },
        campo(
          "Fornecedor",
          seletor([["", "Escolha o fornecedor"], ...ativos().map((f) => [f.id, f.nome])], orcamento.fornecedor_id, {
            onChange: (evento) => {
              orcamento.fornecedor_id = evento.target.value ? Number(evento.target.value) : "";
              desenhar();
            },
          }),
          lido.fornecedor_nome
            ? h(
                "span",
                {},
                `No arquivo: ${lido.fornecedor_nome}${lido.fornecedor_cnpj ? ` (${lido.fornecedor_cnpj})` : ""}`,
                semCadastro && pode("fornecedores.editar")
                  ? h("button", { type: "button", class: "link", onClick: () => cadastrarFornecedor(orcamento) }, "Cadastrar")
                  : null
              )
            : null
        ),
        campo("Frete (R$)", entrada(orcamento, "frete", { type: "number", min: 0, step: "0.01" })),
        campo("Prazo de entrega (dias)", entrada(orcamento, "prazo_entrega_dias", { type: "number", min: 0, step: 1 })),
        campo("Válida até", entrada(orcamento, "validade", { type: "date" })),
        campo(
          "Forma de pagamento",
          seletor([["", "Não informada"], ...formas.map((f) => [f.id, `${f.codigo} - ${f.titulo}`])], orcamento.forma_pagamento_id, {
            onChange: (evento) => {
              orcamento.forma_pagamento_id = evento.target.value ? Number(evento.target.value) : "";
            },
          }),
          lido.condicao_pagamento ? `No arquivo: ${lido.condicao_pagamento}` : null
        ),
        h("div", { class: "campo-largo" }, campo("Observação", entrada(orcamento, "observacao", { maxlength: 500 })))
      ),
      orcamento.itens.length
        ? h(
            "div",
            { class: "quadro" },
            h(
              "table",
              { class: "tabela-orcamento" },
              h(
                "thead",
                {},
                h(
                  "tr",
                  {},
                  h("th", {}, "Item no orçamento"),
                  h("th", { class: "direita" }, "Quantidade"),
                  h("th", { class: "direita" }, "Preço unit. (R$)"),
                  h("th", {}, "Produto no sistema")
                )
              ),
              h("tbody", {}, orcamento.itens.map((item) => linhaItem(orcamento, item)))
            )
          )
        : null
    );
  }

  /* ---------- Itens da solicitação ---------- */

  function prontos() {
    return estado.orcamentos.filter((o) => o.estado === "pronto");
  }

  function produtosEscolhidos() {
    const mapa = new Map();

    prontos().forEach((orcamento) => {
      const fornecedor = fornecedores.find((f) => f.id === orcamento.fornecedor_id);
      orcamento.itens
        .filter((item) => item.produto_id)
        .forEach((item) => {
          const atual = mapa.get(item.produto_id) || {
            produto_id: item.produto_id,
            nome: produtos.find((p) => p.id === item.produto_id)?.nome ?? "—",
            quantidade: 0,
            ofertas: [],
          };
          atual.quantidade = Math.max(atual.quantidade, Math.ceil(item.quantidade));
          atual.ofertas.push({ fornecedor: fornecedor?.nome ?? orcamento.arquivo, preco: item.preco_unitario });
          mapa.set(item.produto_id, atual);
        });
    });

    return [...mapa.values()];
  }

  function desenharResumo() {
    const itens = produtosEscolhidos();
    const cotacoes = prontos().filter((o) => o.itens.some((i) => i.produto_id)).length;

    botaoCriar.disabled = !itens.length;
    botaoCriar.textContent = itens.length
      ? `Criar solicitação com ${cotacoes} cotaç${cotacoes === 1 ? "ão" : "ões"}`
      : "Criar solicitação";

    resumo.replaceChildren(
      h("div", { class: "bloco-topo" }, h("h2", {}, "Itens da solicitação")),
      itens.length
        ? h(
            "div",
            { class: "quadro" },
            h(
              "table",
              {},
              h(
                "thead",
                {},
                h(
                  "tr",
                  {},
                  h("th", {}, "Produto"),
                  h("th", { class: "direita" }, "Quantidade a comprar"),
                  h("th", { class: "direita" }, "Ofertas"),
                  h("th", { class: "direita" }, "Menor preço")
                )
              ),
              h(
                "tbody",
                {},
                itens.map((item) => {
                  const precos = item.ofertas.map((o) => o.preco).filter((p) => p !== null);
                  const menor = precos.length ? Math.min(...precos) : null;
                  const melhor = item.ofertas.find((o) => o.preco === menor);
                  return h(
                    "tr",
                    {},
                    h("td", {}, item.nome),
                    h(
                      "td",
                      { class: "direita" },
                      h("input", {
                        type: "number",
                        min: 1,
                        step: 1,
                        class: "entrada-quantidade",
                        "aria-label": `Quantidade de ${item.nome}`,
                        value: estado.quantidades.get(item.produto_id) ?? item.quantidade,
                        onInput: (evento) => estado.quantidades.set(item.produto_id, evento.target.value),
                      })
                    ),
                    h("td", { class: "direita numero" }, item.ofertas.length),
                    h(
                      "td",
                      { class: "direita numero" },
                      menor === null ? "—" : `${precoUnitario(menor)}${item.ofertas.length > 1 ? ` (${melhor.fornecedor})` : ""}`
                    )
                  );
                })
              )
            )
          )
        : h("p", { class: "suave" }, "Associe os itens dos orçamentos aos produtos para montar a solicitação."),
      h(
        "label",
        { class: "observacao-solicitacao" },
        "Observação da solicitação",
        h(
          "textarea",
          {
            maxlength: 500,
            onInput: (evento) => {
              estado.observacao = evento.target.value;
            },
          },
          estado.observacao
        )
      ),
      h("div", { class: "acoes-final" }, botaoCriar)
    );
  }

  function desenhar() {
    lista.replaceChildren(...estado.orcamentos.map(cartao));
    desenharResumo();
  }

  /* ---------- Criação ---------- */

  function montarCorpo() {
    const erros = [];
    const orcamentos = [];
    const usados = new Map();

    if (estado.orcamentos.some((o) => o.estado === "lendo")) {
      erros.push("Aguarde terminar a leitura dos arquivos.");
    }

    prontos().forEach((orcamento) => {
      const itens = orcamento.itens.filter((item) => item.produto_id);
      if (!itens.length) return;

      if (!orcamento.fornecedor_id) {
        erros.push(`Escolha o fornecedor de "${orcamento.arquivo}".`);
        return;
      }
      if (usados.has(orcamento.fornecedor_id)) {
        erros.push(`"${orcamento.arquivo}" e "${usados.get(orcamento.fornecedor_id)}" são do mesmo fornecedor. Remova um deles.`);
      }
      usados.set(orcamento.fornecedor_id, orcamento.arquivo);

      const prazo = numero(orcamento.prazo_entrega_dias);
      if (orcamento.prazo_entrega_dias === "" || prazo === null || prazo < 0) {
        erros.push(`Informe o prazo de entrega de "${orcamento.arquivo}".`);
      }

      const repetidos = itens.map((i) => i.produto_id).filter((id, indice, todos) => todos.indexOf(id) !== indice);
      if (repetidos.length) {
        erros.push(`Em "${orcamento.arquivo}", dois itens estão associados ao mesmo produto.`);
      }

      if (itens.some((item) => item.preco_unitario === null || item.preco_unitario < 0)) {
        erros.push(`Confira os preços de "${orcamento.arquivo}".`);
      }

      orcamentos.push({
        fornecedor_id: orcamento.fornecedor_id,
        frete: numero(orcamento.frete) ?? 0,
        prazo_entrega_dias: Math.round(prazo ?? 0),
        validade: orcamento.validade || null,
        forma_pagamento_id: orcamento.forma_pagamento_id || null,
        observacao: orcamento.observacao?.trim() || null,
        itens: itens.map((item) => ({
          produto_id: item.produto_id,
          preco_unitario: item.preco_unitario,
          codigo_fornecedor: item.codigo ? String(item.codigo).slice(0, 100) : null,
          descricao_fornecedor: item.descricao.slice(0, 300),
        })),
      });
    });

    const itens = produtosEscolhidos().map((item) => {
      const quantidade = Number(estado.quantidades.get(item.produto_id) ?? item.quantidade);
      if (!Number.isInteger(quantidade) || quantidade < 1) {
        erros.push(`A quantidade de ${item.nome} precisa ser um número inteiro maior que zero.`);
      }
      return { produto_id: item.produto_id, quantidade };
    });

    return { erros, corpo: { observacao: estado.observacao.trim() || null, itens, orcamentos } };
  }

  async function criar() {
    const { erros, corpo } = montarCorpo();

    if (erros.length) {
      avisar(erros.join(" "), "erro");
      return;
    }

    botaoCriar.disabled = true;

    try {
      const solicitacao = await api.post("/orcamentos/solicitacao", corpo);
      avisar(`Solicitação Nº ${solicitacao.id} criada com ${corpo.orcamentos.length} cotação(ões).`);
      window.location.hash = `#/solicitacoes/${solicitacao.id}`;
    } catch (falha) {
      avisar(falha.message, "erro");
      botaoCriar.disabled = false;
    }
  }

  const secoes = [
    cabecalho(
      "Solicitação a partir de orçamentos",
      "Envie os orçamentos que recebeu. O sistema lê cada um, você confere e associa os itens aos produtos, e a solicitação já nasce com as cotações.",
      h("a", { class: "botao", href: "#/solicitacoes" }, "Voltar")
    ),
    configuracao.leitura_por_ia
      ? null
      : h(
          "p",
          { class: "aviso-configuracao" },
          "A leitura de PDF e imagens está desligada. Para ligar de graça, instale o Ollama no servidor e defina OLLAMA_URL no .env; ou use ANTHROPIC_API_KEY (pago por uso). Depois reinicie a API."
        ),
    zona,
    lista,
    resumo,
  ];

  area.replaceChildren(...secoes.filter(Boolean));

  desenharResumo();
}
