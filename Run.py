#!/usr/bin/env python3

from Assembler import *
from Gui import *
from pyqtgraph import QtCore
import  gc
from argparse import ArgumentParser
import logging
import os
from Gui import ResultView
import warnings
def main(argv=None):
    
    ap = ArgumentParser(description='''
    Create an initial geometry based on pre-defined structures.

    The program will open a GUI where points that will be fitted to a defined
    structure are chosen.''')

    ap.add_argument('-i', '--input', dest='input', action='store_false',
                    help='Directory containing the run')
    ap.add_argument('-t','--train', dest='train', action='store_false',
            help='TrainId that contains the data, if none is given the first train will be taken')
    ap.add_argument('--test', help='Only a test with is performed', dest='test', action='store_false')
    ap.add_argument('--vmin', help=('Minimum value to be displayed in the Gui\n'
                                    '(default: -1000)'), dest='vmin')
    ap.add_argument('--vmax', help=('Maximum value to be displayed in the Gui\n'
                                    '(default: 5000)'), dest='vmin')
    ap.set_defaults(vmin=-1000)
    ap.set_defaults(vmax=5000)
    ap.set_defaults(test=False)
    ap.set_defaults(input=None)
    ap.set_defaults(train=None)
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(os.path.basename(__file__))
    args = ap.parse_args(argv)

    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    if args.input is None and args.test is False:
        log.warning('No input was given and test is set to false, turning test on')
        args.test = True
    if args.input is not None:
        ## Taking trains with karabo-data
        import karabo_data as kd
        if os.path.isdir(args.input):
            Run_Dir = kd.RunDirectory(args.input)
            if args.train is not None:
                log.info('Getting train ID #%i:'%int(args.train))
                trainID, data = Run_Dir.train_from_id(int(args.train))
            else:
                log.info('Getting first Train')
                trainID, data = Run_Dir.train_from_index(0)
        else:
            log.error('Error: Directory %s does not exist'%args.input)
            raise RuntimeError('No such file or directory')
    else:
        ## Get some mock data for testing
        data = get_testdata()

    log.info('Starting to assemble')
    A = Assemble()
    points = []
    while True:
        shift = A.get_geometry(data, pre_points=points)
        View = ResultView(A.apply_geo(data), A, shift=shift, vmin=args.vmin,
                          vmax=args.vmax)
        appl = View.apply
        p = View.positions
        del View
        gc.collect()
        QtCore.QCoreApplication.quit()
        if appl:
            break
        else:
            points=p
            QtCore.QCoreApplication.quit()
        log.info('Re-assembling...')



if __name__ == '__main__':
    import sys
    vmin, vmax = -1000, 5000
    main()
    sys.exit()
    
