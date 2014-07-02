import unittest

from s2f.sforce import SClient
from s2f import util


util.setupLogging()


def getSClient():
    return SClient(util.SForceCfgFileName, util.SForceTokenFileName)


class TestClient(unittest.TestCase):

    def test_getAPIVersions(self):
        client = getSClient()
        self.assertTrue(len(client.getAPIVersions()) > 0)

    def test_getAvailableResources(self):
        client = getSClient()
        self.assertTrue(len(client.getAvailableResources().keys()) > 0)

    def test_getCompanyChatter(self):
        client = getSClient()
        self.assertTrue(len(client.getCompanyChatter()) >= 0)

    def test_getOpportunitiesChatter(self):
        client = getSClient()
        opChatter = client.getOpportunitiesChatter()
        self.assertTrue(len(opChatter) >= 0)

    def testGetOpportunitiesChatterDetails(self):
        client = getSClient()
        details = client.getOpportunitiesChatterDetails(maxPages=1)
        self.assertTrue(len(details) >= 0)
