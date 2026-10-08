import { api, montarQuery } from "../api.js";
import { pode } from "../sessao.js";
import {
  abrirFormulario,
  botoesExportar,
  cabecalho,
  campoFiltro,
  confirmar,
  etiquetaStatus,
  executar,
  h,
  seletor,
  tabela,
} from "../ui.js";

export async function telaFornecedores(area) {
  const podeEditar = pode("fornecedores.editar");
  const filtros = { ativo: "" };
  const lista = h("div");

  function campos(fornecedor = {}) {
    return [
      { nome: "nome", rotulo: "Nome", obrigatorio: true, minimo: 2, maximo: 150, valor: fornecedor.nome },
      [
        { nome: "cpf_cnpj", rotulo: "CPF ou CNPJ", maximo: 20, valor: fornecedor.cpf_cnpj },
        { nome: "contato", rotulo: "Pessoa de contato", maximo: 150, valor: fornecedor.contato },
      ],
      [
        { nome: "telefone", rotulo: "Telefone", tipo: "tel", maximo: 30, valor: fornecedor.telefone },
        { nome: "email", rotulo: "E-mail", tipo: "email", valor: fornecedor.email },
      ],
      { nome: "site", rotulo: "Site", maximo: 255, dica: "https://", valor: fornecedor.site },
    ];
  }

  function formulario(fornecedor) {
    abrirFormulario({
      titulo: fornecedor ? `Editar ${fornecedor.nome}` : "Novo fornecedor",
      campos: campos(fornecedor),
      textoAcao: fornecedor ? "Salvar alterações" : "Cadastrar fornecedor",
      aoEnviar: async (dados) => {
        if (fornecedor) {
          await api.put(`/fornecedores/${fornecedor.id}`, dados);
        } else {
          await api.post("/fornecedores", dados);
        }
        carregar();
      },
    });
  }

  async function alternarStatus(fornecedor) {
    const ativar = !fornecedor.ativo;

    const ok = await confirmar({
      titulo: ativar ? "Reativar fornecedor" : "Inativar fornecedor",
      mensagem: ativar
        ? `${fornecedor.nome} volta a poder ser usado em produtos e cotações.`
        : `${fornecedor.nome} deixa de aparecer para novos produtos e cotações. O histórico continua salvo.`,
      textoAcao: ativar ? "Reativar" : "Inativar",
      perigo: !ativar,
    });

    if (ok) {
      await executar(
        () => api.patch(`/fornecedores/${fornecedor.id}/status`, { ativo: ativar }),
        ativar ? "Fornecedor reativado." : "Fornecedor inativado."
      );
      carregar();
    }
  }

  function contato(fornecedor) {
    const partes = [fornecedor.contato, fornecedor.telefone, fornecedor.email].filter(Boolean);
    return partes.length ? partes.join(", ") : h("span", { class: "suave" }, "—");
  }

  async function carregar() {
    const fornecedores = await executar(() => api.get(`/fornecedores${montarQuery({ ativo: filtros.ativo })}`));
    if (!fornecedores) return;

    lista.replaceChildren(
      tabela(
        [
          {
            titulo: "Fornecedor",
            valor: (f) =>
              f.site
                ? h("a", { href: f.site, target: "_blank", rel: "noopener noreferrer" }, f.nome)
                : f.nome,
          },
          { titulo: "CPF ou CNPJ", classe: "numero", valor: (f) => f.cpf_cnpj || "—" },
          { titulo: "Contato", valor: contato },
          { titulo: "Status", valor: (f) => etiquetaStatus(f.ativo ? "ATIVO" : "INATIVO") },
          {
            titulo: h("span", { class: "oculto-visualmente" }, "Ações"),
            classe: "acoes",
            valor: (f) => !podeEditar ? null : [
              h("button", { class: "pequeno", onClick: () => formulario(f) }, "Editar"),
              h(
                "button",
                { class: `pequeno ${f.ativo ? "perigo" : ""}`, onClick: () => alternarStatus(f) },
                f.ativo ? "Inativar" : "Reativar"
              ),
            ],
          },
        ],
        fornecedores,
        {
          vazio: filtros.ativo ? "Nenhum fornecedor com esse status." : "Nenhum fornecedor cadastrado.",
          acaoVazio: podeEditar ? h("button", { class: "primario", onClick: () => formulario() }, "Cadastrar fornecedor") : null,
        }
      )
    );
  }

  area.replaceChildren(
    cabecalho(
      "Fornecedores",
      "Quem fornece os produtos e participa das cotações. Fornecedores são inativados, nunca excluídos.",
      botoesExportar("/exportacoes/fornecedores", () => ({ ativo: filtros.ativo })),
      podeEditar ? h("button", { class: "primario", onClick: () => formulario() }, "Cadastrar fornecedor") : null
    ),
    h(
      "div",
      { class: "filtros" },
      campoFiltro(
        "Status",
        seletor(
          [
            ["", "Todos"],
            ["true", "Ativos"],
            ["false", "Inativos"],
          ],
          "",
          {
            onChange: (evento) => {
              filtros.ativo = evento.target.value;
              carregar();
            },
          }
        )
      )
    ),
    lista
  );

  await carregar();
}
