#!/usr/bin/env python3
"""Script that run geoAssembler GUI."""

from argparse import ArgumentParser
import logging
import os
import re
import readline

from ipykernel import kernelspec
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

RE_SPACE = re.compile('.*\s+$', re.M)

NB_MESSAGE = """

Notebook has been created. You can use it by loading the file
{nb_path} either by using JupyterHub on desy:
 https://max-jhub.desy.de
or by starting a jupyter server:
 jupyter-notebook --port PORT_NUBER* --no-browser &
and follow the displayed instructions. For more information see https://bit.ly/2Gm97c0


Note 1: the PORT_NUMBER should be a number of >= 1024 like 8432
"""


class Completer:
    """Provide tab completion directories and files for call of input."""

    def _listdir(self, root):
        """List directory 'root' appending the path separator to subdirs."""
        res = []
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            res.append(name)
        return res

    def complete(self, text: str, state: int):
        """Define the complet method for readline."""
        try:
            path = self.complete_path(text)
        except Exception:
            return None
        if state >= len(path):
            return None
        return path[state]

    def complete_path(self, path):
        """Perform completion of filesystem path."""
        if not path:
            return self._listdir('.')
        dirname, rest = os.path.split(os.path.expanduser(path))
        tmp = dirname if dirname else '.'
        res = [os.path.join(dirname, p)
               for p in self._listdir(tmp) if p.startswith(rest)]
        # more than one match, or single match which does not exist (typo)
        if len(res) > 1 or os.path.exists(res[0]):
            return res
        # resolved to a single directory, so return list of files below it
        if os.path.isdir(path):
            return [self._listdir(path)]
        # exact file match terminates this completion
        return os.path.abspath(path)


def check_tmpl(var, default=None, tab_complete=False):
    """Get entries for template."""
    if tab_complete:
        comp = Completer()
        readline.set_completer(comp.complete)
        readline.set_completer_delims('')
        readline.parse_and_bind("tab: complete")
    if default is None:
        inpt = input('Enter {}:'.format(var))
    else:
        inpt = input('Enter {} [default {}]: '.format(var, default))
    readline.set_completer(None)
    if not inpt:
        return default
    else:
        return inpt


def create_nbkernel():
    """Create a new karabo_data jupyter kernel if non exists."""
    log.warn("A new kernel called 'xfel' will be created in your home directory")
    inpt = input('Do you whish to continue [YES|no]:')
    if 'no' in inpt.lower():
        log.info('Aborting')
        return
    log.info('Creating xfel notebook kernel in userspace')
    kernelspec.install(kernel_name='xfel', user=True)
    log.info(
        'The kernel can be loaded from the jupyter notbook menu: kernels -> change kernel -> xfel')


def copy_notebook(defaults):
    """Create a new notebook and copy it into the user-space."""
    parent = os.path.dirname(os.path.dirname(__file__))
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
              nb_dir=None, nb_file=None, no_kernel=False):
    """Creat a notebook and copy it into the user space."""
    # Get the default varaibles for the notebook, if user has already given them
    # take them if not ask for them and provide default options
    nb_defaults = {}
    nb_defaults['rundir'] = repr(rundir or check_tmpl(
        'Run Directory',
        default='/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0005',
        tab_complete=True))
    geofile = geofile or check_tmpl('Input Geometry File in CFEL format',
                                    default=None,
                                    tab_complete=True)
    if geofile is not None:
        nb_defaults['geofile'] = repr(geofile)
    else:
        nb_defaults['geofile'] = None
    levels = levels or check_tmpl(
        'Min/Max Display Limits', default=None)
    if isinstance(levels, str):
        for repl in ('/', ',', '|', ';', ':'):
            levels = levels.replace(repl, ' ')
        levels = [float(lev) for lev in levels.strip().split()]
    elif levels is None:
        levels = [None, None]
    else:
        levels = levels
    nb_defaults['levels'] = levels
    nb_defaults['clen'] = clen or check_tmpl('Detector Distance [m]',
                                             default=str(clen))
    nb_defaults['energy'] = energy or check_tmpl('Beam Wavelength [eV]',
                                                 default=str(energy))
    nb_defaults['folder'] = nb_dir or check_tmpl('Directory where your notebooks should be located',
                                                 tab_complete=True,
                                                 default=os.path.join(os.environ['HOME'],
                                                                      'notebooks'))
    name = nb_file or check_tmpl('Name of the geoAssembler notebook',
                                 tab_complete=True,
                                 default='GeoAssembler.ipynb')
    if not name.endswith('.ipynb'):
        name += '.ipynb'
    nb_defaults['name'] = os.path.basename(name)
    if not no_kernel:
        create_nbkernel()
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
    ap.add_argument('-no_kernel', default=False, action='store_true',
                    help='Do not try to attempt creating a xfel notebook kernel')
    ap.add_argument('-nb_folder', default=None,
                    help='Set default directory to save notebooks')
    ap.add_argument('-nb_file', default=None,
                    help='Set file name of the notbook')
    ap.add_argument('-r', '--run', default=None,
                    help='Select a run')
    ap.add_argument('-g', '--geometry', default=None,
                    help='Select a cfel geometry file')
    ap.add_argument('-c', '--clen', default=0.119,
                    help='Detector distance [m]')
    ap.add_argument('-e', '--energy', default=10235,
                    help='Photon energy [ev]')
    ap.add_argument('-l', '--level', nargs=2, default=None,
                    help='Pre defined display range for plotting')

    args = ap.parse_args()

    if args.notebook:
        create_nb(args.run, args.geometry, args.clen, args.energy, args.level,
                  args.nb_folder, args.nb_file, args.no_kernel)
    else:
        create_calibrate_gui(args.run, args.geometry, levels=args.level,
                             header=HEADER.format(clen=args.clen, energy=args.energy))


if __name__ == '__main__':
    main()
