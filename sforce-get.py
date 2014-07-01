#! /usr/bin/env python3

import argparse
import json
from s2f.sforce import SClient
from s2f import util


def parseArgs():
    p = argparse.ArgumentParser(description='Print JSON from SalesForce URL')
    p.add_argument('url', help='''SalesForce URL to GET JSON from.
            If relative, it's interpreted as relative to the API root.
            You can start the exploration by passing an empty string ''
            for this argument.
            ''')
    return p.parse_args()


if __name__ == '__main__':
    args = parseArgs()
    util.setupLogging()
    client = SClient(util.SForceCfgFileName, util.SForceTokenFileName)
    print(json.dumps(client.getJson(args.url), indent=2))
