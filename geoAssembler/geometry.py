"""Provide AGIPD-D geometry information that supports quadrant moving."""

import logging
import tempfile

from extra_geom import (
    AGIPD_1MGeometry, DSSC_1MGeometry, LPD_1MGeometry,
)
from extra_geom.detectors import GeometryFragment
import numpy as np
import pandas as pd

from .defaults import DefaultGeometryConfig as Defaults

log = logging.getLogger(__name__)

def _move_mod(module, inc):
    """Move module into an given direction.

    Parameters:
        module (list): List containing Geometry Fragments
        inc (nd array) : 3d vector containing the move direction
    """
    return [GeometryFragment(
              tile.corner_pos+inc,
              tile.ss_vec,
              tile.fs_vec,
              tile.ss_pixels,
              tile.fs_pixels,
            ) for tile in module]


class GeometryAssembler:
    """Base class for geometry methods not part of extra_geom.

    This base class provides methods for getting quad corners, moving them
    and positioning all modules.
    """

    filename = None
    unit = None
    frag_ss_pixels = None
    frag_fs_pixels = None
    pixel_size = None
    detector_name = 'generic'

    def __init__(self, exgeom_obj):
        """The class is instanciated using an extra_geom geometry object."""
        self.exgeom_obj = self.exgeom_obj_orig = exgeom_obj
        # Store quadrant shifts as integer numbers of pixels, and convert to
        # metres when we apply them, to avoid accumulating floating point error.
        self.quad_offsets = np.zeros((4, 2), dtype=np.int32)

    @property
    def modules(self):
        """The karabo data geometry modules."""
        return self.exgeom_obj.modules

    @property
    def snapped_geom(self):
        """Create a snapped geometry."""
        return self.exgeom_obj._snapped()

    def inspect(self):
        """Plot a representation of the current geometry."""
        return self.exgeom_obj.inspect()

    def move_quad(self, quad, inc):
        """Move the whole quad in a given direction.

        Parameters:
            quad (int): Quandrant number that is to be moved (1 - 4)
            inc (collection): increment of the direction to be moved
        """
        self.set_quad_offset(quad, self.quad_offsets[quad - 1] + inc)

    def set_quad_offset(self, quad, offset):
        self.quad_offsets[quad - 1] = offset
        quad_offsets_m = self.quad_offsets * self.pixel_size
        self.exgeom_obj = self.exgeom_obj_orig.offset(
            # Repeat each quadrant offset 4 times to get offsets per module
            np.repeat(quad_offsets_m, repeats=4, axis=0)
        )

    def get_quad_corners(self, quad, centre):
        """Get the bounding box of a quad.

        Parameters:
            quad (int): quadrant number
            centre (tuple): y, x coordinates of the detector centre
        """
        modules = Defaults.quad2slice[self.detector_name][quad]
        X = []
        Y = []
        for module in self.snapped_geom.modules[modules]:
            for tile in module:
                # Offset by centre to make all coordinates positive
                y, x = tile.corner_idx + centre - self.snapped_geom.centre
                h, w = tile.pixel_dims
                Y.append(y)
                Y.append(y+h)
                X.append(x)
                X.append(x)
        dy = abs(max(Y) - min(Y))
        dx = abs(max(X) - min(X))
        return (min(X)-2, min(Y)-2), dx+w+4, dy+4

    def position_all_modules(self, data, canvas=None):
        """Assemble data from this detector according to where the pixels are.

        Parameters
        ----------

        data : ndarray
          The last three dimensions should be channelno, pixel_ss, pixel_fs
          (lengths 16, 512, 128). ss/fs are slow-scan and fast-scan.
        canvas : tuple
          The shape of the canvas the out array will be embedded in.
          If None is given (default) no embedding will be applied.

        Returns
        -------
        out : ndarray
          Array with one dimension fewer than the input.
          The last two dimensions represent pixel y and x in the detector space.
        centre : ndarray
          (y, x) pixel location of the detector centre in this geometry.
        """
        if canvas is None:
            return self.exgeom_obj.position_modules_fast(data)
        else:
            out_shape = data.shape[:-3] + tuple(canvas)
            if np.issubdtype(data.dtype, np.floating):
                out = np.full(out_shape, np.nan, dtype=data.dtype)
            else:
                out = np.zeros(out_shape, dtype=data.dtype)
            self.exgeom_obj.position_modules_symmetric(data, out=out)
            cv_centre = (canvas[0]//2, canvas[-1]//2)
            return out, cv_centre

    def write_crystfel_geom(self, filename, *,
                            data_path='/entry_1/instrument_1/detector_1/data',
                            mask_path=None, dims=('frame', 'modno', 'ss', 'fs'),
                            adu_per_ev=None, clen=None, photon_energy=None):
        """Write this geometry to a CrystFEL format (.geom) geometry file.

        Parameters
        ----------

        filename : str
            Filename of the geometry file to write.
        data_path : str
            Path to the group that contains the data array in the hdf5 file.
            Default: ``'/entry_1/instrument_1/detector_1/data'``.
        mask_path : str
            Path to the group that contains the mask array in the hdf5 file.
        dims : tuple
            Dimensions of the data. Extra dimensions, except for the defaults,
            should be added by their index, e.g.
            ('frame', 'modno', 0, 'ss', 'fs') for raw data.
            Default: ``('frame', 'modno', 'ss', 'fs')``.
            Note: the dimensions must contain frame, modno, ss, fs.
        adu_per_ev : float
            ADU (analog digital units) per electron volt for the considered
            detector.
        clen : float
            Distance between sample and detector in meters
        photon_energy : float
            Beam wave length in eV
        """
        return self.exgeom_obj.write_crystfel_geom(filename, data_path=data_path,
                                                   mask_path=mask_path,
                                                   dims=dims,
                                                   adu_per_ev=adu_per_ev,
                                                   clen=clen,
                                                   photon_energy=photon_energy)
    def write_quad_pos(self, filename):
        """Write current quadrant positions to csv file.

        Parameters:
            filename (str): filename containing the quad postions
        """
        df = self.quad_pos
        log.info(' Quadrant positions:\n{}'.format(df))
        df.to_csv(filename)



class AGIPDGeometry(GeometryAssembler):
    """Detector layout for AGIPD-1M."""
    detector_name = 'AGIPD'

    def __init__(self, exgeom_obj):
        """Set the properties for AGIPD detector.

        Paramerters:
            exgeom_obj (AGIPD_1MGeometry) : extra_geom geometry objet
        """
        GeometryAssembler.__init__(self, exgeom_obj)
        self.unit = 2e-4
        self.pixel_size = 2e-4  # 2e-4 metres == 0.2 mm
        self.frag_ss_pixels = 64
        self.frag_fs_pixels = 128

    @classmethod
    def from_quad_positions(cls, quad_pos=None):
        """Generate geometry from quadrant positions."""
        quad_pos = quad_pos or Defaults.fallback_quad_pos[cls.detector_name]
        exgeom_obj = AGIPD_1MGeometry.from_quad_positions(quad_pos)
        return cls(exgeom_obj)

    @classmethod
    def from_crystfel_geom(cls, filename):
        """Load geometry from crystfel geometry."""
        try:
            exgeom_obj = AGIPD_1MGeometry.from_crystfel_geom(filename)
        except KeyError:
            # Probably some informations like clen and adu_per_eV missing
            with open(filename) as f:
                geom_file = f.read()
            with tempfile.NamedTemporaryFile() as temp:
                with open(temp.name, 'w') as f:
                    f.write("""clen = 0.118
adu_per_eV = 0.0075
"""+geom_file)
                exgeom_obj = AGIPD_1MGeometry.from_crystfel_geom(temp.name)
        return cls(exgeom_obj)

    @property
    def quad_pos(self):
        """Get quadrant positions."""
        return pd.DataFrame(self.exgeom_obj.quad_positions(),
                            index=['q{}'.format(i) for i in range(1, 5)],
                            columns=['X', 'Y'])


class DSSCGeometry(GeometryAssembler):
    """Detector layout for DSSC."""
    detector_name = 'DSSC'

    def __init__(self, exgeom_obj, filename):
        """Set the properties for DSSC detector.

        Paramerters:
            exgeom_obj (DSSCGeometry) : extra_geom geometry objet
            filename (str) : path to the hdf5 geometry description
        """
        GeometryAssembler.__init__(self, exgeom_obj)
        self.filename = filename
        self.pixel_size = 236e-6
        self.unit = 1e-3
        self.frag_ss_pixels = 128
        self.frag_fs_pixels = 256
        self._pixel_shape = np.array([1., 1.5/np.sqrt(3)])

    @classmethod
    def from_h5_file_and_quad_positions(cls, geom_file, quad_pos=None):
        """Create geometry from geometry file or quad positions."""
        quad_pos = quad_pos or Defaults.fallback_quad_pos[cls.detector_name]
        exgeom_obj = DSSC_1MGeometry.from_h5_file_and_quad_positions(
            geom_file,quad_pos
        )
        return cls(exgeom_obj, geom_file)

    @classmethod
    def from_quad_positions(cls, quad_pos):
        exgeom_obj = cls._extra_geom_from_quad_positions(quad_pos)
        return cls(exgeom_obj, None)

    @staticmethod
    def _extra_geom_from_quad_positions(quad_pos, *, unit=1e-3):
        # Copied here until the relevant code is merged in EXtra-geom
        assert len(quad_pos) == 4
        asic_gap_m = 2e-3
        panel_gap_m = 4e-3

        quads_x_orientation = [-1, -1, 1, 1]
        quads_y_orientation = [1, 1, -1, -1]

        cls = DSSC_1MGeometry
        frag_width = cls._pixel_shape[0] * cls.frag_fs_pixels
        frag_height = cls._pixel_shape[1] * cls.frag_ss_pixels
        module_width = (2 * frag_width) + asic_gap_m
        quad_height = (4 * frag_height) + (3 * panel_gap_m)

        module_step_vec = np.array([0, frag_height + panel_gap_m, 0])
        tile_step_vec = np.array([frag_width + asic_gap_m, 0, 0])

        modules = []

        for p in range(cls.n_modules):
            Q = p // 4
            x_orient = quads_x_orientation[Q]
            y_orient = quads_y_orientation[Q]
            quad_corner_x = quad_pos[Q][0] * unit
            quad_corner_y = quad_pos[Q][1] * unit

            p_in_quad = p % 4

            # Measuring in terms of the step within a row, the
            # step to the next row of hexagons is 1.5/sqrt(3).
            ss_vec = np.array([0, y_orient, 0]) * cls.pixel_size * 1.5 / np.sqrt(3)
            fs_vec = np.array([x_orient, 0, 0]) * cls.pixel_size

            # Corner position is measured at low-x, low-y corner (bottom
            # right as plotted). We want the position of the corner
            # with the first pixel, which is either high-x low-y or
            # low-x high-y.
            if x_orient == -1:
                quad_start_x = quad_corner_x + module_width
                quad_start_y = quad_corner_y
            else:  # y_orient == -1
                quad_start_x = quad_corner_x
                quad_start_y = quad_corner_y + quad_height

            quad_start = np.array([quad_start_x, quad_start_y, 0.])
            module_start = quad_start + (y_orient * p_in_quad * module_step_vec)

            modules.append([
                GeometryFragment(
                    corner_pos=module_start + (x_orient * t * tile_step_vec),
                    ss_vec=ss_vec,
                    fs_vec=fs_vec,
                    ss_pixels=cls.frag_ss_pixels,
                    fs_pixels=cls.frag_fs_pixels,
                ) for t in range(cls.n_tiles_per_module)
            ])

        return cls(modules)


    @property
    def quad_pos(self):
        """Get the quadrant positions from the geometry object."""
        quad_pos = self.exgeom_obj.quad_positions(self.filename)
        return pd.DataFrame(quad_pos,
                            columns=['X', 'Y'],
                            index=['q{}'.format(i) for i in range(1, 5)])


class LPDGeometry(GeometryAssembler):
    """Detector layout for LPD."""
    detector_name = 'LPD'

    def __init__(self, exgeom_obj, filename):
        """Set the properties for LPD detector.

        Paramerters:
            exgeom_obj (LPD_1MGeometry) : extra_geom geometry objet
            filename (str) : path to the hdf5 geometry description
        """
        GeometryAssembler.__init__(self, exgeom_obj)
        self.filename = filename
        self.unit = 1e-3
        self.pixel_size = 5e-4  # 5e-4 metres == 0.5 mm
        self.frag_ss_pixels = 32
        self.frag_fs_pixels = 128

    @classmethod
    def from_h5_file_and_quad_positions(cls, geom_file, quad_pos=None):
        """Create geometry from geometry file or quad positions."""
        quad_pos = quad_pos or Defaults.fallback_quad_pos[cls.detector_name]
        exgeom_obj = LPD_1MGeometry.from_h5_file_and_quad_positions(
            geom_file, quad_pos
        )
        return cls(exgeom_obj, geom_file)

    @classmethod
    def from_quad_positions(cls, quad_pos):
        exgeom_obj = LPD_1MGeometry.from_quad_positions(quad_pos)
        return cls(exgeom_obj, None)

    @classmethod
    def from_crystfel_geom(cls, filename):
        exgeom_obj = LPD_1MGeometry.from_crystfel_geom(filename)
        # filename used in .quad_pos is expected to be HDF5, so we don't store
        # the .geom filename here
        return cls(exgeom_obj, None)

    @property
    def quad_pos(self):
        """Get the quadrant positions from the geometry object."""
        quad_pos = self.exgeom_obj.quad_positions(self.filename)
        return pd.DataFrame(quad_pos,
                            columns=['X', 'Y'],
                            index=['q{}'.format(i) for i in range(1, 5)])


GEOM_CLASSES = {
    'AGIPD': AGIPDGeometry,
    'LPD': LPDGeometry,
    'DSSC': DSSCGeometry,
}



if __name__ == '__main__':
    geom = AGIPD_1MGeometry.from_quad_positions(quad_pos=[
        (-525, 625),
        (-550, -10),
        (520, -160),
        (542.5, 475),
    ])

    geom.write_crystfel_geom('sample.geom')
    geom = AGIPD_1MGeometry.from_crystfel_geom('sample.geom')
