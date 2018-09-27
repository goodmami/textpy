#!/usr/bin/env python3

from distutils.core import setup
from Cython.Build import cythonize

setup(
  name = 'textpy',
  ext_modules = cythonize("textpy/_scanners.pyx"),
)
