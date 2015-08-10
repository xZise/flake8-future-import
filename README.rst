__future__ import checker
=========================

A script to check for the imported __future__ modules to make it easier to have
a consistent code base.

By default it requires all imports but it's possible to have certain imports
optional by ignoring their error code. In the future it's planned to have a
“consistency” mode and to forbid certain imports (by ignoring the even error
codes).

This module provides a plugin for ``flake8``, the Python code checker.


Standalone script
-----------------

The checker can be used directly::

  $ python -m flake8-import --ignore I301,I303,I305,I307,I309,I311 some_file.py
  some_file.py:0:1: I313 __future__ import "unicode_literals" missing

Even though ``flake8`` still uses ``optparse`` this script in standalone mode
is using ``argparse``.


Plugin for Flake8
-----------------

When both ``flake8 2.0`` and ``flake8-future-imports`` are installed, the plugin
is available in ``flake8``::

  $ flake8 --version
  2.0 (pep8: 1.4.2, flake8-future-imports: 0.1, pyflakes: 0.6.1)

By default the plugin will check for all the future imports but with
``--ignore`` it's possible to define which imports from ``__future__`` are
optional. It will emit a warning if necessary imports are missing::

  $ flake8 --ignore I301,I303,I305,I307,I309,I311 some_file.py
  ...
  some_file.py:0:1: I313 __future__ import "unicode_literals" missing


Error codes
-----------

This plugin is using the following error codes:

+------+----------------------------------------------+
| I301 | __future__ import "nested_scopes" missing    |
+------+----------------------------------------------+
| I303 | __future__ import "generators" missing       |
+------+----------------------------------------------+
| I305 | __future__ import "division" missing         |
+------+----------------------------------------------+
| I307 | __future__ import "absolute_import" missing  |
+------+----------------------------------------------+
| I309 | __future__ import "with_statement" missing   |
+------+----------------------------------------------+
| I311 | __future__ import "print_function" missing   |
+------+----------------------------------------------+
| I313 | __future__ import "unicode_literals" missing |
+------+----------------------------------------------+


Changes
-------

0.2 - 2015-08-10
````````````````
* Instead of parameters it's now using error codes to define which futures are
  missing. This is removing the ability to forbid a future for now.

0.1 - 2015-08-08
````````````````
* First release
