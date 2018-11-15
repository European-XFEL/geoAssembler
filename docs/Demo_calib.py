#!/usr/bin/env python3

import os
import sys

from argparse import ArgumentParser
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__),'../'))
from geoAssembler import Calibrate


def get_testdata():
    '''Method to get some test-data'''
    array = np.load(os.path.join(os.path.dirname(__file__),
                                 '../geoAssembler/tests/data.npz'))
    ## Create some mock test data as it would be comming from karabo-data
    data=array['data']
    print(data.shape)
    return array['data']

def help(argv=None):
    ap = ArgumentParser(description='''
    This prgram demonstrates how to call the ring based geometry calibration.

    The program will open a GUI assemble data according to a pre-defined
    geometry.

    To select quadrants click on the quadrant and to move the selected quadrant
    use CTRL+arrow-keys.''')
    ap.parse_args(argv)

if __name__ == '__main__':

    # First lets load the data, this can either be done by karabo-data's
    # RunDirectory, a virtual dataset or by reading the data from hdf files.
    # The only constraint is that the data should be of shape (16x512x128)
    # which means only one image

    #Get some mock data for testing
    #
    data = get_testdata()

    # Define a header that should be added to the geometry file, this is useful
    # to use the geometry file with tools like hdfsee
    header ='''data = /entry_1/data_1/data
;mask = /entry_1/data_1/mask

mask_good = 0x0
mask_bad = 0xffff

adu_per_eV = 0.0075  ; no idea
clen = 0.119  ; Camera length, aka detector distance
photon_energy = 10235'''

    # Read a starting geometry, if no geometry is present the starting
    # starting geometry can be set to None

    start_geom = 'testing.geom'
    C = Calibrate(data, start_geom, vmin=-1000, vmax=5000, header=header)

    # The centre coordinates might be of interest (i.e azimuthal integration)
    print('Geometry-centre is P(y: {}/x: {})'.format(*C.centre))
