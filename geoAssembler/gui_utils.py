
"""Provide helper methods for the gui."""

import os

from .defaults import params

def read_geometry(detector, filename, quad_pos):
    """Create the correct geometry class for a given detector.

    Parameters:
        detector (str): Name of the considered detector 
        filename (str): Path to the geometry file
        quad_pos (list): X,Y coordinates of quadrants

    Retruns:
        GeometryAssembler Object
    """
    if detector == 'AGIPD':
        from .geometry import AGIPDGeometry
        if os.path.isfile(filename):
            return AGIPDGeometry.from_crystfel_geom(filename)
        else:
            quad_pos = quad_pos or params.FALLBACK_QUAD_POS['AGIPD']
            return AGIPDGeometry.from_quad_positions(quad_pos)
    elif detector == 'LPD':
        from .geometry import LPDGeometry
        quad_pos = quad_pos or params.FALLBACK_QUAD_POS['AGIPD']
        return LPDGeometry.from_h5_file_and_quad_positions(filename, quad_pos)
    else:
        raise NotImplementedError('Detector Class not available')

def write_geometry(geom, filename, header=''):
    """Write the correct geometry description.

    Parameters:
        geom (GeometryAssembler): object holding the geometry information
        filename (str): Output filename
    """
    from .geometry import AGIPDGeometry, LPDGeometry
    if isinstance(type(geom), AGIPDGeometry):
        geom.write_crystfel_geom(filename, header=header)
    elif isinstance(type(geom), LPDGeometry):
        geom.write_quad_pos(filename)
    else:
        raise NotImplementedError('Detector Class not available')
