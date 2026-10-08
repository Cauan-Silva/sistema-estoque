let usuarioAtual = null;

export const NOMES_PERFIS = {
  ADMINISTRADOR: "Administrador",
  COMPRADOR: "Comprador",
  APROVADOR: "Aprovador",
  ALMOXARIFE: "Almoxarife",
  CONSULTA: "Consulta",
};

export function definirUsuario(usuario) {
  usuarioAtual = usuario;
}

export function usuario() {
  return usuarioAtual;
}

export function pode(permissao) {
  return Boolean(usuarioAtual?.permissoes?.includes(permissao));
}
