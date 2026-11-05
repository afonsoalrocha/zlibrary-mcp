"""Local privacy patch: no file logs and no default debug logging."""
import logging
import sys

logger = logging.getLogger("zlibrary")
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
    handler.close()
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.ERROR)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.ERROR)
logger.propagate = False
