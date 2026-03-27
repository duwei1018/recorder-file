# utils/logger.py
import logging
import sys
from pathlib import Path

def setup_logger(log_file: str = "C:\\Users\\Administrator\\recorder-file\\agent.log") -> logging.Logger:
    logger = logging.getLogger("recorder_file")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger

log = setup_logger()
