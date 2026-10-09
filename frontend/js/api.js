const CHAVE_TOKEN = "estoque.token";
let tokenEmMemoria = null;

export function obterToken() {
  try {
    return localStorage.getItem(CHAVE_TOKEN) || tokenEmMemoria;
  } catch {
    return tokenEmMemoria;
  }
}

export function salvarToken(token) {
  tokenEmMemoria = token;
  try {
    localStorage.setItem(CHAVE_TOKEN, token);
  } catch {
    /* navegador sem armazenamento: fica só em memória */
  }
}

export function removerToken() {
  tokenEmMemoria = null;
  try {
    localStorage.removeItem(CHAVE_TOKEN);
  } catch {
    /* nada a remover */
  }
}

export class ErroApi extends Error {
  constructor(mensagem, status) {
    super(mensagem);
    this.status = status;
  }
}

const NOMES_CAMPOS = {
  nome: "Nome",
  email: "E-mail",
  senha: "Senha",
  quantidade: "Quantidade",
  preco: "Preço",
  preco_unitario: "Preço unitário",
  frete: "Frete",
  prazo_entrega_dias: "Prazo",
  itens: "Itens",
  justificativa: "Justificativa",
  categoria_id: "Categoria",
  produto_id: "Produto",
};

function mensagemDeErro(corpo, status) {
  if (corpo && typeof corpo.detail === "string") {
    return corpo.detail;
  }

  if (corpo && Array.isArray(corpo.detail)) {
    return corpo.detail
      .map((erro) => {
        const campo = [...(erro.loc || [])]
          .reverse()
          .find((parte) => typeof parte === "string" && parte !== "body");
        const nome = NOMES_CAMPOS[campo] || campo;
        const texto = (erro.msg || "valor inválido").replace(/^Value error, /, "");
        return nome ? `${nome}: ${texto}` : texto;
      })
      .join(" ");
  }

  if (status >= 500) {
    return "O servidor não conseguiu concluir a operação. Tente novamente.";
  }

  return "Não foi possível concluir a operação.";
}

export async function requisicao(metodo, caminho, corpo, opcoes = {}) {
  const cabecalhos = {};
  const token = obterToken();

  if (token) {
    cabecalhos.Authorization = `Bearer ${token}`;
  }

  const formulario = corpo instanceof FormData;

  if (corpo !== undefined && !formulario) {
    cabecalhos["Content-Type"] = "application/json";
  }

  let resposta;

  try {
    resposta = await fetch(caminho, {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : formulario ? corpo : JSON.stringify(corpo),
    });
  } catch {
    throw new ErroApi("Sem conexão com a API. Verifique se o servidor está rodando.", 0);
  }

  if (resposta.status === 204) {
    return null;
  }

  let dados = null;

  try {
    dados = await resposta.json();
  } catch {
    dados = null;
  }

  if (resposta.status === 401 && !opcoes.semRedirecionar) {
    removerToken();
    window.location.hash = "#/entrar";
    throw new ErroApi("Sua sessão expirou. Entre novamente.", 401);
  }

  if (!resposta.ok) {
    throw new ErroApi(mensagemDeErro(dados, resposta.status), resposta.status);
  }

  return dados;
}

export const api = {
  get: (caminho) => requisicao("GET", caminho),
  post: (caminho, corpo, opcoes) => requisicao("POST", caminho, corpo ?? {}, opcoes),
  put: (caminho, corpo) => requisicao("PUT", caminho, corpo),
  patch: (caminho, corpo) => requisicao("PATCH", caminho, corpo ?? {}),
  delete: (caminho) => requisicao("DELETE", caminho),
  enviarArquivo(caminho, arquivo, campo = "arquivo") {
    const corpo = new FormData();
    corpo.append(campo, arquivo);
    return requisicao("POST", caminho, corpo);
  },
};

export function montarQuery(parametros) {
  const busca = new URLSearchParams();

  Object.entries(parametros).forEach(([chave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== "" && valor !== false) {
      busca.set(chave, valor);
    }
  });

  const texto = busca.toString();
  return texto ? `?${texto}` : "";
}

export async function listarTodos(caminho, parametros = {}) {
  const resultado = [];
  const tamanho = 100;

  for (let pagina = 1; pagina <= 50; pagina += 1) {
    const lote = await api.get(caminho + montarQuery({ ...parametros, pagina, tamanho }));
    resultado.push(...lote);

    if (lote.length < tamanho) {
      break;
    }
  }

  return resultado;
}


export async function baixarArquivo(caminho) {
  const token = obterToken();
  let resposta;

  try {
    resposta = await fetch(caminho, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw new ErroApi("Sem conexão com a API. Verifique se o servidor está rodando.", 0);
  }

  if (!resposta.ok) {
    let dados = null;
    try {
      dados = await resposta.json();
    } catch {
      dados = null;
    }
    throw new ErroApi(mensagemDeErro(dados, resposta.status), resposta.status);
  }

  const disposicao = resposta.headers.get("Content-Disposition") || "";
  const nome = /filename="([^"]+)"/.exec(disposicao)?.[1] || "exportacao";
  const blob = await resposta.blob();
  const endereco = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = endereco;
  link.download = nome;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(endereco), 1000);

  return nome;
}
