# Full imports

import sys

# Partial imports
from contextlib import contextmanager
from json import loads


def print_line(line):
    """
    Print given line to stdout.
    """
    sys.__stdout__.write('{}\n'.format(line))
    sys.__stdout__.flush()


def print_stderr(line):
    """
    Print line to stderr.
    """
    print(line, file=sys.stderr)


@contextmanager
def jsonify(string):
    """
    Transform the given string to a JSON in a context manager fashion.
    """
    prefix = ''
    if string.startswith(','):
        prefix, string = ',', string[1:]
    yield (prefix, loads(string))
