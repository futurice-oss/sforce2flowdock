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
        """
        first = True
        for op in opChatter:
            if first:
                first = False
            else:
                print()
            for dotPath, label in {
                'parent.name': 'Opportunity name',
                'body.text': 'Text',
                'modifiedDate': 'When',
                'parent.url': 'Opportunity URL',
                'actor.name': 'Who',
                'type': 'Type',
                'preamble.text': 'Preamble',
                    }.items():
                print(label + ':', util.getNested(op, dotPath, '¡NOT FOUND!'))
        """
        self.assertTrue(len(opChatter) >= 0)
