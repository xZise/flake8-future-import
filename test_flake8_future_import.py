from __future__ import print_function

import ast
import codecs
import itertools
import os
import pip
import re
import subprocess
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
            "    print('42 is even')\n"
            "print(sys.version_info)\n"
            "print(path.abspath(__file__))\n")
    for chain in imported:
        code = "from __future__ import {0}\n{1}".format(
            ', '.join(chain), code)
    return code


def reverse_parse(lines, tmp_file=None):
    for line in lines:
        match = re.match(r'([^:]+):(\d+):1: (.*)', line)
        yield int(match.group(2)), match.group(3)
        if tmp_file is not None:
            self.assertEqual(match.group(1), tmp_file)


class TestCaseBase(unittest.TestCase):

    def check_result(self, iterator):
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
        self.assertFalse(found_missing & found_forbidden)
        self.assertFalse(found_missing - all_available)
        self.assertFalse(found_forbidden - all_available)
        return found_missing, found_forbidden

    def run_test(self, iterator, *imported):
        imported = set(itertools.chain(*imported))
        missing = set(flake8_future_import
                      .FutureImportChecker.AVAILABLE_IMPORTS) - imported
        imported &= all_available
        found_missing, found_forbidden = self.check_result(iterator)
        self.assertEqual(found_missing, missing)
        self.assertEqual(found_forbidden, imported - missing)

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
        self.messages += [msg]

    def setUp(self):
        super(TestMainPrintPatched, self).setUp()
        flake8_future_import.print = self.patched_print

    def tearDown(self):
        flake8_future_import.print = print
        super(TestMainPrintPatched, self).tearDown()

    def run_main(self, *imported):
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
        self.run_test(reverse_parse(self.messages), *imported)

    def test_main(self):
        self.run_main()
        self.run_main(['unicode_literals'])
        self.run_main(['unicode_literals', 'division'])
        self.run_main(['unicode_literals'], ['division'])
        self.run_main(['invalid_code'])
        self.run_main(['invalid_code', 'unicode_literals'])


class BadSyntaxMetaClass(type):

    expected_imports = dict((n, set()) for n in range(3, 10))
    expected_imports[10] = set(['absolute_import', 'print_function'])

    def __new__(cls, name, bases, dct):
        def create_test(tree, expected):
            def test(self):
                checker = flake8_future_import.FutureImportChecker(tree, 'fn')
                iterator = self.iterator(checker)
                found_missing, found_forbidden = self.check_result(iterator)
                self.assertEqual(found_missing, all_available - expected)
                self.assertEqual(found_forbidden, expected)
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
                test = create_test(tree, cls.expected_imports[num])
                test.__name__ = str('test_badsyntax_{0}'.format(num))
                dct[test.__name__] = test
                files_found.add(num)

        for not_found in sorted(set(cls.expected_imports) - files_found):
            print('File "badsyntax_future{0}" not found.'.format(not_found))
        return super(BadSyntaxMetaClass, cls).__new__(cls, name, bases, dct)


@six.add_metaclass(BadSyntaxMetaClass)
class BadSyntaxTestCase(TestCaseBase):

    """Test using various bad syntax examples from Python's library."""


class Flake8TestCase(TestCaseBase):

    """
    Test this plugin using flake8.

    This must install it in order for flake8 to be detected and might change the
    current environment. So run it only if "TEST_FLAKE8_INSTALL" is set.
    """

    @classmethod
    def setUpClass(cls):
        for dist in pip.utils.get_installed_distributions():
            if dist.key == 'flake8-future-import':
                if dist.location != os.path.dirname(os.path.abspath(__file__)):
                    raise unittest.SkipTest('The plugin is already installed '
                                            'but somewhere else.')
                cls._installed = False
                break
        else:
            if os.environ.get('TEST_FLAKE8_INSTALL') == '1':
                output = subprocess.check_output(['python', 'setup.py',
                                                  'develop'])
                output = output.decode('utf8')
                print('Installed package:\n\n' + output)
                cls._installed = True
            else:
                raise unittest.SkipTest('The plugin is not installed and '
                                        'TEST_FLAKE8_INSTALL not set')
        super(Flake8TestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        if cls._installed:
            output = subprocess.check_output(['pip', 'uninstall', '-y',
                                              'flake8-future-import'])
            output = output.decode('utf8')
            print('Uninstalled package:\n\n' + output)
        super(Flake8TestCase, cls).tearDownClass()

    def run_flake8(self, *imported):
        code = generate_code(*imported)
        code = '#!/usr/bin/python\n# -*- coding: utf-8 -*-\n' + code
        handle, tmp_file = tempfile.mkstemp()
        try:
            with codecs.open(tmp_file, 'w', 'utf-8') as f:
                f.write(code)
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf8'
            command = ['flake8', tmp_file]
            p = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            data_out, data_err = p.communicate()
        finally:
            os.close(handle)
            os.remove(tmp_file)
        self.assertFalse(data_err)
        self.run_test(reverse_parse(data_out.decode('utf8').splitlines()),
                      *imported)
        self.assertEqual(p.returncode, 1)

    def test_flake8(self):
        self.run_flake8()
        self.run_flake8(['unicode_literals'])
        self.run_flake8(['unicode_literals', 'division'])
        self.run_flake8(['unicode_literals'], ['division'])
        self.run_flake8(['invalid_code'])
        self.run_flake8(['invalid_code', 'unicode_literals'])


if __name__ == '__main__':
    unittest.main()
