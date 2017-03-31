#!/usr/bin/env python3

from distutils.core import setup
from Cython.Build import cythonize

# setup(
#   name = 'grammarian_',
#   ext_modules = cythonize("grammarian_.pyx"),
# )
setup(
  name = 'grammarian',
  ext_modules = cythonize("grammarian/_scanners.pyx"),
)
