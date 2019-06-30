
"""Module that defines pyFAI calibrans."""

import os

import pyFAI.calibrant

# Calibrants can be added here:
#1)
# The Lithium Titanat (LiTiO2) crystal is a Face centered cubic (FCC) with
# a = b = c = 4.14 A and alpha = beta = gamma = 90 deg
# see http://www.crystallography.net/cod/1541630.html
_LiTiO2 = pyFAI.calibrant.Cell.cubic(4.14, lattice_type='F')

# Add the pyFAI standard calibrants
_cells = {'LiTiO2': _LiTiO2}
parent = os.path.dirname(__file__)
celldir = os.path.join(parent, 'cells')
calibrants = list(pyFAI.calibrant.CALIBRANT_FACTORY.keys())
for name, cell in _cells.items():
    if not os.path.isfile(os.path.join(celldir, name+'.D')):
        cell.save(os.path.join(celldir, name))
calibrants += list(_cells.keys())

