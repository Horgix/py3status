from __future__ import print_function

# Full imports
import locale
import sys

# Project imports
from profiling import profile
from helpers import print_line, print_stderr
from module import Module
from py3status import Py3status
from logger import log, initLogger

try:
    from setproctitle import setproctitle
    setproctitle('py3status')
except ImportError:
    pass

def main():
    """
    Error exit codes :
        - 0 : OK
        - 1 : CLI command error
        - 2 : Exception during setup
        - 3 : Exception during run
    """
    initLogger() # Initialize global logger
    log.info("Starting py3status")
    try:
        log.info("Setting locale")
        locale.setlocale(locale.LC_ALL, '')
        log.info("Instantiating py3status")
        py3 = Py3status()
        log.info("Setting py3status up")
        py3.setup()
    except KeyboardInterrupt:
        #err = sys.exc_info()[1]
        log.warning("Setup interrupted (KeyboardInterrupt Exception)")
        #py3.i3_nagbar('Setup interrupted (KeyboardInterrupt)')
        sys.exit(0)
    except Exception as e:
        log.error('Setup error : {}'.format(e))
        #py3.i3_nagbar('setup error ({})'.format(err))
        py3.stop()
        sys.exit(2)

    try:
        log.info("Running py3status")
        py3.run()
    except IOError as e:
        log.error("Caught IOError : {}".format(e))
        sys.exit(3)
    except KeyboardInterrupt as e:
        log.error("Run interrupted (KeyboardInterrupted Exception)")
        pass
    except Exception as e:
        log.error("Caught Exception : {}".format(e))
        #py3.i3_nagbar('runtime error ({})'.format(err))
        sys.exit(3)
    finally:
        log.debug("Stopping py3status")
        py3.stop()
        sys.exit(0)


if __name__ == '__main__':
    main()
