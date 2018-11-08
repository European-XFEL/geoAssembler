#!/usr/bin/env python3

import gc
import glob
import logging
import os
import warnings

from argparse import ArgumentParser
from h5py import File
import numpy as np
from pyqtgraph import QtCore

from geoAssembler.PanelView import Calibrate
from geoAssembler.geometry import AGIPD_1MGeometry

def read_data(run_dir, events, func=lambda x: x, pattern='*.h5', **kwargs):
    '''
        Method that reads AGIPD image data from a given run directory

    Parameters:
        run_dir (str) : The directory that contains the data in hdf5 format
        events : The indices of the data, that is to be read

    Keywords:
        func : a function that apply to the data, default is no function is applied
               this could be a sum along the first axis
        pattern : a glob pattern to select certain files (dfault *.h5)

    Return 3D array of shape (16, 128, 512)
    '''
    files = glob.glob(os.path.join(run_dir, pattern))
    files.sort()
    h5=[File(fn, 'r') for fn in files]
    data=np.empty([16, 512, 128])
    kwargs={}

    for n,k in enumerate(data.keys()):
        data[n] = func(h5[n]['/INSTRUMENT/SPB_DET_AGIPD1M-1/DET/{}CH0:xtdf/image'.format(n)]['data'][events], **kwargs)
    return data

def get_testdata():
    '''Method to get some test-data'''
    array = np.load(os.path.join(os.path.dirname(__file__), 'image.npz'))
    ## Create some mock test data as it would be comming from karabo-data
    data=array['data']
    print(data.shape)
    return array['data']


def main(argv=None):

    ap = ArgumentParser(description='''
    Create an initial geometry based on pre-defined structures.

    The program will open a GUI where points that will be fitted to a defined
    structure are chosen.''')

    ap.add_argument('-i', '--input',
                    help='Directory containing the run')
    ap.add_argument('-t', '--train',
                    help='TrainId that contains the data, if none is given the first train will be taken')
    ap.add_argument('-o', '--output',
                    help='Write data to tiff format with given filename')
    ap.add_argument('--test', help='Only a test with is performed',
                    dest='test', action='store_false')
    ap.add_argument('-vmin', help=('Minimum value to be displayed in the Gui\n'
                                    '(default: -1000)'), dest='vmin')
    ap.add_argument('-vmax', help=('Maximum value to be displayed in the Gui\n'
                                    '(default: 5000)'), dest='vmax')
    ap.add_argument('-g', '--geometry', dest='geof',
                    help='Name of the geometry file to be written')


    ap.set_defaults(vmin=-1000)
    ap.set_defaults(vmax=5000)
    ap.set_defaults(test=False)
    ap.set_defaults(input=None)
    ap.set_defaults(train=None)
    ap.set_defaults(geof='test.geom')
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(os.path.basename(__file__))
    args = ap.parse_args(argv)

    header ='''data = /entry_1/data_1/data
;mask = /entry_1/data_1/mask

mask_good = 0x0
mask_bad = 0xffff

adu_per_eV = 0.0075  ; no idea
clen = 0.119  ; Camera length, aka detector distance
photon_energy = 10235'''



    if args.input is None and args.test is False:
        log.warning(
            'No input was given and test is set to false, turning test on')
        args.test = True
    if args.input is not None:
        # Taking trains with karabo-data
        import karabo_data as kd
        if os.path.isdir(args.input):
            Run_Dir = kd.RunDirectory(args.input)
            if args.train is not None:
                log.info('Getting train ID # %i:' % int(args.train))
                trainID, data = Run_Dir.select('*/DET/*', 'image.data').train_from_index(int(args.train))
            else:
                log.info('Getting first Train')
                trainID, data = Run_Dir.train_from_index(0)
        else:
            log.error('Error: Directory %s does not exist' % args.input)
            raise RuntimeError('No such file or directory')
    else:
        # Get some mock data for testing
        data = get_testdata()

    vmin, vmax = int(args.vmin), int(args.vmax)
    cal = Calibrate(data, None, vmin=vmin, vmax=vmax)


if __name__ == '__main__':
    main()
