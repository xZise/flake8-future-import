#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Extension for flake8 to test for certain __future__ imports"""
try:
    import argparse
except ImportError as e:
    argparse = e

import sys

from ast import NodeVisitor, PyCF_ONLY_AST

__version__ = '0.1'


class FutureImportVisitor(NodeVisitor):

    def __init__(self):
        super(FutureImportVisitor, self).__init__()
        self.future_imports = []

    def visit_ImportFrom(self, node):
        if node.module == '__future__':
            self.future_imports += [node]


class FutureImportChecker(object):

    AVAILABLE_IMPORTS = ('nested_scopes', 'generators', 'division',
                         'absolute_import', 'with_statement',
                         'print_function', 'unicode_literals')

    ERROR_CODES = {
        201: 'necessary __future__ import "{0}" missing',
        202: '__future__ import "{0}" not allowed'
    }

    version = __version__
    name = 'future-imports'

    def __init__(self, tree, filename):
        self.tree = tree

    @classmethod
    def add_options(cls, parser):
        if isinstance(parser, argparse.ArgumentParser):
            add_meth = parser.add_argument
        else:
            add_meth = parser.add_option
        add_meth('--necessary-import', action='append', default=[],
                 help='List of __future__ imports which are necessary.')
        add_meth('--invalid-import', action='append', default=[],
                 help='List of __future__ imports which are not allowed.')

    @classmethod
    def _normalize_imports(cls, imports):
        unknown = []
        converted = []
        for imp in imports:
            candidates = []
            for available_import in cls.AVAILABLE_IMPORTS:
                if available_import == imp:
                    break
                elif imp in available_import:
                    candidates += [available_import]
            else:
                if len(candidates) == 1:
                    available_import = candidates[0]
                else:
                    unknown += [imp]
                    continue

            converted += [available_import]
        return set(converted), unknown

    @classmethod
    def parse_options(cls, options):
        necessary, unknown_necessary = cls._normalize_imports(
            options.necessary_import)
        invalid, unknown_invalid = cls._normalize_imports(
            options.invalid_import)
        unknown = unknown_necessary + unknown_invalid
        if unknown:
            raise ValueError('Unknown imports "{0}"'.format(
                '", "'.join(unknown)))
        cls.necessary_imports = necessary
        cls.invalid_imports = invalid
        conflicting = cls.necessary_imports & cls.invalid_imports
        if conflicting:
            raise ValueError('The selected import(s) "{0}" conflict'.format(
                '", "'.join(conflicting)))

    def _generate_error(self, code, lineno, *args, **kwargs):
        msg = self.ERROR_CODES[code].format(*args, **kwargs)
        return lineno, 0, 'I{0:0>3} {1}'.format(code, msg), type(self)

    def run(self):
        visitor = FutureImportVisitor()
        visitor.visit(self.tree)
        missing = set(self.necessary_imports)
        for import_node in visitor.future_imports:
            for alias in import_node.names:
                if alias.name in self.invalid_imports:
                    yield self._generate_error(202, import_node.lineno,
                                               alias.name)
                else:
                    missing.discard(alias.name)
        for name in sorted(missing):
            yield self._generate_error(201, 1, name)


def main(args):
    if isinstance(argparse, ImportError):
        print('argparse is required for the standalone version.')
        return
    parser = argparse.ArgumentParser()
    FutureImportChecker.add_options(parser)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    FutureImportChecker.parse_options(args)
    for filename in args.files:
        with open(filename, 'rb') as f:
            tree = compile(f.read(), filename, 'exec', PyCF_ONLY_AST)
        for error_line in FutureImportChecker(tree, filename).run():
            print('{0}:{1}:{2}: {3}'.format(filename, *error_line[:3]))


if __name__ == '__main__':
    main(sys.argv[1:])
