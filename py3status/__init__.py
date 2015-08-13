from __future__ import print_function

# Full imports
import ast
import imp
import locale
import sys
import logging

# Partial imports
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime
from json import dumps, loads
from signal import signal
from signal import SIGTERM, SIGUSR1
from subprocess import call
from syslog import syslog, LOG_ERR, LOG_INFO, LOG_WARNING

# Project imports
from profiling import profile
from helpers import print_line, print_stderr
from events import Events
from module import Module
from py3status import Py3status
from logger import logger, initLogger

try:
    from setproctitle import setproctitle
    setproctitle('py3status')
except ImportError:
    pass

@contextmanager
def jsonify(string):
    """
    Transform the given string to a JSON in a context manager fashion.
    """
    prefix = ''
    if string.startswith(','):
        prefix, string = ',', string[1:]
    yield (prefix, loads(string))

def main():
    initLogger()
    logger.debug("Starting py3status")
    try:
        logger.debug("main: Setting locale")
        locale.setlocale(locale.LC_ALL, '')
        logger.debug("main: Setting locale OK")
        logger.debug("main: Initiating py3status")
        py3 = Py3status()
        logger.debug("main: Initiating py3status OK")
        logger.debug("main: Setting py3status up")
        py3.setup()
        logger.debug("main: Setting py3status up OK")
    except KeyboardInterrupt:
        err = sys.exc_info()[1]
        PyErr_Print()
        logger.error("main: Keyboard interrupted setup")
        py3.i3_nagbar('setup interrupted (KeyboardInterrupt)')
        sys.exit(0)
    except Exception as e:
        err = sys.exc_info()[1]
        raise e
        logger.error('setup error ({})'.format(err))
        py3.i3_nagbar('setup error ({})'.format(err))
        py3.stop()
        sys.exit(2)

    try:
        logger.info("main: Running py3status")
        py3.run()
    except Exception:
        err = sys.exc_info()[1]
        py3.i3_nagbar('runtime error ({})'.format(err))
        sys.exit(3)
    except KeyboardInterrupt:
        logger.error("main: Keyboard interrupted run")
        pass
    finally:
        logger.debug("main: Stopping")
        py3.stop()
        sys.exit(0)


if __name__ == '__main__':
    main()
