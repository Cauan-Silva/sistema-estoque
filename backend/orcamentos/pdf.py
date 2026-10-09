"""Texto e imagens de páginas de PDF, para a leitura com IA local."""

from io import BytesIO

MAXIMO_PAGINAS = 4


def _abrir(conteudo: bytes):
    import pypdfium2 as pdfium

    return pdfium.PdfDocument(conteudo)


def texto(conteudo: bytes) -> str:
    """Texto das primeiras páginas, ou "" se o PDF for só imagem (escaneado)."""
    documento = _abrir(conteudo)
    try:
        partes = []
        for indice in range(min(len(documento), MAXIMO_PAGINAS)):
            pagina = documento[indice]
            pagina_texto = pagina.get_textpage()
            partes.append(pagina_texto.get_text_range())
            pagina_texto.close()
            pagina.close()
        return "\n\n".join(parte.strip() for parte in partes if parte.strip())
    finally:
        documento.close()


def imagens(conteudo: bytes, escala: float = 2.0) -> list[bytes]:
    """Páginas renderizadas como PNG (para PDFs escaneados)."""
    documento = _abrir(conteudo)
    try:
        resultado = []
        for indice in range(min(len(documento), MAXIMO_PAGINAS)):
            pagina = documento[indice]
            imagem = pagina.render(scale=escala).to_pil()
            saida = BytesIO()
            imagem.save(saida, format="PNG")
            resultado.append(saida.getvalue())
            pagina.close()
        return resultado
    finally:
        documento.close()
