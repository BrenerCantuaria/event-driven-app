import logging
from logging.handlers import RotatingFileHandler
import os

# Diretório onde os logs serão salvos
LOG_DIR = "infra/logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "system.log")

def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado com:
    - Logs no console
    - Logs em arquivo rotativo (até 5 MB por arquivo, 5 backups)
    - Formatação padronizada
    """
    logger = logging.getLogger(name)

    # Evita configuração duplicada ao chamar get_logger várias vezes
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # Nível mínimo de log

    # Formato padrão
    log_format = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # --- Console Handler ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(log_format)

    # --- File Handler com rotação ---
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    # Adiciona handlers ao logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Exemplo de uso interno
if __name__ == "__main__":
    log = get_logger("TEST_LOGGER")
    log.info("Logger configurado com sucesso!")
    log.warning("Aviso de teste!")
    log.error("Erro de teste!")
