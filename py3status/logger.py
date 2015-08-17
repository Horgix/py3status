# Full imports
import logging

log = logging.getLogger('py3status')


def initLogger():
    stdoutHandler = logging.StreamHandler()
    #stdoutFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stdoutFormatter = logging.Formatter("%(levelname)5s [%(filename)20s:%(funcName)10s()] - %(message)s")

    stdoutHandler.setLevel(logging.DEBUG)

    stdoutHandler.setFormatter(stdoutFormatter)
    log.addHandler(stdoutHandler)
    log.setLevel(logging.DEBUG)
