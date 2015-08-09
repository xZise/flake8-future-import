__future__ import checker
=========================

A script to check for the imported __future__ modules to make it easier to have
a consistent code base.

It is possible to select which imports are necessary or not allowed and it'll
output files which violate these rules. The import names provided only need to
be unique. So if the import ``uni`` is necessary it'll check actually for
``unicode_literals``.

This module provides a plugin for ``flake8``, the Python code checker.


Standalone script
-----------------

The checker can be used directly::

  $ python -m flake8-import --necessary-import unicode_literals some_file.py
  some_file.py:0:1: I001 necessary __future__ import "unicode_literals" missing

Even though ``flake8`` still uses ``optparse`` this script in standalone mode
is using ``argparse``.


Plugin for Flake8
-----------------

When both ``flake8 2.0`` and ``flake8-import`` are installed, the plugin is
available in ``flake8``::

  $ flake8 --version
  2.0 (pep8: 1.4.2, future_imports: 0.1, pyflakes: 0.6.1)

By default the plugin won't check the future imports but with
``--necessary-import`` and ``--invalid-import`` it's possible to define which
imports from ``__future__`` are necessary or not allowed. It will emit a
warning if necessary imports are missing or invalid imports a present::

  $ flake8 --necessary-import unicode_literals some_file.py
  ...
  some_file.py:0:1: I001 necessary __future__ import "unicode_literals" missing


Error codes
-----------

This plugin is using the following error codes:

+------+---------------------------------------------+
| I201 | The given import is missing                 |
+------+---------------------------------------------+
| I202 | The given import is present but not allowed |
+------+---------------------------------------------+


Changes
-------

0.1 - 2015-08-08
````````````````
* First release
