
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

def write_geometry(geom, filename, header=''):
    """Write the correct geometry description.

    Parameters:
        geom (GeometryAssembler): object holding the geometry information
        filename (str): Output filename
    """
    from .geometry import AGIPDGeometry, LPDGeometry
    if isinstance(geom, AGIPDGeometry):
        geom.write_crystfel_geom(filename, header=header)
    elif isinstance(geom, LPDGeometry):
        geom.write_quad_pos(filename)
    else:
        raise NotImplementedError('Detector Class not available')

def get_icon(file_name, size=16):
    """Load icon from file."""
    parent_dir = os.path.dirname(__file__)
    icon_path = os.path.join(parent_dir, 'icons')
    icon = QtGui.QIcon(os.path.join(icon_path, file_name))
    qsize = QtCore.QSize(size, size)
    return icon, qsize

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
                   'rois': ('rois.png', 16),
                   'rundir': ('open.png', 16),
                   'save': ('save.png', 16),
                   'square': ('square.png', 16)
                   }

    button = QtGui.QPushButton(label)
    icon, qsize = get_icon(*icon_types[icon_type])
    button.setIcon(icon)
    button.setIconSize(qsize)
    return button
