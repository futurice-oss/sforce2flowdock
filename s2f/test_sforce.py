import unittest

from s2f.sforce import SClient


class TestClient(unittest.TestCase):

    def test_getAPIVersions(self):
        c = SClient()
        c.apiInstanceName = 'na1'
        self.assertTrue(len(c.getAPIVersions()) > 0)
