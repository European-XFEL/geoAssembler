#!/usr/bin/env python3
"""Script that run geoAssembler GUI."""

from argparse import ArgumentParser
import logging
import os

from pyqtgraph import QtGui
from . import CalibrateQt

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(os.path.basename(__file__))

# Define a header that should be added to the geometry file, this is useful
# to use the geometry file with tools like hdfsee
HEADER = """data = /entry_1/data_1/data
;mask = /entry_1/data_1/mask

mask_good = 0x0
mask_bad = 0xffff

adu_per_eV = 0.0075  ; no idea
clen = {clen}  ; Camera length, aka detector distance
photon_energy = {energy} ;"""

NB_MESSAGE = """Notebook has been created. You can use it by loading the file
{nb_path} either by using JupyterHub on desy:
 https://max-jhub.desy.de
or by starting a jupyter server:
 jupyter-notebook --port PORT_NUMBER* --no-browser &
and follow the displayed instructions. For more information see:

https://in.xfel.eu/readthedocs/docs/data-analysis-user-documentation/en/latest/computing.html#can-i-execute-a-jupyter-notebook-on-the-maxwell-cluster-and-connect-it-to-the-webbrowser-of-my-desktop-laptop


Note 1: the PORT_NUMBER should be a number of >= 1024 like 8432
"""

NB_DIR = os.path.join(os.environ['HOME'], 'notebooks')
NB_FILE = 'GeoAssembler.ipynb'
CLEN = 0.119 #Default sample distance
ENERGY = 10235 #Default beam energy
# Default run directory
RUNDIR = '/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0005'

def copy_notebook(defaults):
    """Create a new notebook and copy it into the user-space."""
    parent = os.path.dirname(__file__)
    tmpl = os.path.join(parent, 'templates', 'geoAssembler.tmpl')
    try:
        os.makedirs(defaults['folder'])
    except FileExistsError:
        pass
    with open(tmpl) as f:
        jb_tmpl = f.read()

    for key in ('rundir', 'geofile', 'levels', 'clen', 'energy'):
        jb_tmpl = jb_tmpl.replace('{%s}' % key, str(defaults[key]))

    with open(os.path.join(defaults['folder'], defaults['name']), 'w') as f:
        f.write(jb_tmpl)

    print(NB_MESSAGE.format(nb_path=os.path.join(defaults['folder'],
                                                 defaults['name'])))


def create_nb(rundir=None, geofile=None, clen=None, energy=None, levels=None,
              nb_dir=None, nb_file=None):
    """Creat a notebook and copy it into the user space."""
    # Get the default varaibles for the notebook, if user has already given them
    # take them if not ask for them and provide default options
    nb_defaults = {}
    nb_defaults['rundir'] = repr(rundir or RUNDIR)
    if geofile is not None:
        nb_defaults['geofile'] = repr(geofile)
    else:
        nb_defaults['geofile'] = None
    if levels is None:
        levels = [None, None]
    else:
        levels = levels
    nb_defaults['levels'] = levels
    nb_defaults['energy'] = energy
    nb_defaults['folder'] = nb_dir or NB_DIR
    name = nb_file or NB_FILE
    if not name.endswith('.ipynb'):
        name += '.ipynb'
    nb_defaults['name'] = os.path.basename(name)
    nb_defaults['clen'] = clen or CLEN
    copy_notebook(nb_defaults)


def create_calibrate_gui(*args, **kwargs):
    """Create a QtGui Application and return an instance of CalibrateQt."""
    app = QtGui.QApplication([])
    calib = CalibrateQt(*args, **kwargs)
    calib.window.show()
    app.exec_()
    app.closeAllWindows()
    return calib


def main(argv=None):
    """Define the help string."""
    ap = ArgumentParser(description="""
    This program allows for a ring based geometry calibration.

    The program will open a GUI to assemble data according to a geometry that
    can either be loaded or that can be based on fixed quadrant positions.

    To select quadrants click on the quadrant and to move the selected quadrant
    use CTRL+arrow-keys.""")
    ap.add_argument('-nb', '--notebook', default=False, action='store_true',
                    help='Create a notebook from a template that is saved in '
                         'your userspace')
    ap.add_argument('-nb_dir',
                    default=NB_DIR,
                    help='Set default directory to save notebooks')
    ap.add_argument('-nb_file', default=NB_FILE,
                    help='Set file name of the notbook (default {})'.format(NB_FILE))
    ap.add_argument('-r', '--rundir', default=None,
                    help='Select a run (default {})'.format(RUNDIR))
    ap.add_argument('-g', '--geometry', default=None,
                    help='Select a cfel geometry file (default None)')
    ap.add_argument('-c', '--clen', default=CLEN,
                    help='Detector distance [m] (default {})'.format(CLEN))
    ap.add_argument('-e', '--energy', default=ENERGY,
                    help='Photon energy [ev] (default {})'.format(ENERGY))
    ap.add_argument('-l', '--level', nargs=2, default=[None, None],
                    help='Pre defined display range for plotting')
    ap.add_argument('-t', '--test', default=False, action='store_true',
                    help='Test mode')

    args = ap.parse_args()

    if args.notebook:
        create_nb(args.rundir, args.geometry, args.clen, args.energy, args.level,
                  args.nb_dir, args.nb_file)
    else:
        if args.test:
            from tempfile import TemporaryDirectory
            from .tests.utils import create_test_directory
            with TemporaryDirectory() as td:
                log.info('Creating temp data in {}...'.format(td))
                create_test_directory(td)
                log.info('...done')
                create_calibrate_gui(td,
                                     args.geometry,
                                     levels=args.level,
                                     header=HEADER.format(clen=args.clen,
                                                          energy=args.energy))
        else:
            create_calibrate_gui(args.rundir,
                                 args.geometry, levels=args.level,
                                 header=HEADER.format(clen=args.clen,
                                                      energy=args.energy))

if __name__ == '__main__':
    main()
