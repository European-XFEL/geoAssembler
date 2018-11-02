#!/usr/bin/env python3

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=ImportWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
import numpy as np
import pandas as pd
from Assembler import Assemble, get_testdata
from Gui import ResultView, PanelView
from pyqtgraph import QtCore
import gc
from argparse import ArgumentParser
import logging
import os
from geometry import AGIPD_1MGeometry
warnings.resetwarnings()


def crate_testData(run_dir, pattern='*.h5'):
   from h5py import File
   import os, glob
   from Assemble import Test
   files = glob.glob(os.path.join(run_dir, pattern))
   files.sort()
   h5=[File(fn, 'r') for fn in files]
   data=Test()
   kwargs={}

   for n,k in enumerate(data.keys()):
      data[k]['image.data'] = h5[n]['/INSTRUMENT/SPB_DET_AGIPD1M-1/DET/{}CH0:xtdf/image'.format(n)]['data'][12345]
      kwargs['image.%02i'%n] =  data[k]['image.data']

   return data

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

    log.info('Starting to assemble')
    #A = Assemble()
    quad_pos = [ (-540, 610), (-540, -15), (540, -143), (540, 482)]
    geom =  AGIPD_1MGeometry.from_quad_positions(quad_pos=quad_pos)
    points = []
    vmin, vmax = int(args.vmin), int(args.vmax)
    #while True:
    View = PanelView(data, geom, vmin=vmin,
                      vmax=vmax)
    appl = View.apply
    print(appl)
    p = View.positions
    xx = []
    yy = []
    for pp in p:
        xx.append(pp.pos().x())
        yy.append(pp.pos().y())
    pp = pd.DataFrame(dict(X=xx, Y=yy))
    del View
    gc.collect()
    QtCore.QCoreApplication.quit()
    '''
    if appl:
        break
    else:
        points = p
        QtCore.QCoreApplication.quit()
    '''
    log.info('Re-assembling...')
    if args.output is not None:
        output = args.output.replace('.tiff', '').replace('.tif', '')

        from PIL import Image
        data = np.ma.masked_invalid(A.apply_geo(data))

        im = Image.fromarray(np.ma.masked_outside(data, -10, 50).filled(-10))
        im.save(output+'.tif')
    pp.to_csv('points.csv')
    geo.to_csv('geo.csv')

    ## Create the Geometry file
    geof=args.geof.replace('.geom','')
    geom = AGIPD_1MGeometry.from_quad_positions(quad_pos=A.pos, panel_gap=29, asic_gap=0)

    geom.write_crystfel_geom(geof+'.geom', header=header)


if __name__ == '__main__':
    import sys
    vmin, vmax = -1000, 5000
    main()
    sys.exit()
