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
        self.assertTrue(len(client.getCompanyChatter(maxPages=1)[0]) >= 0)

    def test_getOpportunitiesChatter(self):
        client = getSClient()
        opChatter, upUrl = client.getOpportunitiesChatter(maxPages=1)
        self.assertTrue(len(opChatter) >= 0)

    def testGetOpportunitiesChatterDetails(self):
        client = getSClient()
        details, upUrl = client.getOpportunitiesChatterDetails(maxPages=1,
                maxOpportunities=1)
        self.assertTrue(len(details) >= 0)

    def testGetOpportunities(self):
        client = getSClient()
        self.assertTrue(len(client.getOpportunities()) >= 0)
        self.assertTrue(len(client.getOpportunities(
            minModified='2014-01-01T00:00:00.000+0000')) >= 0)
