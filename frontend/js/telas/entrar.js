import { api, salvarToken } from "../api.js";
import { h } from "../ui.js";
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

  const cores = ["azul", "laranja", "verde", "marrom", "ardosia", "vermelho"];

  raiz.replaceChildren(
    h(
      "div",
      { class: "entrada" },
      h(
        "section",
        { class: "entrada-lado" },
        h("h1", {}, "Estoque e Compras"),
        h(
          "div",
          { class: "feixe", "aria-hidden": "true" },
          cores.map((cor, indice) =>
            h("span", { style: { background: `var(--fibra-${cor})`, width: `${92 - indice * 9}%` } })
          )
        ),
        h(
          "p",
          {},
          "Controle o que entra e sai do estoque e acompanhe cada compra, da solicitação ao pedido."
        )
      ),
      h("section", { class: "entrada-form" }, formulario)
    )
  );

  aplicarModo();
}
