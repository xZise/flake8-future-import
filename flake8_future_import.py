#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Extension for flake8 to test for certain __future__ imports"""
from __future__ import print_function

import optparse
import sys

from collections import namedtuple

try:
    import argparse
except ImportError as e:
    argparse = e

import ast

__version__ = '0.4.3'


class FutureImportVisitor(ast.NodeVisitor):

    def __init__(self):
        super(FutureImportVisitor, self).__init__()
        self.future_imports = []

        self._uses_code = False
        self._uses_print = False
        self._uses_division = False
        self._uses_import = False
        self._uses_str_literals = False
        self._uses_generators = False
        self._uses_with = False

    def _is_print(self, node):
        # python 2
        if hasattr(ast, 'Print') and isinstance(node, ast.Print):
            return True

        # python 3
        if isinstance(node, ast.Call) and \
           isinstance(node.func, ast.Name) and \
           node.func.id == 'print':
            return True

        return False

    def visit_ImportFrom(self, node):
        if node.module == '__future__':
            self.future_imports += [node]
        else:
            self._uses_import = True

    def generic_visit(self, node):
        if not isinstance(node, ast.Module):
            self._uses_code = True

        if isinstance(node, ast.Str):
            self._uses_str_literals = True
        elif self._is_print(node):
            self._uses_print = True
        elif isinstance(node, ast.Div):
            self._uses_division = True
        elif isinstance(node, ast.Import):
            self._uses_import = True
        elif isinstance(node, ast.With):
            self._uses_with = True
        elif isinstance(node, ast.Yield):
            self._uses_generators = True

        super(FutureImportVisitor, self).generic_visit(node)

    @property
    def uses_code(self):
        return self._uses_code or self.future_imports


class Flake8Argparse(object):

    @classmethod
    def add_options(cls, parser):
        class Wrapper(object):
            def add_argument(self, *args, **kwargs):
                kwargs.setdefault('parse_from_config', True)
                try:
                    parser.add_option(*args, **kwargs)
                except (optparse.OptionError, TypeError):
                    use_config = kwargs.pop('parse_from_config')
                    option = parser.add_option(*args, **kwargs)
                    if use_config:
                        # flake8 2.X uses config_options to handle stuff like 'store_true'
                        parser.config_options.append(option.get_opt_string().lstrip('-'))

        cls.add_arguments(Wrapper())

    @classmethod
    def add_arguments(cls, parser):
        pass


Feature = namedtuple('Feature', 'index, name, optional, mandatory')

DIVISION = Feature(0, 'division', (2, 2, 0), (3, 0, 0))
ABSOLUTE_IMPORT = Feature(1, 'absolute_import', (2, 5, 0), (3, 0, 0))
WITH_STATEMENT = Feature(2, 'with_statement', (2, 5, 0), (2, 6, 0))
PRINT_FUNCTION = Feature(3, 'print_function', (2, 6, 0), (3, 0, 0))
UNICODE_LITERALS = Feature(4, 'unicode_literals', (2, 6, 0), (3, 0, 0))
GENERATOR_STOP = Feature(5, 'generator_stop', (3, 5, 0), (3, 7, 0))
NESTED_SCOPES = Feature(6, 'nested_scopes', (2, 1, 0), (2, 2, 0))
GENERATORS = Feature(7, 'generators', (2, 2, 0), (2, 3, 0))


# Order important as it defines the error code
ALL_FEATURES = (DIVISION, ABSOLUTE_IMPORT, WITH_STATEMENT, PRINT_FUNCTION,
                UNICODE_LITERALS, GENERATOR_STOP, NESTED_SCOPES, GENERATORS)
FEATURES = dict((feature.name, feature) for feature in ALL_FEATURES)
FEATURE_NAMES = frozenset(feature.name for feature in ALL_FEATURES)
# Make sure the features aren't messed up
assert len(FEATURES) == len(ALL_FEATURES)
assert all(feature.index == index for index, feature in enumerate(ALL_FEATURES))


class FutureImportChecker(Flake8Argparse):

    version = __version__
    name = 'flake8-future-import'
    require_code = True
    min_version = False
    require_used = False

    def __init__(self, tree, filename):
        self.tree = tree

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('--require-code', action='store_true',
                            help='Do only apply to files which not only have '
                                 'comments and (doc)strings')
        parser.add_argument('--min-version', default=False,
                            help='The minimum version supported so that it can '
                                 'ignore mandatory and non-existent features')
        parser.add_argument('--require-used', action='store_true',
                            help='Only alert when relevant features are used')

    @classmethod
    def parse_options(cls, options):
        cls.require_code = options.require_code
        min_version = options.min_version
        if min_version is not False:
            try:
                min_version = tuple(int(num)
                                    for num in min_version.split('.'))
            except ValueError:
                min_version = None
            if min_version is None or len(min_version) > 3:
                raise ValueError('Minimum version "{0}" not formatted '
                                 'like "A.B.C"'.format(options.min_version))
            min_version += (0, ) * (max(3 - len(min_version), 0))
        cls.min_version = min_version
        cls.require_used = options.require_used

    def _generate_error(self, future_import, lineno, present):
        feature = FEATURES.get(future_import)
        if feature is None:
            code = 90
            msg = 'does not exist'
        else:
            if (not present and self.min_version and
                    (feature.mandatory <= self.min_version or
                     feature.optional > self.min_version)):
                return None

            code = 10 + feature.index
            if present:
                msg = 'present'
                code += 40
            else:
                msg = 'missing'
        msg = 'FI{0} __future__ import "{1}" ' + msg
        return lineno, 0, msg.format(code, future_import), type(self)

    def run(self):
        visitor = FutureImportVisitor()
        visitor.visit(self.tree)
        if self.require_code and not visitor.uses_code:
            return
        present = set()
        for import_node in visitor.future_imports:
            for alias in import_node.names:
                err = self._generate_error(alias.name, import_node.lineno, True)
                if err:
                    yield err
                present.add(alias.name)
        for name in FEATURES:
            if name in present:
                continue

            if self.require_used:
                if name == 'print_function' and not visitor._uses_print:
                    continue

                if name == 'division' and not visitor._uses_division:
                    continue

                if name == 'absolute_import' and not visitor._uses_import:
                    continue

                if name == 'unicode_literals' and not visitor._uses_str_literals:
                    continue

                if name == 'generators' and not visitor._uses_generators:
                    continue

                if name == 'with_statement' and not visitor._uses_with:
                    continue

            err = self._generate_error(name, 1, False)
            if err:
                yield err


def main(args):
    if isinstance(argparse, ImportError):
        print('argparse is required for the standalone version.')
        return
    parser = argparse.ArgumentParser()
    choices = set(10 + feature.index for feature in FEATURES.values())
    choices |= set(40 + choice for choice in choices) | set([90])
    choices = set('FI{0}'.format(choice) for choice in choices)
    parser.add_argument('--ignore', help='Ignore the given comma-separated '
                                         'codes')
    FutureImportChecker.add_arguments(parser)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args(args)
    FutureImportChecker.parse_options(args)
    if args.ignore:
        ignored = set(args.ignore.split(','))
        unrecognized = ignored - choices
        ignored &= choices
        if unrecognized:
            invalid = set()
            for invalid_code in unrecognized:
                no_valid = True
                if not invalid:
                    for valid_code in choices:
                        if valid_code.startswith(invalid_code):
                            ignored.add(valid_code)
                            no_valid = False
                if no_valid:
                    invalid.add(invalid_code)
            if invalid:
                raise ValueError('The code(s) is/are invalid: "{0}"'.format(
                    '", "'.join(invalid)))
    else:
        ignored = set()
    has_errors = False
    for filename in args.files:
        with open(filename, 'rb') as f:
            tree = ast.parse(f.read(), filename=filename, mode='exec')
        for line, char, msg, checker in FutureImportChecker(tree,
                                                            filename).run():
            if msg[:4] not in ignored:
                has_errors = True
                print('{0}:{1}:{2}: {3}'.format(filename, line, char + 1, msg))
    return has_errors


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1:]) else 0)
