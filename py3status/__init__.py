from __future__ import print_function

# Full imports
import locale
import sys

# Partial imports
from collections import OrderedDict
from subprocess import call

# Project imports
from profiling import profile
from helpers import print_line, print_stderr
from module import Module
from py3status import Py3status
from logger import logger, initLogger

try:
    from setproctitle import setproctitle
    setproctitle('py3status')
except ImportError:
    pass


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
    except IOError as e:
        logger.error("main: Caught IOError", e)
        sys.exit(3)
    except KeyboardInterrupt as e:
        logger.error("main: Caught KeyboardInterrupted")
        pass
    except Exception as e:
        logger.error("main: Caught Exception", e)
        sys.exit(2)
        err = sys.exc_info()[1]
        logger.info(sys.exc_info())
        logger.error("main: runtime error ({})".format(sys.exc_info()[2]))
        traceback.print_tb(sys.exc_info()[2])
        raise e
        py3.i3_nagbar('runtime error ({})'.format(err))
        sys.exit(3)
    finally:
        logger.debug(sys.exc_info())
        logger.debug("main: Stopping")
        py3.stop()
        sys.exit(0)


if __name__ == '__main__':
    main()
