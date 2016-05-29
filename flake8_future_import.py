#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Extension for flake8 to test for certain __future__ imports"""
from __future__ import print_function

import sys

try:
    import argparse
except ImportError as e:
    argparse = e

from ast import NodeVisitor, PyCF_ONLY_AST, Str, Module

__version__ = '0.4.0.dev1'


class FutureImportVisitor(NodeVisitor):

    def __init__(self):
        super(FutureImportVisitor, self).__init__()
        self.future_imports = []
        self._uses_code = False

    def visit_ImportFrom(self, node):
        if node.module == '__future__':
            self.future_imports += [node]

    def visit_Expr(self, node):
        if not isinstance(node.value, Str) or node.value.col_offset != 0:
            self._uses_code = True

    def generic_visit(self, node):
        if not isinstance(node, Module):
            self._uses_code = True
        super(FutureImportVisitor, self).generic_visit(node)

    @property
    def uses_code(self):
        return self._uses_code or self.future_imports


class Flake8Argparse(object):

    @classmethod
    def add_options(cls, parser):
        class Wrapper(object):
            def add_argument(self, *args, **kwargs):
                # flake8 uses config_options to handle stuff like 'store_true'
                for opt in args:
                    if opt.startswith('--'):
                        break
                else:
                    opt = args[0]
                parser.config_options.append(opt.lstrip('-'))
                parser.add_option(*args, **kwargs)

        cls.add_arguments(Wrapper())

    @classmethod
    def add_arguments(cls, parser):
        pass


class Feature(object):

    def __init__(self, index, name, optional, mandatory):
        self.index = index
        self.name = name
        self.optional = optional
        self.mandatory = mandatory


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
# Make sure the features aren't messed up
assert len(FEATURES) == len(ALL_FEATURES)
assert all(feature.index == index for index, feature in enumerate(ALL_FEATURES))


class FutureImportChecker(Flake8Argparse):

    version = __version__
    name = 'flake8-future-import'
    require_code = True
    min_version = False

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

    @classmethod
    def parse_options(cls, options):
        cls.require_code = options.require_code
        min_version = options.min_version
        if min_version is not False:
            try:
                min_version = tuple(int(num)
                                    for num in min_version.split('.'))
            except ValueError:
                raise ValueError('Minimum version "{0}" not formatted '
                                 'like "A.B.C"'.format(min_version))
            min_version += (0, ) * (max(3 - len(min_version), 0))
            # TODO: Warn when longer than 3
        cls.min_version = min_version

    def _generate_error(self, future_import, lineno, present):
        feature = FEATURES.get(future_import)
        if feature is None:
            code = 90
            msg = 'does not exist'
        else:
            if (self.min_version and
                    ((feature.mandatory < self.min_version and not present) or
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
            if name not in present:
                err = self._generate_error(name, 1, False)
                if err:
                    yield err


def main(args):
    if isinstance(argparse, ImportError):
        print('argparse is required for the standalone version.')
        return
    parser = argparse.ArgumentParser()
    choices = set(10 + feature.index for feature in FEATURES.values())
    choices |= set(50 + choice for choice in choices) | set([90, 91])
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
    for filename in args.files:
        with open(filename, 'rb') as f:
            tree = compile(f.read(), filename, 'exec', PyCF_ONLY_AST)
        for line, char, msg, checker in FutureImportChecker(tree,
                                                            filename).run():
            if msg[:4] not in ignored:
                print('{0}:{1}:{2}: {3}'.format(filename, line, char + 1, msg))


if __name__ == '__main__':
    main(sys.argv[1:])
