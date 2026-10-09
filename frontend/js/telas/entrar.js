import { api, salvarToken } from "../api.js";
import { h, paisagem } from "../ui.js";
import { seletorTema } from "../tema.js";

export function telaEntrar(raiz, aoEntrar) {
  let modo = "entrar";

  const erro = h("p", { class: "erro", role: "alert", hidden: true });
  const campoNome = h("label", { hidden: true }, "Nome", h("input", { name: "nome", autocomplete: "name" }));
  const titulo = h("h2", {}, "Entrar");
  const botao = h("button", { type: "submit", class: "primario" }, "Entrar");
  const alternar = h("button", { type: "button", class: "texto" }, "Ainda não tenho conta");

  const formulario = h(
    "form",
    {},
    titulo,
    campoNome,
    h(
      "label",
      {},
      "E-mail",
      h("input", { name: "email", type: "email", required: true, autocomplete: "email" })
    ),
    h(
      "label",
      {},
      "Senha",
      h("input", {
        name: "senha",
        type: "password",
        required: true,
        minlength: "8",
        autocomplete: "current-password",
      })
    ),
    erro,
    botao,
    alternar,
    seletorTema()
  );

  function aplicarModo() {
    const cadastro = modo === "cadastrar";
    titulo.textContent = cadastro ? "Criar conta" : "Entrar";
    botao.textContent = cadastro ? "Criar conta e entrar" : "Entrar";
    alternar.textContent = cadastro ? "Já tenho conta" : "Ainda não tenho conta";
    campoNome.hidden = !cadastro;
    formulario.elements.nome.required = cadastro;
    formulario.elements.senha.autocomplete = cadastro ? "new-password" : "current-password";
    erro.hidden = true;
  }

  alternar.addEventListener("click", () => {
    modo = modo === "entrar" ? "cadastrar" : "entrar";
    aplicarModo();
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    erro.hidden = true;
    botao.disabled = true;

    const email = formulario.elements.email.value.trim();
    const senha = formulario.elements.senha.value;

    try {
      if (modo === "cadastrar") {
        await api.post(
          "/usuarios",
          { nome: formulario.elements.nome.value.trim(), email, senha },
          { semRedirecionar: true }
        );
      }

      const resposta = await api.post("/usuarios/login", { email, senha }, { semRedirecionar: true });
      salvarToken(resposta.access_token);
      await aoEntrar();
    } catch (falha) {
      erro.textContent = falha.message;
      erro.hidden = false;
    } finally {
      botao.disabled = false;
    }
  });

  raiz.replaceChildren(
    h(
      "div",
      { class: "entrada" },
      h("div", { class: "entrada-ceu", "aria-hidden": "true" }),
      paisagem("cena"),
      h(
        "header",
        { class: "entrada-topo" },
        h("span", { class: "marca" }, h("span", { class: "marca-icone" }, h("span", { class: "marca-sol" })), h("span", { class: "marca-nome" }, "Estoque", h("em", {}, " & Compras")))
      ),
      h(
        "section",
        { class: "entrada-chamada" },
        h("h1", {}, "Estoque"),
        h(
          "p",
          {},
          "Do pedido de compra à entrada no estoque: cotações, aprovação, recebimento e relatórios num só lugar."
        )
      ),
      h("section", { class: "entrada-form" }, formulario)
    )
  );

  aplicarModo();
}
