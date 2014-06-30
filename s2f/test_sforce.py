import unittest

from s2f.sforce import SClient
from s2f import util


util.setupLogging()


class TestClient(unittest.TestCase):

    def test_getAPIVersions(self):
        client = SClient(util.SForceCfgFileName, util.SForceTokenFileName)
        self.assertTrue(len(client.getAPIVersions()) > 0)

    def test_getAvailableResources(self):
        client = SClient(util.SForceCfgFileName, util.SForceTokenFileName)
        self.assertTrue(len(client.getAvailableResources().keys()) > 0)
