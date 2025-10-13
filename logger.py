import logging
from logging.handlers import RotatingFileHandler
import os

LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("APP_LOG_FILE", "club_house.log")
MAX_BYTES = int(os.getenv("APP_LOG_MAX_BYTES", 5 * 1024 * 1024))
BACKUP_COUNT = int(os.getenv("APP_LOG_BACKUP_COUNT", 3))

def get_logger(name: str = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"))
    logger.addHandler(ch)

    fh = RotatingFileHandler(LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"))
    logger.addHandler(fh)

    logger.propagate = False
    return logger