"""Busca por texto que ignora acentos, maiúsculas e a ordem das palavras.

"splitter 1:8" encontra "SPLITTER APC 1:8 FIBRA"; "optico" encontra "ÓPTICO".
Feito com translate() do próprio PostgreSQL, sem depender de extensões.
"""

import unicodedata

COM_ACENTO = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑáàâãäéèêëíìîïóòôõöúùûüçñ"
SEM_ACENTO = "AAAAAEEEEIIIIOOOOOUUUUCNaaaaaeeeeiiiiooooouuuucn"


def _normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def condicao_busca(coluna: str, busca: str | None):
    """Devolve (sql, parametros) exigindo que cada palavra apareça na coluna."""
    palavras = [p for p in _normalizar(busca or "").split() if p]

    if not palavras:
        return None, []

    expressao = f"lower(translate({coluna}, '{COM_ACENTO}', '{SEM_ACENTO}'))"
    sql = " AND ".join(f"{expressao} LIKE %s" for _ in palavras)
    parametros = [f"%{p.replace('%', '').replace('_', '')}%" for p in palavras]

    return f"({sql})", parametros
