"""
Helpers for this package.
"""

import logging
import time


SForceCfgFileName = 'config/sforce-config.json'
SForceTokenFileName = 'config/sforce-token.json'


def setupLogging():
    """
    Set up logging for an application.

    Call this function only once, e.g. from your program's main module,
    before any code (your own, or library code) logs anything.

    https://docs.python.org/3.4/howto/logging-cookbook.html
    """
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


def getNested(dictObj, dotPath, default=None):
    """
    Return the value nested at dotPath if present, or default.

    dotPath is a string 'field1.field2.….fieldn' and this function returns
    dictObj[field1][field2]…[fieldn].
    dictObj can e.g. come from parsing JSON.
    """
    fieldNames = dotPath.split('.')
    def get(obj, fieldsArr, default):
        if not fieldsArr:
            return obj
        if type(obj) != dict:
            return default
        nextField = fieldsArr[0]
        fieldsArr = fieldsArr[1:]
        if nextField not in obj:
            return default
        return get(obj[nextField], fieldsArr, default)
    return get(dictObj, dotPath.split('.'), default)
