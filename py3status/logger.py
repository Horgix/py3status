# Full imports
import logging

logger = logging.getLogger()

def initLogger():
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
