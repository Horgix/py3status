# Full imports
import logging
import sys

# Partial imports
from subprocess import Popen

log = logging.getLogger('py3status')

class I3nagbarHandler(logging.StreamHandler):
    """
    Logging handler used to display warning and errors with i3-nagbar.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            Popen(
                ['i3-nagbar', '-m', msg, '-t',
                    logging.getLevelName(self.level).lower()],
                stdout=open('/dev/null', 'w'),
                stderr=open('/dev/null', 'w')
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

def init_logger():
    # TODO : add syslog handler
    # Handlers
    stdoutHandler = logging.StreamHandler()
    nagbarHandler = I3nagbarHandler()
    # Formatters
    verboseFormatter = logging.Formatter(
            "%(levelname)5s [%(filename)20s:%(funcName)10s()] - %(message)s"
            )
    # TODO : Make the 'Mod+Shift+R' message parse the i3 config ?
    nagbarFormatter = logging.Formatter(
            "py3status: %(message)s. "
            "Please try to fix this and reload i3wm (Mod+Shift+R)")
    # Levels
    stdoutHandler.setLevel(logging.DEBUG)
    nagbarHandler.setLevel(logging.WARNING)
    # Loggers
    stdoutHandler.setFormatter(verboseFormatter)
    nagbarHandler.setFormatter(nagbarFormatter)
    log.addHandler(stdoutHandler)
    log.addHandler(nagbarHandler)
    # Default level : DEBUG = forward everything to handlers
    log.setLevel(logging.DEBUG)
