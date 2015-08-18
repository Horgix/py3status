# Full imports
import sys
import logging
import logging.handlers

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
    # Handlers
    stdoutHandler = logging.StreamHandler()
    nagbarHandler = I3nagbarHandler()
    syslogHandler = logging.handlers.SysLogHandler(address='/dev/log')
    # Formatters
    stdoutFormatter = logging.Formatter(
            "%(levelname)5s [%(filename)20s:%(funcName)10s()] - %(message)s"
            )
    nagbarFormatter = logging.Formatter(
            "py3status: %(message)s. "
            "Please try to fix this and reload i3wm (Mod+Shift+R)")
            # TODO : Make the 'Mod+Shift+R' message parse the i3 config ?
    syslogFormatter = logging.Formatter("%(message)s")
    # Levels
    stdoutHandler.setLevel(logging.DEBUG)
    nagbarHandler.setLevel(logging.WARNING)
    syslogHandler.setLevel(logging.DEBUG)
    # Loggers
    stdoutHandler.setFormatter(stdoutFormatter)
    nagbarHandler.setFormatter(nagbarFormatter)
    syslogHandler.setFormatter(syslogFormatter)
    log.addHandler(stdoutHandler)
    log.addHandler(nagbarHandler)
    log.addHandler(syslogHandler)
    # Default level : DEBUG = forward everything to handlers
    log.setLevel(logging.DEBUG)
