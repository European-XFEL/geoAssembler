
"""Provide helper methods for the gui."""

from collections import namedtuple
import os


from pyqtgraph.Qt import (QtCore, QtGui)
from .defaults import DefaultGeometryConfig as Defaults


def read_geometry(detector, filename, quad_pos=None):
    """Create the correct geometry class for a given detector.

    Parameters:
        detector (str): Name of the considered detector
        filename (str): Path to the geometry file
    Keywords:
        quad_pos (list): X,Y coordinates of quadrants (default None)

    Retruns:
        GeometryAssembler Object
    """
    filename = filename or ''
    try:
        quad_pos = quad_pos or Defaults.fallback_quad_pos[detector]
    except KeyError:
        raise NotImplementedError('Detector Class not available')

    if detector == 'AGIPD':
        from .geometry import AGIPDGeometry
        if os.path.isfile(filename):
            return AGIPDGeometry.from_crystfel_geom(filename)
        else:
            return AGIPDGeometry.from_quad_positions(quad_pos)
    elif detector == 'LPD':
        from .geometry import LPDGeometry
        return LPDGeometry.from_h5_file_and_quad_positions(filename, quad_pos)
    elif detector == 'DSSC':
        from .geometry import DSSCGeometry
        return DSSCGeometry.from_h5_file_and_quad_positions(filename, quad_pos)


def write_geometry(geom, filename, header, logger):
    """Write the correct geometry description.

    Parameters:
        geom (GeometryAssembler): object holding the geometry information
        filename (str): Output filename
        header (str): Additional infromation for a geometry header
        logger (str): Logging object to display information
    """
    from .geometry import AGIPDGeometry, DSSCGeometry, LPDGeometry
    if isinstance(geom, AGIPDGeometry):
        geom.write_crystfel_geom(filename, header=header)
    elif isinstance(geom, LPDGeometry) or isinstance(geom, DSSCGeometry):
        geom.write_quad_pos(filename)
        logger.info(f'Quadpos {geom.quad_pos}')
    else:
        raise NotImplementedError('Detector Class not available')


def get_icon(file_name):
    """Load icon from file."""
    parent_dir = os.path.dirname(__file__)
    icon_path = os.path.join(parent_dir, 'icons')
    icon = QtGui.QIcon(os.path.join(icon_path, file_name))
    return icon


def create_button(label, icon_type):
    """Create a button and set an icon to it."""
    icon_types = {
                   'circle': ('circle.png', 16),
                   'cancel': ('gtk-cancel.png', 16),
                   'clear': ('clear-all.png', 16),
                   'detector': ('main_icon_64x64.png', 16),
                   'draw': ('system-run.png', 16),
                   'load': ('file.png', 16),
                   'log': ('log.png', 16),
                   'main': ('main_icon_64x64.png', 64),
                   'ok': ('gtk-ok.png', 16),
                   'quit': ('exit.png', 16),
                   'quads': ('quads.png', 16),
                   'shapes': ('shapes.png', 16),
                   'rundir': ('open.png', 16),
                   'save': ('save.png', 16),
                   'square': ('square.png', 16)
                   }

    icon_name, size = icon_types[icon_type]

    button = QtGui.QPushButton(label)
    button.setIcon(get_icon(icon_name))
    button.setIconSize(QtCore.QSize(size, size))

    return button
