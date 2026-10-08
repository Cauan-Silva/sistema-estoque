import logging
from datetime import date, timedelta

import psycopg2

from backend.database import conectar

logger = logging.getLogger(__name__)


def registrar_auditoria(
    id_requisicao: str,
    usuario_id: int | None,
    metodo: str,
    caminho: str,
    status: int,
    ip: str | None,
    duracao_ms: int
):
    conexao = conectar()

    if conexao is None:
        return

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO auditoria (
                id_requisicao,
                usuario_id,
                metodo,
                caminho,
                status,
                ip,
                duracao_ms
            )
            VALUES (
                %s,
                (SELECT id FROM usuarios WHERE id = %s),
                %s, %s, %s, %s, %s
            );
            """,
            (id_requisicao, usuario_id, metodo, caminho, status, ip, duracao_ms)
        )

        conexao.commit()

        cursor.close()
        conexao.close()

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        logger.error("Erro ao registrar auditoria: %s", erro)


def listar_auditoria(
    usuario_id: int | None = None,
    metodo: str | None = None,
    somente_falhas: bool = False,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    pagina: int = 1,
    tamanho: int = 50
):
    conexao = conectar()

    if conexao is None:
        return None

    condicoes = []
    parametros = []

    if usuario_id is not None:
        condicoes.append("a.usuario_id = %s")
        parametros.append(usuario_id)

    if metodo is not None:
        condicoes.append("a.metodo = %s")
        parametros.append(metodo)

    if somente_falhas:
        condicoes.append("a.status >= 400")

    if data_inicio is not None:
        condicoes.append("a.data_hora >= %s")
        parametros.append(data_inicio)

    if data_fim is not None:
        condicoes.append("a.data_hora < %s")
        parametros.append(data_fim + timedelta(days=1))

    clausula = " WHERE " + " AND ".join(condicoes) if condicoes else ""

    try:
        cursor = conexao.cursor()

        cursor.execute(
            f"SELECT COUNT(*) FROM auditoria a{clausula};",
            tuple(parametros)
        )

        total = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT
                a.id,
                a.data_hora,
                a.id_requisicao,
                a.usuario_id,
                u.nome,
                a.metodo,
                a.caminho,
                a.status,
                a.ip,
                a.duracao_ms
            FROM auditoria a
            LEFT JOIN usuarios u
                ON u.id = a.usuario_id
            {clausula}
            ORDER BY a.id DESC
            LIMIT %s
            OFFSET %s;
            """,
            (*parametros, tamanho, (pagina - 1) * tamanho)
        )

        itens = [
            {
                "id": r[0],
                "data_hora": r[1],
                "id_requisicao": r[2],
                "usuario_id": r[3],
                "usuario": r[4],
                "metodo": r[5],
                "caminho": r[6],
                "status": r[7],
                "ip": r[8],
                "duracao_ms": r[9],
            }
            for r in cursor.fetchall()
        ]

        cursor.close()
        conexao.close()

        return {"total": total, "pagina": pagina, "tamanho": tamanho, "itens": itens}

    except psycopg2.Error as erro:
        conexao.close()

        logger.error("Erro ao listar auditoria: %s", erro)

        return None
