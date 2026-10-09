from datetime import datetime
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from backend.autenticacao import obter_usuario_atual
from backend.permissoes import exigir_alguma, perfil_do_usuario
from backend.repositorio_anexo import (
    buscar_anexo,
    excluir_anexo,
    listar_anexos,
    salvar_anexo,
)


router = APIRouter(
    prefix="/solicitacoes-compra/{solicitacao_id}/anexos",
    tags=["Anexos"],
    dependencies=[Depends(obter_usuario_atual)]
)

TAMANHO_MAXIMO = 10 * 1024 * 1024

# Extensão permitida -> tipo de conteúdo servido. HTML e SVG ficam de fora de propósito.
TIPOS = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "xml": "application/xml",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "txt": "text/plain",
}

VISUALIZAVEIS = {"application/pdf", "image/png", "image/jpeg", "image/webp", "image/gif"}

TipoAnexo = Literal["NOTA_FISCAL", "PROPOSTA", "PEDIDO", "BOLETO", "OUTRO"]

PODE_ANEXAR = exigir_alguma(
    "solicitacoes.editar", "cotacoes.editar", "compras.registrar", "recebimentos.registrar"
)


class AnexoResposta(BaseModel):
    id: int
    solicitacao_id: int
    tipo: str
    descricao: str | None
    nome_arquivo: str
    tipo_conteudo: str
    tamanho: int
    fornecedor_id: int | None
    fornecedor: str | None
    usuario_id: int | None
    usuario: str | None
    data_envio: datetime


@router.get("", response_model=list[AnexoResposta])
def listar(solicitacao_id: int):
    anexos = listar_anexos(solicitacao_id)

    if anexos is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação de compra não encontrada.")

    return anexos


@router.post("", response_model=AnexoResposta, status_code=status.HTTP_201_CREATED)
async def anexar(
    solicitacao_id: int,
    arquivo: UploadFile = File(...),
    tipo: TipoAnexo = Form("OUTRO"),
    descricao: str | None = Form(None, max_length=200),
    fornecedor_id: int | None = Form(None, gt=0),
    usuario=PODE_ANEXAR,
):
    nome = (arquivo.filename or "arquivo").replace("\\", "/").rsplit("/", 1)[-1].strip()[:255] or "arquivo"
    extensao = nome.lower().rsplit(".", 1)[-1] if "." in nome else ""

    if extensao not in TIPOS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Tipo de arquivo não aceito. Envie PDF, imagem, XML, planilha, documento ou texto.",
        )

    conteudo = await arquivo.read(TAMANHO_MAXIMO + 1)

    if not conteudo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O arquivo está vazio.")

    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "O arquivo passa de 10 MB.")

    anexo, erro = salvar_anexo(
        solicitacao_id=solicitacao_id,
        tipo=tipo,
        descricao=descricao.strip() if descricao and descricao.strip() else None,
        nome_arquivo=nome,
        tipo_conteudo=TIPOS[extensao],
        conteudo=conteudo,
        fornecedor_id=fornecedor_id,
        usuario_id=usuario[0],
    )

    if erro == "solicitacao_nao_encontrada":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação de compra não encontrada.")
    if erro == "fornecedor_nao_encontrado":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fornecedor não encontrado.")
    if erro or anexo is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível salvar o anexo.")

    return anexo


@router.get("/{anexo_id}")
def baixar(solicitacao_id: int, anexo_id: int):
    anexo = buscar_anexo(solicitacao_id, anexo_id, com_conteudo=True)

    if anexo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anexo não encontrado.")

    disposicao = "inline" if anexo["tipo_conteudo"] in VISUALIZAVEIS else "attachment"
    ascii_nome = anexo["nome_arquivo"].encode("ascii", "ignore").decode().replace('"', "") or "anexo"

    return Response(
        content=anexo["conteudo"],
        media_type=anexo["tipo_conteudo"],
        headers={
            "Content-Disposition": f"{disposicao}; filename=\"{ascii_nome}\"; filename*=UTF-8''{quote(anexo['nome_arquivo'])}",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox",
        },
    )


@router.delete("/{anexo_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(solicitacao_id: int, anexo_id: int, usuario=Depends(obter_usuario_atual)):
    anexo = buscar_anexo(solicitacao_id, anexo_id)

    if anexo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anexo não encontrado.")

    if anexo["usuario_id"] != usuario[0] and perfil_do_usuario(usuario) != "ADMINISTRADOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só quem enviou o anexo ou um administrador pode excluí-lo.")

    excluir_anexo(solicitacao_id, anexo_id)
