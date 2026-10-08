from fastapi import Depends, HTTPException, status

from backend.autenticacao import obter_usuario_atual


PERFIS = (
    "ADMINISTRADOR",
    "COMPRADOR",
    "APROVADOR",
    "ALMOXARIFE",
    "CONSULTA",
)

PERMISSOES = {
    "estoque.editar": {"ADMINISTRADOR", "ALMOXARIFE"},
    "fornecedores.editar": {"ADMINISTRADOR", "COMPRADOR"},
    "solicitacoes.editar": {"ADMINISTRADOR", "COMPRADOR", "ALMOXARIFE"},
    "cotacoes.editar": {"ADMINISTRADOR", "COMPRADOR"},
    "compras.aprovar": {"ADMINISTRADOR", "APROVADOR"},
    "compras.registrar": {"ADMINISTRADOR", "COMPRADOR"},
    "recebimentos.registrar": {"ADMINISTRADOR", "ALMOXARIFE"},
    "usuarios.gerenciar": {"ADMINISTRADOR"},
    "auditoria.ver": {"ADMINISTRADOR"},
}

INDICE_PERFIL = 6


def perfil_do_usuario(usuario) -> str:
    return usuario[INDICE_PERFIL]


def permissoes_do_perfil(perfil: str) -> list[str]:
    return sorted(
        permissao
        for permissao, perfis in PERMISSOES.items()
        if perfil in perfis
    )


def exigir(permissao: str):
    if permissao not in PERMISSOES:
        raise ValueError(f"Permissão desconhecida: {permissao}")

    def verificar(usuario=Depends(obter_usuario_atual)):
        if perfil_do_usuario(usuario) not in PERMISSOES[permissao]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil não tem permissão para esta ação."
            )

        return usuario

    return Depends(verificar)
