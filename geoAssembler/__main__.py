#!/usr/bin/env python3
"""Script that run geoAssembler GUI."""
from argparse import ArgumentParser

from pyqtgraph import QtGui

from .qt_viewer import CalibrateQt


# Define a header that should be added to the geometry file, this is useful
# to use the geometry file with tools like hdfsee
HEADER = """data = /entry_1/data_1/data
;mask = /entry_1/data_1/mask

mask_good = 0x0
mask_bad = 0xffff

adu_per_eV = 0.0075  ; no idea
clen = {clen}  ; Camera length, aka detector distance
photon_energy = {energy} ;"""


def CreateCalibrateGui(*args, **kwargs):
    """Create a QtGui Application and return an instance of CalibrateQt"""

    app = QtGui.QApplication([])
    calib = CalibrateQt(*args, **kwargs)
    calib.window.show()
    app.exec_()
    app.closeAllWindows()
    return calib


def main(argv=None):
    """Define the help string."""
    ap = ArgumentParser(description="""
    This prgram allows for a ring based geometry calibration.

    The program will open a GUI to assemble data according to a geometry that
    can either be loaded or that can be based on fixed quadrant positions.

    To select quadrants click on the quadrant and to move the selected quadrant
    use CTRL+arrow-keys.""")

    ap.add_argument('-r','--run', default=None,
                    help='Select a run')
    ap.add_argument('-g','--geometry', default=None,
                    help='Select a cfel geometry file')
    ap.add_argument('-c','--clen', default=0.119,
                    help='Detector distance [m]')
    ap.add_argument('-e','--energy', default=10235,
                    help='Photon energy [ev]')
    ap.add_argument('-l','--level', nargs='+', default=[], type=int,
                    help='Pre defined display range for plotting')

    args = ap.parse_args()
    if len(args.level) == 0:
        levels = None
    elif len(args.level) == 2:
        levels = args.level
    else:
        raise IndexError('Levels should be one min and one max value')

    CreateCalibrateGui(args.run, args.geometry, levels=levels,
            header=HEADER.format(clen=args.clen, energy=args.energy))

if __name__ == '__main__':
    main()

