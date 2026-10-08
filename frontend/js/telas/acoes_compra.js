import { api } from "../api.js";
import { abrirFormulario, formatar, hojeISO } from "../ui.js";

export function abrirRegistroCompra({ solicitacaoId, cotacao, aoConcluir }) {
  abrirFormulario({
    titulo: `Registrar compra da solicitação Nº ${solicitacaoId}`,
    descricao: cotacao
      ? `${cotacao.fornecedor}: ${formatar.moeda(cotacao.valor_total)}${cotacao.forma_pagamento ? `, pagamento ${cotacao.forma_pagamento}` : ""}. Se a previsão ficar vazia, ela é calculada com o prazo de ${formatar.dias(cotacao.prazo_entrega_dias)}.`
      : undefined,
    campos: [
      { nome: "numero_pedido", rotulo: "Número do pedido", maximo: 50 },
      [
        { nome: "data_compra", rotulo: "Data da compra", tipo: "date", valor: hojeISO() },
        { nome: "previsao_entrega", rotulo: "Previsão de entrega", tipo: "date" },
      ],
      { nome: "observacao", rotulo: "Observação", tipo: "textarea", maximo: 500 },
    ],
    textoAcao: "Registrar compra",
    aoEnviar: async (dados) => {
      const compra = await api.post(`/solicitacoes-compra/${solicitacaoId}/compra`, dados);
      await aoConcluir(compra);
    },
  });
}
