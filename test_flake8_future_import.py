import ast
import re
import unittest

from flake8_import import FutureImportChecker


class SimpleImportTestCase(unittest.TestCase):

    @staticmethod
    def _generate_code(imported):
        code = ("import sys\n"
                "from os import path\n"
                "print('Hello World')\n"
                "if 42 % 2 == 0:\n"
                "    print('42 is even')")
        if imported:
            code = "from __future__ import {0}\n{1}".format(
                ', '.join(imported), code)
        return code

    def run_test(self, imported):
        tree = ast.parse(self._generate_code(imported))
        missing = set(FutureImportChecker.AVAILABLE_IMPORTS) - set(imported)
        checker = FutureImportChecker(tree, 'fn')
        found_missing = set()
        for line, char, msg, origin in checker.run():
            match = re.match('I(3[01][1-9]) __future__ import "([a-z_]+)".*', msg)
            self.assertIsNotNone(match)
            self.assertEqual(int(match.group(1)) % 2, 1)
            self.assertEqual(line, 1)
            imp = checker.AVAILABLE_IMPORTS[(int(match.group(1)) - 301) // 2]
            self.assertEqual(match.group(2), imp)
            self.assertEqual(char, 0)
            self.assertIs(origin, FutureImportChecker)
            found_missing.add(imp)
        self.assertEqual(found_missing, missing)

    def test_allow_none(self):
        self.run_test([])
        self.run_test(['unicode_literals'])
        self.run_test(['unicode_literals', 'division'])


if __name__ == '__main__':
    unittest.main()
