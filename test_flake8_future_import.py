from __future__ import print_function

import ast
import codecs
import itertools
import os
import re
import tempfile
import unittest

import six

import flake8_future_import

all_available = set(flake8_future_import.FutureImportChecker.AVAILABLE_IMPORTS)


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

    def check_result(self, iterator):
        found_missing = set()
        found_forbidden = set()
        found_invalid = set()
        for line, msg in iterator:
            match = re.match(r'FI(\d\d) __future__ import "([^"]+)" '
                             r'(missing|present|does not exist)', msg)
            self.assertIsNotNone(match, 'Line "{0}" did not match.'.format(msg))
            code = int(match.group(1))
            if code < 90:
                self.assertIs(10 <= code < 50, match.group(3) == 'missing')
                imp = flake8_future_import.FutureImportChecker.AVAILABLE_IMPORTS[
                    (code - 10) % 40]
                self.assertEqual(match.group(2), imp)
                if code < 50:
                    found_missing.add(imp)
                    self.assertEqual(line, 1)
                else:
                    found_forbidden.add(imp)
            else:
                self.assertEqual(code, 90)
                found_invalid.add(match.group(2))
        self.assertFalse(found_missing & found_forbidden)
        self.assertFalse(found_missing & found_invalid)
        self.assertFalse(found_forbidden & found_invalid)
        self.assertFalse(found_invalid & all_available)
        return found_missing, found_forbidden, found_invalid

    def run_test(self, iterator, *imported):
        imported = set(itertools.chain(*imported))
        missing = set(flake8_future_import
                      .FutureImportChecker.AVAILABLE_IMPORTS) - imported
        invalid = imported - all_available
        imported -= invalid
        found_missing, found_forbidden, found_invalid = self.check_result(iterator)
        self.assertEqual(found_missing, missing)
        self.assertEqual(found_forbidden, imported - missing)
        self.assertEqual(found_invalid, invalid)

    def iterator(self, checker):
        for line, char, msg, origin in checker.run():
            yield line, msg
            self.assertEqual(char, 0)
            self.assertIs(origin, flake8_future_import.FutureImportChecker)


class SimpleImportTestCase(TestCaseBase):

    def run_checker(self, *imported):
        tree = ast.parse(generate_code(*imported))
        checker = flake8_future_import.FutureImportChecker(tree, 'fn')
        self.run_test(self.iterator(checker), *imported)

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


class BadSyntaxMetaClass(type):

    expected_imports = dict((n, (set(), set())) for n in range(4, 8))
    expected_imports[3] = (set(), set(['rested_snopes']))
    expected_imports[8] = (set(), set(['*']))
    expected_imports[9] = (set(), set(['braces']))
    expected_imports[10] = (set(['absolute_import', 'print_function']), set())
    for n in range(3, 10):
        if n == 8:
            continue
        expected_imports[n][0].add('nested_scopes')

    def __new__(cls, name, bases, dct):
        def create_test(tree, expected, filename):
            def test(self):
                checker = flake8_future_import.FutureImportChecker(tree,
                                                                   filename)
                iterator = self.iterator(checker)
                found_missing, found_forbidden, found_invalid = self.check_result(iterator)
                self.assertEqual(found_missing, all_available - expected[0])
                self.assertEqual(found_forbidden, expected[0])
                self.assertEqual(found_invalid, expected[1])
            return test

        files_found = set()
        for fn in os.listdir(os.path.dirname(os.path.abspath(__file__))):
            m = re.match('^badsyntax_future(\d+).py$', fn)
            if m:
                num = int(m.group(1))
                if num not in cls.expected_imports:
                    print('File "{0}" is not expected'.format(fn))
                with open(fn, 'rb') as f:
                    tree = compile(f.read(), fn, 'exec', ast.PyCF_ONLY_AST)
                test = create_test(tree, cls.expected_imports[num], fn)
                test.__name__ = str('test_badsyntax_{0}'.format(num))
                dct[test.__name__] = test
                files_found.add(num)

        for not_found in sorted(set(cls.expected_imports) - files_found):
            print('File "badsyntax_future{0}" not found.'.format(not_found))
        return super(BadSyntaxMetaClass, cls).__new__(cls, name, bases, dct)


@six.add_metaclass(BadSyntaxMetaClass)
class BadSyntaxTestCase(TestCaseBase):

    """Test using various bad syntax examples from Python's library."""


if __name__ == '__main__':
    unittest.main()
