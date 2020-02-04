#!/usr/bin/env python3
"""Setup script for intalling the geoAssembler."""
import glob
import os.path as osp
import re
from setuptools import setup, find_packages
import sys


def get_script_path():
    """Return the directory path of this file."""
    return osp.dirname(osp.realpath(sys.argv[0]))


def read(*parts):
    """Read the content of a file."""
    return open(osp.join(get_script_path(), *parts)).read()


def find_version(*parts):
    """Get the version number of the lib."""
    vers_file = read(*parts)
    match = re.search(r'^__version__ = "(\d+\.\d+\.\d+)"', vers_file, re.M)
    if match is not None:
        return match.group(1)
    raise RuntimeError("Unable to find version string.")


def find_files(directory):
    return glob.glob(osp.join(directory, '*'))

setup(name="geoAssembler",
      version=find_version("geoAssembler", "__init__.py"),
      author="European XFEL GmbH",
      author_email="cas-support@xfel.eu",
      maintainer="Martin Bergemann",
      url="https://git.xfel.eu/gitlab/dataAnalysis/geoAssembler",
      description="Tool to Calibrate Detector Geometry Based on Power Diffraction Pattern",
      long_description=read("README.md"),
      license="BSD-3-Clause",
      packages=find_packages(),
      data_files=[('templates', find_files('templates')),
                  ('cells', find_files('cells'))],
      package_data={'': ['cells/*.D', 'templates/*.tmpl', 'icons/*.png'],
                    'geoAssembler.tests': ['data_*.npz', 'test.geom'],
                    'geoAssembler.widgets.editor': ['*.ui'],
                    },
      entry_points={
          'gui_scripts': [
              'geoAssembler = geoAssembler.main:main'
          ]},
      install_requires=[
          'cfelpyutils',
          'karabo-data',
          'matplotlib',
          'numpy',
          'pyqtgraph',
          'ipywidgets',
          'pyFai',
          'PyQt5 >= 5.13.2, <= 6.0.0',
          'PyQt5-sip >= 12.7.0, <= 13.0.0',
          'scipy'
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
          'Topic :: Scientific/Engineering :: Information Analysis',
          'Topic :: Scientific/Engineering :: Physics',
      ]
      )
