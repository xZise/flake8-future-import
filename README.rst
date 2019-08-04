__future__ import checker
=========================

.. image:: https://secure.travis-ci.org/xZise/flake8-future-import.png?branch=0.4.6
   :alt: Build Status
   :target: https://travis-ci.org/xZise/flake8-future-import

.. image:: https://codecov.io/gh/xZise/flake8-future-import/branch/master/graph/badge.svg
   :alt: Coverage Status
   :target: https://codecov.io/gh/xZise/flake8-future-import

.. image:: https://badge.fury.io/py/flake8-future-import.svg
   :alt: Pypi Entry
   :target: https://pypi.python.org/pypi/flake8-future-import

A script to check for the imported ``__future__`` modules to make it easier to
have a consistent code base.

By default it requires and forbids all imports but it's possible to have
certain imports optional by ignoring both their requiring and forbidding error
code. In the future it's planned to have a “consistency” mode and that the
default is having the import optional or required (not sure on that yet).

This module provides a plugin for ``flake8``, the Python code checker.


Standalone script
-----------------

The checker can be used directly::

  $ python -m flake8-import --ignore FI10,FI11,FI12,FI13,FI15,FI5 some_file.py
  some_file.py:1:1: FI14 __future__ import "unicode_literals" missing

Even though ``flake8`` still uses ``optparse`` this script in standalone mode
is using ``argparse``.


Plugin for Flake8
-----------------

When both ``flake8 2.0`` and ``flake8-future-imports`` are installed, the plugin
is available in ``flake8``::

  $ flake8 --version
  3.5.0 (flake8-future-imports: 0.4.6, mccabe: 0.6.1, pycodestyle: 2.3.1, pyflakes: 1.6.0)

By default the plugin will check for all the future imports but with
``--ignore`` it's possible to define which imports from ``__future__`` are
optional, required or forbidden. It will emit a warning if necessary imports
are missing::

  $ flake8 --ignore FI10,FI11,FI12,FI13,FI15,FI5 some_file.py
  ...
  some_file.py:1:1: FI14 __future__ import "unicode_literals" missing


Parameters
----------

This module adds one parameter:

* ``--require-code``: Doesn't complain on files which only contain comments or
  strings (and by extension docstrings). Corresponds to ``require-code = True``
  in the ``tox.ini``.
* ``--min-version``: Define the minimum version supported by the project. Any
  features already mandatory or not available won't cause a warning when they
  are missing. Corresponds to ``min-version = …`` in the ``tox.ini``.

The stand alone version also mimics flake8's ignore parameter.


Error codes
-----------

This plugin is using the following error codes:

+------+--------------------------------------------------+
| FI10 | ``__future__`` import "division" missing         |
+------+--------------------------------------------------+
| FI11 | ``__future__`` import "absolute_import" missing  |
+------+--------------------------------------------------+
| FI12 | ``__future__`` import "with_statement" missing   |
+------+--------------------------------------------------+
| FI13 | ``__future__`` import "print_function" missing   |
+------+--------------------------------------------------+
| FI14 | ``__future__`` import "unicode_literals" missing |
+------+--------------------------------------------------+
| FI15 | ``__future__`` import "generator_stop" missing   |
+------+--------------------------------------------------+
| FI16 | ``__future__`` import "nested_scopes" missing    |
+------+--------------------------------------------------+
| FI17 | ``__future__`` import "generators" missing       |
+------+--------------------------------------------------+
| FI12 | ``__future__`` import "annotations" missing      |
+------+--------------------------------------------------+
+------+--------------------------------------------------+
| FI50 | ``__future__`` import "division" present         |
+------+--------------------------------------------------+
| FI51 | ``__future__`` import "absolute_import" present  |
+------+--------------------------------------------------+
| FI52 | ``__future__`` import "with_statement" present   |
+------+--------------------------------------------------+
| FI53 | ``__future__`` import "print_function" present   |
+------+--------------------------------------------------+
| FI54 | ``__future__`` import "unicode_literals" present |
+------+--------------------------------------------------+
| FI55 | ``__future__`` import "generator_stop" present   |
+------+--------------------------------------------------+
| FI56 | ``__future__`` import "nested_scopes" present    |
+------+--------------------------------------------------+
| FI57 | ``__future__`` import "generators" present       |
+------+--------------------------------------------------+
| FI58 | ``__future__`` import "annotations" present      |
+------+--------------------------------------------------+
+------+--------------------------------------------------+
| FI90 | ``__future__`` import does not exist             |
+------+--------------------------------------------------+

For a sensible usage, for each import either or both error code need to be
ignored as it will otherwise always complain either because it's present or
because it is not. The corresponding other error code can be determined by
adding or subtracting 40.

* Ignoring the **lower** one will **forbid** the import
* Ignoring the **higher** one will **require** the import
* Ignoring **both** will make the import **optional**

The plugin is always producing errors about missing and present imports and
``flake8`` actually does ignore then the codes accordingly. So the plugin does
not know that an import is allowed and forbidden at the same time and thus
cannot skip reporting those imports.


Changes
-------

0.4.6 - 2019-08-04
``````````````````
* Add new ``annotations`` feature.

0.4.5 - 2018-04-15
``````````````````
* Support pip version 10 in the tests.
* Add ``LICENSE`` and ``test_flake8_future_import.py`` to the source
  distribution.

0.4.4 - 2018-01-05
``````````````````
* Add ``Flake8`` framework classifier.

0.4.3 - 2016-07-01
``````````````````
* When using Flake8 version 2, it wasn't correctly looking for the options in
  the ``tox.ini`` file. This is restoring the old behaviour there.

0.4.2 - 2016-07-01
``````````````````
* Support flake8 version 3's new config option interface
* Do not increase offset by one in the standalone variant, like flake8 does
  with version 3

0.4.1 - 2016-05-30
``````````````````
* Do not ignore imports which are present and have been added after the minimum
  version
* Ignore imports which became mandatory with the minimum version

0.4.0 - 2016-05-30
``````````````````
* Add two older ``future`` imports
* Issue an error when a future import does not exist
* Define which is the oldest Python version to be supported so that already
  mandatory features can be ignored and not yet supported features default to
  forbidden (ignoring the lower error code).
* Use return code of 1 if errors occurred

0.3.2 - 2015-10-18
``````````````````
* Prevent errors when using unknown future imports
* Test several examples for bad future imports from the Python library
* Fixed the README to use present for the higher codes

0.3.1 - 2015-09-07
``````````````````
* Support setting ``--require-code`` in the ``tox.ini``

0.3.0 - 2015-09-07
``````````````````
* Using a different error code namespace (FIXX)
* Add error codes returned when an import is present
* Removed ``nested_scopes`` and ``generators`` from the available list
* Skip files which only contains comments and strings

0.2.1 - 2015-08-10
``````````````````
* Fixed the module and URL in setup.py
* Fixed the name in the script itself

0.2 - 2015-08-10
````````````````
* Instead of parameters it's now using error codes to define which futures are
  missing. This is removing the ability to forbid a future for now.

0.1 - 2015-08-08
````````````````
* First release
