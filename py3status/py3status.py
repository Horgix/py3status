# Full imports

import sys
import os
import argparse

# Partial imports
from time import sleep, time
from threading import Event
from copy import deepcopy
from json import dumps
from signal import signal, SIGTERM, SIGUSR1

# Project imports
from profiling import profile
from logger import logger
from i3status_wrapper import I3status
from events import Events


class Py3status():
    """
    This is the py3status wrapper around i3status.
    """
    def __init__(self):
        """
        Useful variables we'll need.
        """
        logger.debug("Initializing py3status")
        self.last_refresh_ts = time()
        self.lock = Event()
        self.modules = {}
        self.py3_modules = []
        logger.debug("Initializing py3status OK")

    def get_config(self):
        """
        Create the py3status based on command line options we received.
        """
        # get home path
        home_path = os.path.expanduser('~')

        # defaults
        config = {
            'cache_timeout': 60,
            'include_paths': ['{}/.i3/py3status/'.format(home_path)],
            'interval': 1
        }

        # package version
        try:
            import pkg_resources
            version = pkg_resources.get_distribution('py3status').version
        except:
            version = 'unknown'
        config['version'] = version

        # i3status config file default detection
        # respect i3status' file detection order wrt issue #43
        i3status_config_file_candidates = [
            '{}/.i3status.conf'.format(home_path),
            '{}/.config/i3status/config'.format(
                os.environ.get('XDG_CONFIG_HOME', home_path)
            ),
            '/etc/i3status.conf',
            '{}/i3status/config'.format(
                os.environ.get('XDG_CONFIG_DIRS', '/etc/xdg')
            )
        ]
        for fn in i3status_config_file_candidates:
            if os.path.isfile(fn):
                i3status_config_file_default = fn
                break
        else:
            # if none of the default files exists, we will default
            # to ~/.i3/i3status.conf
            i3status_config_file_default = '{}/.i3/i3status.conf'.format(
                home_path
            )

        # command line options
        parser = argparse.ArgumentParser(
            description='The agile, python-powered, i3status wrapper')
        parser = argparse.ArgumentParser(add_help=True)
        parser.add_argument('-c', '--config', action="store",
                            dest="i3status_conf",
                            type=str,
                            default=i3status_config_file_default,
                            help="path to i3status config file")
        parser.add_argument('-d', '--debug', action="store_true",
                            help="be verbose in syslog")
        parser.add_argument('-i', '--include', action="append",
                            dest="include_paths",
                            help="""include user-written modules from those
                            directories (default ~/.i3/py3status)""")
        parser.add_argument('-n', '--interval', action="store",
                            dest="interval",
                            type=float,
                            default=config['interval'],
                            help="update interval in seconds (default 1 sec)")
        parser.add_argument('-s', '--standalone', action="store_true",
                            help="standalone mode, do not use i3status")
        parser.add_argument('-t', '--timeout', action="store",
                            dest="cache_timeout",
                            type=int,
                            default=config['cache_timeout'],
                            help="""default injection cache timeout in seconds
                            (default 60 sec)""")
        parser.add_argument('-v', '--version', action="store_true",
                            help="""show py3status version and exit""")
        parser.add_argument('cli_command', nargs='*', help=argparse.SUPPRESS)

        options = parser.parse_args()

        if options.cli_command:
            config['cli_command'] = options.cli_command

        # only asked for version
        if options.version:
            from platform import python_version
            print(
                'py3status version {} (python {})'.format(
                    config['version'],
                    python_version()
                )
            )
            sys.exit(0)

        # override configuration and helper variables
        config['cache_timeout'] = options.cache_timeout
        config['debug'] = options.debug
        if options.include_paths:
            config['include_paths'] = options.include_paths
        config['interval'] = int(options.interval)
        config['standalone'] = options.standalone
        config['i3status_config_path'] = options.i3status_conf

        # all done
        return config

    def get_user_modules(self):
        """
        Search import directories and files through include paths with
        respect to i3status.conf configured py3status modules.

        User provided modules take precedence over py3status generic modules.

        If no module has been requested from i3status.conf, we'll load
        every module present in the include paths
        as this is the legacy behavior.
        """
        user_modules = dict()
        for include_path in sorted(self.config['include_paths']):
            include_path = os.path.abspath(include_path) + '/'
            if not os.path.isdir(include_path):
                continue

            for f_name in sorted(os.listdir(include_path)):
                if not f_name.endswith('.py'):
                    continue

                module_name = f_name[:-3]

                if self.py3_modules:
                    # i3status.conf based behaviour (using order += 'xx')
                    for module in self.py3_modules:
                        if module_name == module.split(' ')[0]:
                            user_modules[module_name] = (include_path, f_name)
                else:
                    # legacy behaviour (load everything)
                    user_modules[module_name] = (include_path, f_name)
        return user_modules

    def load_modules(self, modules_list, user_modules):
        """
        Load the given modules from the list (contains instance name) with
        respect to the user provided modules dict.

        modules_list: ['weather_yahoo paris', 'net_rate']
        user_modules: {
            'weather_yahoo': ('/etc/py3status.d/', 'weather_yahoo.py')
        }
        """
        for module in modules_list:
            # ignore already provided modules (prevents double inclusion)
            if module in self.modules:
                continue
            try:
                my_m = Module(
                    self.lock,
                    self.config,
                    module,
                    self.i3status_thread,
                    user_modules
                )
                # only start and handle modules with available methods
                if my_m.methods:
                    my_m.start()
                    self.modules[module] = my_m
                elif self.config['debug']:
                    logger.info(
                        'ignoring module "{}" (no methods found)'.format(
                            module
                        )
                    )
            except Exception:
                err = sys.exc_info()[1]
                logger.warning('loading module "{}" failed ({})'
                               .format(module, err))
                self.i3_nagbar(msg, level='warning')

    def setup(self):
        """
        Setup py3status and spawn i3status/events/modules threads.
        """
        logger.debug("Setting up py3status")
        # set the Event lock
        self.lock.set()

        # setup configuration
        logger.debug("setup: getting configuration")
        self.config = self.get_config()
        logger.debug("setup: getting configuration OK")

        if self.config.get('cli_command'):
            logger.info("Got cli_command from config")
            self.handle_cli_command(self.config['cli_command'])
            sys.exit()

        if self.config['debug']:
            logger.info("Started with config {}".format(self.config))

        # setup i3status thread
        self.i3status_thread = I3status(
            self.lock,
            self.config['i3status_config_path'],
            self.config['standalone']
        )
        if self.config['standalone']:
            self.i3status_thread.mock()
        else:
            self.i3status_thread.start()
            while not self.i3status_thread.ready:
                if not self.i3status_thread.is_alive():
                    err = self.i3status_thread.error
                    raise IOError(err)
                sleep(0.1)
        if self.config['debug']:
            logger.info(
                'i3status thread {} with config {}'.format(
                    'started' if not self.config['standalone'] else 'mocked',
                    self.i3status_thread.config
                )
            )

        # setup input events thread
        self.events_thread = Events(
            self.lock,
            self.config,
            self.modules,
            self.i3status_thread.config
        )
        self.events_thread.start()
        if self.config['debug']:
            logger.info('events thread started')

        # suppress modules' ouput wrt issue #20
        if not self.config['debug']:
            sys.stdout = open('/dev/null', 'w')
            sys.stderr = open('/dev/null', 'w')

        # get the list of py3status configured modules
        self.py3_modules = self.i3status_thread.config['py3_modules']

        # get a dict of all user provided modules
        user_modules = self.get_user_modules()
        if self.config['debug']:
            logger.info('user_modules={}'.format(user_modules))

        if self.py3_modules:
            # load and spawn i3status.conf configured modules threads
            self.load_modules(self.py3_modules, user_modules)
        else:
            # legacy behaviour code
            # load and spawn user modules threads based on inclusion folders
            self.load_modules(user_modules, user_modules)

    def i3_nagbar(self, msg, level='error'):
        """
        Make use of i3-nagbar to display errors and warnings to the user.
        We also make sure to log anything to keep trace of it.
        """
        msg = 'py3status: {}. '.format(msg)
        msg += 'please try to fix this and reload i3wm (Mod+Shift+R)'
        try:
            if level == 'error':
                logger.error(msg)
            else:
                logger.warning(msg)
            Popen(
                ['i3-nagbar', '-m', msg, '-t', level],
                stdout=open('/dev/null', 'w'),
                stderr=open('/dev/null', 'w')
            )
        except:
            pass

    def stop(self):
        """
        Clear the Event lock, this will break all threads' loops.
        """
        try:
            self.lock.clear()
            if self.config['debug']:
                logger.info('lock cleared, exiting')
            self.i3status_thread.cleanup_tmpfile()
        except:
            pass

    def sig_handler(self, signum, frame):
        """
        SIGUSR1 was received, the user asks for an immediate refresh of the bar
        so we force i3status to refresh by sending it a SIGUSR1
        and we clear all py3status modules' cache.

        To prevent abuse, we rate limit this function to 100ms.
        """
        if time() > (self.last_refresh_ts + 0.1):
            logger.info('received USR1, forcing refresh')

            # send SIGUSR1 to i3status
            call(['killall', '-s', 'USR1', 'i3status'])

            # clear the cache of all modules
            self.clear_modules_cache()

            # reset the refresh timestamp
            self.last_refresh_ts = time()
        else:
            logger.info(
                'received USR1 but rate limit is in effect, calm down'
            )

    def clear_modules_cache(self):
        """
        For every module, reset the 'cached_until' of all its methods.
        """
        for module in self.modules.values():
            module.clear_cache()

    def get_modules_output(self, json_list):
        """
        Iterate over user modules and their output. Return the list ordered
        as the user asked.
        If two modules specify the same output index/position, the sorting will
        be alphabetical.
        """
        # prepopulate the list so that every usable index exists, thx @Lujeni
        m_list = [
            '' for value in range(
                sum([len(x.methods) for x in self.modules.values()]) +
                len(json_list)
            )
        ]

        # run through modules/methods output and insert them in reverse order
        debug_msg = ''
        for m in reversed(list(self.modules.values())):
            for meth in m.methods:
                position = m.methods[meth]['position']
                last_output = m.methods[meth]['last_output']
                try:
                    assert position in range(len(m_list))
                    if m_list[position] == '':
                        m_list[position] = last_output
                    else:
                        if '' in m_list:
                            m_list.remove('')
                        m_list.insert(position, last_output)
                except (AssertionError, IndexError):
                    # out of range indexes get placed at the end of the output
                    m_list.append(last_output)
                finally:
                    # debug user module's index
                    if self.config['debug']:
                        debug_msg += '{}={} '.format(
                            meth,
                            m_list.index(last_output)
                        )

        # append i3status json list to the modules' list in empty slots
        debug_msg = ''
        for i3s_json in json_list:
            for i in range(len(m_list)):
                if m_list[i] == '':
                    m_list[i] = i3s_json
                    break
            else:
                # this should not happen !
                m_list.append(i3s_json)

            # debug i3status module's index
            if self.config['debug']:
                debug_msg += '{}={} '.format(
                    i3s_json['name'],
                    m_list.index(i3s_json)
                )

        # cleanup and return output list, we also remove empty outputs
        m_list = list(filter(lambda a: a != '' and a['full_text'], m_list))

        # log the final ordering in debug mode
        if self.config['debug']:
            logger.info(
                'ordering result {}'.format([m['name'] for m in m_list])
            )

        # return the ordered result
        return m_list

    def terminate(self, signum, frame):
        """
        Received request to terminate (SIGTERM), exit nicely.
        """
        raise KeyboardInterrupt()

    @profile
    def run(self):
        """
        Main py3status loop, continuously read from i3status and modules
        and output it to i3bar for displaying.
        """
        # SIGUSR1 forces a refresh of the bar both for py3status and i3status,
        # this mimics the USR1 signal handling of i3status (see man i3status)
        signal(SIGUSR1, self.sig_handler)
        signal(SIGTERM, self.terminate)

        # initialize usage variables
        delta = 0
        last_delta = -1
        previous_json_list = []

        # main loop
        while True:
            # check i3status thread
            if not self.i3status_thread.is_alive():
                err = self.i3status_thread.error
                if not err:
                    err = 'i3status died horribly'
                self.i3_nagbar(err)
                break

            # check events thread
            if not self.events_thread.is_alive():
                # don't spam the user with i3-nagbar warnings
                if not hasattr(self.events_thread, 'i3_nagbar'):
                    self.events_thread.i3_nagbar = True
                    err = 'events thread died, click events are disabled'
                    self.i3_nagbar(err, level='warning')

            # check that every module thread is alive
            for module in self.modules.values():
                if not module.is_alive():
                    # don't spam the user with i3-nagbar warnings
                    if not hasattr(module, 'i3_nagbar'):
                        module.i3_nagbar = True
                        msg = 'output frozen for dead module(s) {}'.format(
                            ','.join(module.methods.keys())
                        )
                        self.i3_nagbar(msg, level='warning')

            # get output from i3status
            prefix = self.i3status_thread.last_prefix
            json_list = deepcopy(self.i3status_thread.json_list)

            # transform time and tztime outputs from i3status
            # every configured interval seconds
            if (
                self.config['interval'] <= 1 or (
                    int(delta) % self.config['interval'] == 0 and
                    int(last_delta) != int(delta)
                )
            ):
                delta = 0
                last_delta = 0
                json_list = self.i3status_thread.tick_time_modules(
                    json_list,
                    force=True
                )
            else:
                json_list = self.i3status_thread.tick_time_modules(
                    json_list,
                    force=False
                )

            # construct the global output
            if self.modules:
                if self.py3_modules:
                    # new style i3status configured ordering
                    json_list = self.i3status_thread.get_modules_output(
                        json_list,
                        self.modules
                    )
                else:
                    # old style ordering
                    json_list = self.get_modules_output(json_list)

            # dump the line to stdout only on change
            if json_list != previous_json_list:
                logger.debug('{}{}'.format(prefix, dumps(json_list)))

            # remember the last json list output
            previous_json_list = deepcopy(json_list)

            # reset i3status json_list and json_list_ts
            self.i3status_thread.update_json_list()

            # sleep a bit before doing this again to avoid killing the CPU
            delta += 0.1
            sleep(0.1)

    @staticmethod
    def print_module_description(details, mod_name, mod_path):
        """Print module description extracted from its docstring.
        """
        if mod_name == '__init__':
            return

        path = os.path.join(*mod_path)
        try:
            with open(path) as f:
                module = ast.parse(f.read())

            docstring = ast.get_docstring(module, clean=True)
            if docstring:
                short_description = docstring.split('\n')[0].rstrip('.')
                logger.debug('  %-22s %s.' % (mod_name, short_description))
                if details:
                    for description in docstring.split('\n')[1:]:
                        logger.debug(' ' * 25 + '%s' % description)
                    logger.debug(' ' * 25 + '---')
            else:
                logger.debug('  %-22s No docstring in %s' % (mod_name, path))
        except Exception:
            logger.warning('  %-22s Unable to parse %s' % (mod_name, path))

    def handle_cli_command(self, cmd):
        """Handle a command from the CLI.
        """
        # aliases
        if cmd[0] in ['mod', 'module', 'modules']:
            cmd[0] = 'modules'

        # allowed cli commands
        if cmd[:2] in (['modules', 'list'], ['modules', 'details']):
            try:
                py3_modules_path = imp.find_module('py3status')[1]
                py3_modules_path += '/modules/'
                if os.path.isdir(py3_modules_path):
                    self.config['include_paths'].append(py3_modules_path)
            except:
                print_stderr('Unable to locate py3status modules !')

            details = cmd[1] == 'details'
            user_modules = self.get_user_modules()

            print_stderr('Available modules:')
            for mod_name, mod_path in sorted(user_modules.items()):
                self.print_module_description(details, mod_name, mod_path)
        elif cmd[:2] in (['modules', 'enable'], ['modules', 'disable']):
            # TODO: to be implemented
            pass
        else:
            print_stderr('Error: unknown command')
            sys.exit(1)
