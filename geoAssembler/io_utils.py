"""Provide helper methods for the gui."""

from .defaults import DefaultGeometryConfig as Defaults
from .geometry import AGIPDGeometry, DSSCGeometry, LPDGeometry


def read_geometry(detector, filename, quad_pos=None):
    """Create the correct geometry class for a given detector.

    Parameters:
        detector (str): Name of the considered detector
        filename (str): Path to the geometry file
        quad_pos (list): X,Y coordinates of quadrants (default None)

    Retruns:
        GeometryAssembler Object
    """
    if quad_pos is None:
        quad_pos = Defaults.fallback_quad_pos.get(detector)

    if detector == 'AGIPD':
        if filename:
            return AGIPDGeometry.from_crystfel_geom(filename)
        else:
            return AGIPDGeometry.from_quad_positions(quad_pos)
    elif detector == 'DSSC':
        if not filename:
            raise ValueError(
                "Constructing DSSC geometry without file not yet supported"
            )
        return DSSCGeometry.from_h5_file_and_quad_positions(filename, quad_pos)
    elif detector == 'LPD':
        if not filename:
            raise ValueError(
                "Constructing LPD geometry without file not yet supported"
            )
        return LPDGeometry.from_h5_file_and_quad_positions(filename, quad_pos)
    else:
        raise ValueError("Unknown detector type: %r" % detector)


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
    elif isinstance(geom, (DSSCGeometry, LPDGeometry)):
        geom.write_quad_pos(filename)
        logger.info('Quadpos {}'.format(geom.quad_pos))
    else:
        raise NotImplementedError('Detector Class not available')

