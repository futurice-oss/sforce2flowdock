#! /usr/bin/env python3

import argparse
import json
import logging
import os, os.path
import socket
import sys
import time

from s2f import util
import s2f.s2f


def setupLogging():
    """
    Set up logging.

    https://docs.python.org/3.4/howto/logging-cookbook.html
    """
    # Log UTC times
    logging.Formatter.converter = time.gmtime
    # Show the timezone
    formatter = logging.Formatter(
            '%(asctime)s %(levelname)s:%(name)s:%(message)s',
            "%Y-%m-%d %H:%M:%S %z (%Z)")

    fileH = logging.RotatingFileHandler('s2f.log', encoding='utf-8',
            maxBytes=1024*1024*1, backupCount=5)
    fileH.setFormatter(formatter)

    rootL = logging.getLogger()
    rootL.setLevel(logging.INFO)
    rootL.addHandler(fileH)

setupLogging()

def getLogger():
    return logging.getLogger(__name__)


PORT = 19876
cfgFiles = ('sforce-config.json', 'sforce-token.json', 'flowdock-config.json',
        'limits.json')
stateFileName = 'state.json'


def parseArgs():
    p = argparse.ArgumentParser(description='''Fetch new activity from
            SalesForce and post it to FlowDock.''')
    p.add_argument('config_dir', help='''A directory where this program can
            load configuration files from and where it can write a state file
            to. Configuration files: ''' + ', '.join(cfgFiles) + '''.
            State file: ''' + stateFileName + '''.''')
    return p.parse_args()


def singleinstance(port):
    """
    Provides mutual exclusion by binding a socket. Returns success.

    Not destined for multithreaded use from the same process, but to be called
    once by each process to ensure it is the only instance running.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))

        # prevent a successfully bound socket from being garbage collected,
        # otherwise a second process might be able to bind to the same port
        # while we are still running
        global __bound_sock
        __bound_sock = sock

        return True
    except socket.error:
        return False


if __name__ == '__main__':
    args = parseArgs()
    if not singleinstance(PORT):
        getLogger().warn('Another instance is already running, exiting')
        sys.exit(0)

    sCfg, sTok, fCfg, lim = map(lambda p: os.path.join(args.config_dir, p),
            cfgFiles)
    stateF = os.path.join(args.config_dir, stateFileName)

    state = {}
    try:
        with open(stateF, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except FileNotFoundError:
        pass
    updatesUrl = util.getNested(state, 'updatesUrl')

    state['updatesUrl'] = s2f.s2f.postNewOpportunities(sCfg, sTok, fCfg, lim,
            util.getNested(state, 'updatesUrl'))

    with open(stateF, 'w', encoding='utf-8') as f:
        json.dump(state, f)
