#!/usr/bin/env python3
"""Script that run geoAssembler GUI."""

from argparse import ArgumentParser
import logging
from pathlib import Path

from .nb import create_nb, NB_FILE, NB_DIR

logging.getLogger(__name__).addHandler(logging.NullHandler())
log = logging.getLogger(__name__)

# Default run directory
RUNDIR = '/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0005'


def main(argv=None):
    """Define the help string."""
    ap = ArgumentParser(description="""
    This program allows for a ring based geometry calibration.

    The program will open a GUI to assemble data according to a geometry that
    can either be loaded or that can be based on fixed quadrant positions.

    To select quadrants click on the quadrant and to move the selected quadrant
    use CTRL+arrow-keys.""")
    ap.add_argument('--notebook', default=False, action='store_true',
                    help='Create a notebook from a template that is saved in '
                         'your userspace')
    ap.add_argument('--nb_dir',
                    default=NB_DIR,
                    help='Set default directory to save notebooks')
    ap.add_argument('--nb_file', default=NB_FILE,
                    help='Set file name of the notbook (default {})'.format(NB_FILE))
    ap.add_argument('--rundir', default=None,
                    help='Select a run (default {})'.format(RUNDIR))
    ap.add_argument('--geometry', default=None,
                    help='Select a cfel geometry file (default None)')
    ap.add_argument('--level', nargs=2, default=[0, 10000], type=float,
                    help='Pre defined display range for plotting')
    ap.add_argument('--test', default=False, action='store_true',
                    help='Test mode')
    ap.add_argument('--det', default='AGIPD', choices=('AGIPD', 'LPD'),
                    help='If test mode is activated, the name of the detector')

    args = ap.parse_args(argv)

    if args.notebook:
        create_nb(
            rundir=args.rundir,
            geofile=args.geometry,
            levels=args.level,
            dest_path=Path(args.nb_dir, args.nb_file),
        )
    else:
        from .qt import run_gui
        if args.test:
            from tempfile import TemporaryDirectory
            from geoAssembler.tests.utils import create_test_directory
            with TemporaryDirectory() as td:
                log.info('Creating temp data in {}...'.format(td))
                create_test_directory(td, det=args.det)
                log.info('...done')
                run_gui(td, args.geometry, levels=args.level)
        else:
            run_gui(args.rundir, args.geometry, levels=args.level)


if __name__ == '__main__':
    main()
