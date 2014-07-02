import unittest

from s2f import util


class TestUtil(unittest.TestCase):

    def testGetNested(self):
        # non-existing fields
        self.assertIs(util.getNested(7, 'a'), None)
        self.assertIs(util.getNested({}, ''), None)
        self.assertIs(util.getNested({}, 'a'), None)
        self.assertIs(util.getNested({'x': 3}, 'x.y'), None)

        # default value
        self.assertIs(util.getNested(7, 'a', '§'), '§')
        self.assertIs(util.getNested({}, '', 99), 99)
        self.assertIs(util.getNested({'x': 3}, 'x.y', 0), 0)
        self.assertIs(util.getNested({'a': None}, 'a', 'A'), None)

        # existig field
        self.assertIs(util.getNested({'x': 'X'}, 'x'), 'X')
        self.assertIs(util.getNested({'a': {'b': 8}}, 'a.b'), 8)
        self.assertIs(util.getNested({'a': {'': 7}}, 'a.'), 7)
        self.assertIs(util.getNested({'x': 'X'}, 'x', 'Y'), 'X')
