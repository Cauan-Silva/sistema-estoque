import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


FORMATO = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configurar_logs():
    """Logs no console e em logs/app.log (até 5 arquivos de 5 MB)."""
    raiz = logging.getLogger()

    if getattr(raiz, "_estoque_configurado", False):
        return

    nivel = os.getenv("LOG_LEVEL", "INFO").upper()
    formato = logging.Formatter(FORMATO)

    console = logging.StreamHandler()
    console.setFormatter(formato)
    raiz.addHandler(console)

    pasta = Path(
        os.getenv("LOG_DIR")
        or Path(__file__).resolve().parent.parent / "logs"
    )

    try:
        pasta.mkdir(parents=True, exist_ok=True)

        arquivo = RotatingFileHandler(
            pasta / "app.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        arquivo.setFormatter(formato)
        raiz.addHandler(arquivo)

    except OSError as erro:
        raiz.warning("Não foi possível gravar logs em arquivo: %s", erro)

    raiz.setLevel(nivel)
    raiz._estoque_configurado = True
