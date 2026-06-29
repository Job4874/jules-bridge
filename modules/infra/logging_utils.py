import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from collections import deque

REQUEST_LOG: deque = deque(maxlen=200)

def configure_logging(log_path, root_dir):
    if getattr(configure_logging, "configured", False):
        return
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    os.makedirs(root_dir, exist_ok=True)
    fh = RotatingFileHandler(log_path, maxBytes=10_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(formatter)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    root_logger.addHandler(fh)
    root_logger.addHandler(sh)
    configure_logging.configured = True
