#! /usr/bin/env python3
import json
from s2f.sforce import SClient
from s2f import util

"""
Print SalesForce API versions.

Use this to set the version in the config file JSON.
"""

if __name__ == '__main__':
    util.setupLogging()
    client = SClient(util.SForceCfgFileName, util.SForceTokenFileName)
    print(json.dumps(client.getAPIVersions(), indent=2))
