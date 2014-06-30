#! /usr/bin/env python3

# Example of logging in an application.
# The main executable configures logging, and all (library) modules just log.
# https://docs.python.org/3.4/howto/logging-cookbook.html

import logging
import time

from s2f import hellolog


def setupLogging():
    # Log UTC times
    logging.Formatter.converter = time.gmtime
    # Show the timezone
    formatter = logging.Formatter(
            '%(asctime)s %(levelname)s:%(name)s:%(message)s',
            "%Y-%m-%d %H:%M:%S %z (%Z)")

    consoleH = logging.StreamHandler()
    consoleH.setFormatter(formatter)

    rootL = logging.getLogger()
    rootL.setLevel(logging.INFO)
    rootL.addHandler(consoleH)


if __name__ == '__main__':
    setupLogging()
    hellolog.sayHello()
