#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Extension for flake8 to test for certain __future__ imports"""
import sys

try:
    import argparse
except ImportError as e:
    argparse = e

from ast import NodeVisitor, PyCF_ONLY_AST

__version__ = '0.2'


class FutureImportVisitor(NodeVisitor):

    def __init__(self):
        super(FutureImportVisitor, self).__init__()
        self.future_imports = []

    def visit_ImportFrom(self, node):
        if node.module == '__future__':
            self.future_imports += [node]


class FutureImportChecker(object):

    # Order important as it defines the error code
    AVAILABLE_IMPORTS = ('nested_scopes', 'generators', 'division',
                         'absolute_import', 'with_statement',
                         'print_function', 'unicode_literals')

    version = __version__
    name = 'future-imports'

    def __init__(self, tree, filename):
        self.tree = tree

    def _generate_error(self, future_import, lineno):
        code = 301 + self.AVAILABLE_IMPORTS.index(future_import) * 2
        msg = 'I{0} __future__ import "{1}" missing'.format(code, future_import)
        return lineno, 0, msg, type(self)

    def run(self):
        visitor = FutureImportVisitor()
        visitor.visit(self.tree)
        present = set()
        for import_node in visitor.future_imports:
            for alias in import_node.names:
                present.add(alias.name)
        for name in self.AVAILABLE_IMPORTS:
            if name not in present:
                yield self._generate_error(name, 1)


def main(args):
    if isinstance(argparse, ImportError):
        print('argparse is required for the standalone version.')
        return
    parser = argparse.ArgumentParser()
    choices = set('I' + str(301 + choice * 2) for choice in
                  range(len(FutureImportChecker.AVAILABLE_IMPORTS)))
    parser.add_argument('--ignore', help='Ignore the given comma-separated '
                                         'codes')
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    if args.ignore:
        ignored = args.ignore.split(',')
        invalid = set(ignored) - choices
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
            if msg[:4] not in args.ignore:
                print('{0}:{1}:{2}: {3}'.format(filename, line, char + 1, msg))


if __name__ == '__main__':
    main(sys.argv[1:])
