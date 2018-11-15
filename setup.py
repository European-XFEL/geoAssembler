#!/usr/bin/env python
import os.path as osp
import re
from setuptools import setup, find_packages
import sys


def get_script_path():
    return osp.dirname(osp.realpath(sys.argv[0]))


def read(*parts):
    return open(osp.join(get_script_path(), *parts)).read()


def find_version(*parts):
    vers_file = read(*parts)
    match = re.search(r'^__version__ = "(\d+\.\d+\.\d+)"', vers_file, re.M)
    if match is not None:
        return match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(name="geoAssembler",
      version=find_version("geoAssembler", "__init__.py"),
      author="European XFEL GmbH",
      author_email="cas-support@xfel.eu",
      maintainer="Martin Bergemann",
      url="https://git.xfel.eu/gitlab/dataAnalysis/geoAssembler",
      description="Tool to calibrate Detector Geometry based on Power diffraction pattern",
      long_description=read("README.md"),
      license="BSD-3-Clause",
      packages=find_packages(),
      install_requires=[
          'cfelpyutils',
          'matplotlib',
          'numpy',
          'pyqtgraph',
      ],
      extras_require={
          'docs': [
              'sphinx',
              'nbsphinx',
              'ipython',  # For nbsphinx syntax highlighting
          ],
          'test': [
              'pytest',
              'testpath',
          ]
      },
      python_requires='>=3.4',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Topic :: Scientific/Engineering :: Information Analysis',
          'Topic :: Scientific/Engineering :: Physics',
      ]
)
