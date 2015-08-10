import ast
import itertools
import re
import unittest

from flake8_future_import import FutureImportChecker


def generate_code(*imported):
    code = ("import sys\n"
            "from os import path\n"
            "print('Hello World')\n"
            "if 42 % 2 == 0:\n"
            "    print('42 is even')")
    for chain in imported:
        code = "from __future__ import {0}\n{1}".format(
            ', '.join(chain), code)
    return code


def check_message(testcase, msg):
    # TODO: Do subclassing instead
    match = re.match('FI(\d\d) __future__ import "([a-z_]+)" '
                     '(missing|present)', msg)
    testcase.assertIsNotNone(match)
    code = int(match.group(1))
    testcase.assertLess(code, 90)
    testcase.assertEqual(10 <= code < 50, match.group(3) == 'missing')
    imp = FutureImportChecker.AVAILABLE_IMPORTS[(code - 10) % 40]
    testcase.assertEqual(match.group(2), imp)
    return code < 50, imp


class SimpleImportTestCase(unittest.TestCase):

    def run_test(self, *imported):
        tree = ast.parse(generate_code(*imported))
        imported = set(itertools.chain(*imported))
        missing = set(FutureImportChecker.AVAILABLE_IMPORTS) - imported
        checker = FutureImportChecker(tree, 'fn')
        found_missing = set()
        found_forbidden = set()
        for line, char, msg, origin in checker.run():
            is_missing, imp = check_message(self, msg)
            if is_missing:
                found_missing.add(imp)
                self.assertEqual(line, 1)
            else:
                found_forbidden.add(imp)
            self.assertEqual(char, 0)
            self.assertIs(origin, FutureImportChecker)
        self.assertEqual(found_missing, missing)
        self.assertEqual(found_forbidden, imported - missing)

    def test_allow_none(self):
        self.run_test()
        self.run_test(['unicode_literals'])
        self.run_test(['unicode_literals', 'division'])
        self.run_test(['unicode_literals'], ['division'])


if __name__ == '__main__':
    unittest.main()
