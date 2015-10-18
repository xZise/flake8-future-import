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

__version__ = '0.3.2'


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
                if kwargs['action'] == 'store_true':
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


class FutureImportChecker(Flake8Argparse):

    # Order important as it defines the error code
    AVAILABLE_IMPORTS = ('division', 'absolute_import', 'with_statement',
                         'print_function', 'unicode_literals', 'generator_stop')

    version = __version__
    name = 'flake8-future-import'
    require_code = True

    def __init__(self, tree, filename):
        self.tree = tree

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('--require-code', action='store_true',
                            help='Do only apply to files which not only have '
                                 'comments and (doc)strings')

    @classmethod
    def parse_options(cls, options):
        cls.require_code = options.require_code

    def _generate_error(self, future_import, lineno, present):
        code = 10 + self.AVAILABLE_IMPORTS.index(future_import)
        if present:
            msg = 'FI{0} __future__ import "{1}" present'
            code += 40
        else:
            msg = 'FI{0} __future__ import "{1}" missing'
        return lineno, 0, msg.format(code, future_import), type(self)

    def run(self):
        visitor = FutureImportVisitor()
        visitor.visit(self.tree)
        if self.require_code and not visitor.uses_code:
            return
        present = set()
        for import_node in visitor.future_imports:
            for alias in import_node.names:
                if alias.name not in self.AVAILABLE_IMPORTS:
                    # unknown code
                    continue
                yield self._generate_error(alias.name, import_node.lineno, True)
                present.add(alias.name)
        for name in self.AVAILABLE_IMPORTS:
            if name not in present:
                yield self._generate_error(name, 1, False)


def main(args):
    if isinstance(argparse, ImportError):
        print('argparse is required for the standalone version.')
        return
    parser = argparse.ArgumentParser()
    choices = set('FI' + str(10 + choice) for choice in
                  range(len(FutureImportChecker.AVAILABLE_IMPORTS)))
    choices |= set('FI' + str(50 + choice) for choice in
                   range(len(FutureImportChecker.AVAILABLE_IMPORTS)))
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
