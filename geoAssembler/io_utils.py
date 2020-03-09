"""Provide helper methods for the gui."""

import os

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


def write_geometry(geom, filename, logger):
    """Write the correct geometry description.

    Parameters:
        geom (GeometryAssembler): object holding the geometry information
        filename (str): Output filename
        logger (logging.Logger): Logging object to display information
    """
    from .geometry import AGIPDGeometry, DSSCGeometry, LPDGeometry
    if isinstance(geom, AGIPDGeometry):
        geom.write_crystfel_geom(filename)
    elif isinstance(geom, (LPDGeometry, DSSCGeometry)):
        geom.write_quad_pos(filename)
        logger.info('Quadpos {}'.format(geom.quad_pos))
    else:
        raise NotImplementedError('Detector Class not available')

