from __future__ import print_function

import ast
import codecs
import itertools
import os
import re
import tempfile
import unittest

import flake8_future_import


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


class TestCaseBase(unittest.TestCase):

    def run_test(self, iterator, *imported):
        imported = set(itertools.chain(*imported))
        missing = set(flake8_future_import
                      .FutureImportChecker.AVAILABLE_IMPORTS) - imported
        invalid = imported - set(flake8_future_import
                                 .FutureImportChecker.AVAILABLE_IMPORTS)
        imported -= invalid
        found_missing = set()
        found_forbidden = set()
        for line, msg in iterator:
            match = re.match('FI(\d\d) __future__ import "([a-z_]+)" '
                             '(missing|present)', msg)
            self.assertIsNotNone(match)
            code = int(match.group(1))
            self.assertLess(code, 90)
            self.assertEqual(10 <= code < 50, match.group(3) == 'missing')
            imp = flake8_future_import.FutureImportChecker.AVAILABLE_IMPORTS[
                (code - 10) % 40]
            self.assertEqual(match.group(2), imp)
            if code < 50:
                found_missing.add(imp)
                self.assertEqual(line, 1)
            else:
                found_forbidden.add(imp)
        self.assertEqual(found_missing, missing)
        self.assertEqual(found_forbidden, imported - missing)
        self.assertFalse(found_missing & invalid)
        self.assertFalse(found_forbidden & invalid)


class SimpleImportTestCase(TestCaseBase):

    def run_checker(self, *imported):
        def iterator():
            for line, char, msg, origin in checker.run():
                yield line, msg
                self.assertEqual(char, 0)
                self.assertIs(origin, flake8_future_import.FutureImportChecker)

        tree = ast.parse(generate_code(*imported))
        checker = flake8_future_import.FutureImportChecker(tree, 'fn')
        self.run_test(iterator(), *imported)

    def test_checker(self):
        self.run_checker()
        self.run_checker(['unicode_literals'])
        self.run_checker(['unicode_literals', 'division'])
        self.run_checker(['unicode_literals'], ['division'])
        self.run_checker(['invalid_code'])
        self.run_checker(['invalid_code', 'unicode_literals'])

    def test_main_invalid(self):
        self.assertRaises(ValueError, flake8_future_import.main,
            ['--ignore', 'foobar', '/dev/null'])


class TestMainPrintPatched(TestCaseBase):

    def patched_print(self, msg):
        match = re.match(r'([^:]+):(\d+):1: (.*)', msg)
        self.messages += [match.groups()]

    def setUp(self):
        super(TestMainPrintPatched, self).setUp()
        flake8_future_import.print = self.patched_print

    def tearDown(self):
        flake8_future_import.print = print
        super(TestMainPrintPatched, self).tearDown()

    def run_main(self, *imported):
        def iterator():
            for fn, line, msg in self.messages:
                yield int(line), msg
                self.assertEqual(fn, tmp_file)
        self.messages = []
        code = generate_code(*imported)
        code = '#!/usr/bin/python\n# -*- coding: utf-8 -*-\n' + code
        tmp_file = tempfile.mkstemp()[1]
        try:
            with codecs.open(tmp_file, 'w', 'utf-8') as f:
                f.write(code)
            flake8_future_import.main([tmp_file])
        finally:
            os.remove(tmp_file)
        self.run_test(iterator(), *imported)

    def test_main(self):
        self.run_main()
        self.run_main(['unicode_literals'])
        self.run_main(['unicode_literals', 'division'])
        self.run_main(['unicode_literals'], ['division'])
        self.run_main(['invalid_code'])
        self.run_main(['invalid_code', 'unicode_literals'])


if __name__ == '__main__':
    unittest.main()
