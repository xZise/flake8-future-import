from __future__ import print_function

import __future__
import ast
import codecs
import itertools
import os
import pkg_resources
import re
import subprocess
import sys
import tempfile

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import six

import flake8_future_import


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


class TestCaseBase(unittest.TestCase):

    def check_result(self, iterator):
        found_missing = set()
        found_forbidden = set()
        found_invalid = set()
        for line, msg in iterator:
            match = re.match(r'FI(\d\d) __future__ import "([^"]+)" '
                             r'(missing|present|does not exist)', msg)
            # Ignore all errors which aren't from this plugin
            if match is not None:
                code = int(match.group(1))
                if code < 90:
                    self.assertIs(10 <= code < 50, match.group(3) == 'missing')
                    imp = flake8_future_import.ALL_FEATURES[(code - 10) % 40].name
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
        self.assertFalse(found_invalid & flake8_future_import.FEATURE_NAMES)
        return found_missing, found_forbidden, found_invalid

    def run_test(self, iterator, imported, ignore_present=set(),
                 ignore_missing=set()):
        # assert that the ignored names are valid
        assert not (ignore_present - flake8_future_import.FEATURE_NAMES)
        assert not (ignore_missing - flake8_future_import.FEATURE_NAMES)
        imported = set(itertools.chain(*imported))
        missing = flake8_future_import.FEATURE_NAMES - imported
        invalid = imported - flake8_future_import.FEATURE_NAMES
        imported -= invalid
        found_missing, found_forbidden, found_invalid = self.check_result(iterator)
        self.assertEqual(found_missing, missing - ignore_missing)
        self.assertEqual(found_forbidden, imported - missing - ignore_present)
        self.assertEqual(found_invalid, invalid)

    def iterator(self, checker):
        for line, char, msg, origin in checker.run():
            yield line, msg
            self.assertEqual(char, 0)
            self.assertIs(origin, flake8_future_import.FutureImportChecker)

    def reverse_parse(self, lines, tmp_file=None):
        for line in lines:
            match = re.match(r'((?:[A-Z]:)?[^:]+):(\d+):1: (.*)', line)
            yield int(match.group(2)), match.group(3)
            if tmp_file is not None:
                self.assertEqual(match.group(1), tmp_file)


class SimpleImportTestCase(TestCaseBase):

    def run_checker(self, *imported):
        tree = ast.parse(generate_code(*imported))
        checker = flake8_future_import.FutureImportChecker(tree, 'fn')
        self.run_test(self.iterator(checker), imported)

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


class MinVersionTestCase(TestCaseBase):

    @classmethod
    def setUpClass(cls):
        super(MinVersionTestCase, cls).setUpClass()
        cls._min_version = flake8_future_import.FutureImportChecker.min_version

    @classmethod
    def tearDownClass(cls):
        flake8_future_import.FutureImportChecker.min_version = cls._min_version
        super(MinVersionTestCase, cls).tearDownClass()

    def run_checker(self, min_version, ignored, *imported):
        tree = ast.parse(generate_code(*imported))
        flake8_future_import.FutureImportChecker.min_version = min_version
        checker = flake8_future_import.FutureImportChecker(tree, 'fn')
        self.run_test(self.iterator(checker), imported, ignore_missing=ignored)

    def test_mandatory_and_unavailable(self):
        """Do not care about already mandatory or not yet available features."""
        self.run_checker(
            (2, 6, 0),
            set(['nested_scopes', 'generators', 'with_statement', 'generator_stop', 'annotations']),
            ('unicode_literals', ))

    def test_use_of_unavailable(self):
        """Use an import which is to new for the minimum version."""
        self.run_checker(
            (2, 6, 0),
            set(['nested_scopes', 'generators', 'with_statement', 'annotations']),
            ('generator_stop', ))


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
        handle, tmp_file = tempfile.mkstemp()
        try:
            os.write(handle, code.encode('utf-8'))
            flake8_future_import.main([tmp_file])
        finally:
            os.close(handle)
            os.remove(tmp_file)
        self.run_test(self.reverse_parse(self.messages), imported)

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
                self.assertEqual(found_missing, flake8_future_import.FEATURE_NAMES - expected[0])
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
                    tree = ast.parse(f.read(), filename=fn, mode='exec')
                test = create_test(tree, cls.expected_imports[num], fn)
                test.__name__ = str('test_badsyntax_{0}'.format(num))
                dct[test.__name__] = test
                files_found.add(num)

        for not_found in sorted(set(cls.expected_imports) - files_found):
            print('File "badsyntax_future{0}" not found.'.format(not_found))
        return super(BadSyntaxMetaClass, cls).__new__(cls, name, bases, dct)


@six.add_metaclass(BadSyntaxMetaClass)
class TestBadSyntax(TestCaseBase):

    """Test using various bad syntax examples from Python's library."""


@unittest.skipIf(sys.version_info[:2] >= (3, 7), 'flake8 supports up to 3.6')
class Flake8TestCase(TestCaseBase):

    """
    Test this plugin using flake8.

    This must install it in order for flake8 to be detected and might change the
    current environment. So run it only if "TEST_FLAKE8_INSTALL" is set.
    """

    @classmethod
    def setUpClass(cls):
        for dist in pkg_resources.working_set:
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
                # Indent output by one tab to hightlight where it is
                output = re.sub('^(?!\s)', '\t', output, flags=re.M)
                print('Installed package:\n\n' + output + '\n\n')
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
        handle, tmp_file = tempfile.mkstemp(suffix='.py')
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
        self.run_test(self.reverse_parse(data_out.decode('utf8').splitlines(), tmp_file),
                      imported)
        self.assertEqual(p.returncode, 1)

    def test_flake8(self):
        self.run_flake8()
        self.run_flake8(['unicode_literals'])
        self.run_flake8(['unicode_literals', 'division'])
        self.run_flake8(['unicode_literals'], ['division'])
        self.run_flake8(['invalid_code'])
        self.run_flake8(['invalid_code', 'unicode_literals'])


class FeaturesMetaClass(type):

    def __new__(cls, name, bases, dct):
        def create_existing_test(feat_name):
            def test(self):
                self.assertIn(feat_name, flake8_future_import.FEATURES)
                py_feat = getattr(__future__, feat_name)
                my_feat = flake8_future_import.FEATURES[feat_name]
                self.assertEqual(my_feat.optional, py_feat.optional[:3])
                self.assertEqual(my_feat.mandatory, py_feat.mandatory[:3])
            return test

        def create_to_new_test(feat_name):
            def test(self):
                self.assertGreater(
                    flake8_future_import.FEATURES[feat_name].optional,
                    sys.version_info[:3])
            return test

        # Verify that Python didn't mess up all_feature_names
        assert not set(__future__.all_feature_names) ^ set(feat for feat in dir(__future__)
                                                           if not feat.isupper() and feat[0] != '_' and
                                                           feat != 'all_feature_names')

        for feat in __future__.all_feature_names:
            if feat == 'barry_as_FLUFL':
                continue  # thank you April's Foul
            test = create_existing_test(feat)
            test.__name__ = str('test_{0}'.format(feat))
            test.__doc__ = 'Verify the feature versions.'
            dct[test.__name__] = test

        for missing_feat in (set(flake8_future_import.FEATURES) -
                             set(__future__.all_feature_names)):
            test = create_to_new_test(missing_feat)
            test.__name__ = str('test_{0}'.format(missing_feat))
            test.__doc__ = 'Verify that the feature is not newer than current.'
            dct[test.__name__] = test
        return super(FeaturesMetaClass, cls).__new__(cls, name, bases, dct)


@six.add_metaclass(FeaturesMetaClass)
class TestFeatures(TestCaseBase):

    """Verify that the features are up to date."""


if __name__ == '__main__':
    unittest.main()
