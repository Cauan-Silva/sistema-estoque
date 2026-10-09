from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.database import RAIZ_PROJETO, aplicar_migracoes, conectar


def versao_mais_recente():
    configuracao = Config(str(RAIZ_PROJETO / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ_PROJETO / "migrations"))
    return ScriptDirectory.from_config(configuracao).get_current_head()


def versao_do_banco():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT version_num FROM alembic_version;")
    versao = cursor.fetchone()[0]
    cursor.close()
    conexao.close()
    return versao


def test_banco_esta_na_versao_mais_recente():
    assert versao_do_banco() == versao_mais_recente()


def test_aplicar_migracoes_de_novo_nao_altera_nada():
    antes = versao_do_banco()

    aplicar_migracoes()

    assert versao_do_banco() == antes


def test_ha_uma_unica_versao_final():
    configuracao = Config(str(RAIZ_PROJETO / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ_PROJETO / "migrations"))

    assert len(ScriptDirectory.from_config(configuracao).get_heads()) == 1
