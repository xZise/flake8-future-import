# -*- coding: utf-8 -*-
import codecs
import os

from setuptools import setup


def get_version():
    with open('flake8_future_import.py') as f:
        for line in f:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])


def get_long_description():
    with codecs.open('README.rst', 'r', 'utf-8') as f:
        return f.read()


# Install flake8 if that is set as we are going to test with flake8 as well
if os.environ.get('TEST_FLAKE8_INSTALL') == '1':
    tests_require = ['flake8']
else:
    tests_require = []

tests_require += ['six']


setup(
    name='flake8-future-import',
    version=get_version(),
    description='__future__ import checker, plugin for flake8',
    long_description=get_long_description(),
    keywords='flake8 import future',
    install_requires=['flake8'],
    maintainer='Fabian Neundorf',
    maintainer_email='CommodoreFabianus@gmx.de',
    url='https://github.com/xZise/flake8-future-import',
    license='MIT License',
    py_modules=['flake8_future_import'],
    zip_safe=False,
    entry_points={
        'flake8.extension': [
            'flake8-future-import = flake8_future_import:FutureImportChecker',
        ],
    },
    tests_require=tests_require,
    test_suite='test_flake8_future_import',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Quality Assurance',
    ],
)
