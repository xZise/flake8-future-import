#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Extension for flake8 to test for certain __future__ imports"""
import sys

try:
    import argparse
except ImportError as e:
    argparse = e

from ast import NodeVisitor, PyCF_ONLY_AST

__version__ = '0.3'


class FutureImportVisitor(NodeVisitor):

    def __init__(self):
        super(FutureImportVisitor, self).__init__()
        self.future_imports = []

    def visit_ImportFrom(self, node):
        if node.module == '__future__':
            self.future_imports += [node]


class FutureImportChecker(object):

    # Order important as it defines the error code
    AVAILABLE_IMPORTS = ('division', 'absolute_import', 'with_statement',
                         'print_function', 'unicode_literals', 'generator_stop')

    version = __version__
    name = 'flake8-future-import'

    def __init__(self, tree, filename):
        self.tree = tree

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
        present = set()
        for import_node in visitor.future_imports:
            for alias in import_node.names:
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
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
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
