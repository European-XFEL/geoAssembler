"""Provide AGIPD-D geometry information that supports quadrant moving."""

import logging
import tempfile

import h5py
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
        self.exgeom_obj = exgeom_obj

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
            quad (int): Quandrant number that is to be moved
            inc (collection): increment of the direction to be moved
        """
        pos = Defaults.quad2index[self.detector_name][quad]
        if len(inc) == 2:
            inc = np.array(list(inc)+[0])
        new_modules = [_move_mod(m, inc * self.pixel_size) if (pos <= i < pos + 4) else m
                       for i, m in enumerate(self.modules)]
        exgeom_cls = type(self.exgeom_obj)
        self.exgeom_obj = exgeom_cls(new_modules)

    @property
    def _px_conv(self):
        return self.pixel_size / self.unit

    def get_quad_corners(self, quad, centre):
        """Get the bounding box of a quad.

        Parameters:
            quad (int): quadrant number
            centre (tuple): y, x coordinates of the detector centre
        """
        pos = Defaults.quad2index[self.detector_name][quad]
        X = []
        Y = []
        for i, module in enumerate(self.snapped_geom.modules[pos:pos + 4]):
            for j, tile in enumerate(module):
                # Offset by centre to make all coordinates positive
                y, x = tile.corner_idx + centre
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
        canvas : ndarray
          The canvas the out array will be embeded in. If None is given
          (default) no embedding will be applied.

        Returns
        -------
        out : ndarray
          Array with one dimension fewer than the input.
          The last two dimensions represent pixel y and x in the detector space.
        centre : ndarray
          (y, x) pixel location of the detector centre in this geometry.
        """
        if canvas is None:
            size_yx, centre = self.snapped_geom._get_dimensions()
            out = np.full(data.shape[:-3] + size_yx, np.nan, dtype=data.dtype)
        else:
            _, centre = self.snapped_geom._get_dimensions()
            size_yx = canvas
            cv_centre = (canvas[0]//2, canvas[-1]//2)
            shift = np.array(centre) - np.array(cv_centre)
            out = np.full(data.shape[:-3] + size_yx, np.nan, dtype=data.dtype)
            out = np.roll(out, shift[0], axis=-2)
            out = np.roll(out, shift[1], axis=-1)
            centre -= shift
        for i, module in enumerate(self.snapped_geom.modules):
            mod_data = data[..., i, :, :]
            tiles_data = self.exgeom_obj.split_tiles(mod_data)
            for j, tile in enumerate(module):
                tile_data = tiles_data[j]
                # Offset by centre to make all coordinates positive
                y, x = tile.corner_idx + centre
                h, w = tile.pixel_dims
                s = tile.transform(tile_data)
                out[..., y: y + h, x: x + w] = tile.transform(tile_data)
        return out, centre

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
        quad = {i:[] for i in range(1,5)}
        for n, mod in enumerate(self.modules):
            q = n // 4 + 1
            for a, asic in enumerate(mod):
                quad[q].append(asic.corner_pos[:2])

        quad_pos = []
        for i in range(1, 5):
            if i < 3:
                quad_pos.append((np.array(quad[i])[:,0].min(),
                                np.array(quad[i])[:,1].max()))
            else:
                quad_pos.append((np.array(quad[i])[:,0].max(),
                                np.array(quad[i])[:,1].max()))
        return pd.DataFrame(quad_pos,
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

    @property
    def quad_pos(self):
        """Get the quadrant positions from the geometry object."""
        quad_pos = np.zeros((4, 2))
        for q in range(1, 5):
            # Getting the offset for one tile (4th module, 2nd tile)
            # is sufficient
            quad_pos[q-1] = self._get_offsets(q, 1, 1)
        return pd.DataFrame(quad_pos,
                            columns=['Y', 'X'],
                            index=['q{}'.format(i) for i in range(1, 5)])

    def _get_offsets(self, quad, module, asic):
        """Get the panel and asic offsets."""
        quads_x_orientation = [-1, -1, 1, 1]
        #quads_y_orientation = [1, 1, -1, -1]
        x_orient = quads_x_orientation[quad - 1]
        #y_orient = quads_y_orientation[quad - 1]
        nmod = (quad-1) * 4 + module
        frag = self.modules[nmod-1][asic-1]
        if x_orient == -1:
            cr_pos = (frag.corner_pos + (frag.fs_vec * self.frag_fs_pixels))[:2]
        else:
            cr_pos = (frag.corner_pos + (frag.ss_vec * self.frag_ss_pixels))[:2]

        with h5py.File(self.filename, 'r') as f:
            mod_grp = f['Q{}/M{}'.format(quad, module)]
            mod_offset = mod_grp['Position'][:]
            tile_offset = mod_grp['T{:02}/Position'.format(asic)][:]
        return (cr_pos / self.unit) - (mod_offset + tile_offset)



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

    @property
    def quad_pos(self):
        """Get the quadrant positions from the geometry object."""
        quad_pos = np.zeros((4, 2))
        for q in range(1, 5):
            # Getting the offset for one tile (4th module, 16th tile)
            # is sufficient
            quad_pos[q-1] = self._get_offsets(q, 4, 16)
        return pd.DataFrame(quad_pos,
                            columns=['Y', 'X'],
                            index=['q{}'.format(i) for i in range(1, 5)])

    def _get_offsets(self, quad, module, asic):
        """Get the panel and asic offsets."""
        nmod = (quad-1) * 4 + module
        frag = self.modules[nmod-1][asic-1]
        cr_pos = (frag.corner_pos +
                  (frag.ss_vec * self.frag_ss_pixels) +
                  (frag.fs_vec * self.frag_fs_pixels))[:2]
        with h5py.File(self.filename, 'r') as f:
            mod_grp = f['Q{}/M{}'.format(quad, module)]
            mod_offset = mod_grp['Position'][:]
            tile_offset = mod_grp['T{:02}/Position'.format(asic)][:]
            cr_pos *= self._px_conv
        return cr_pos - (mod_offset + tile_offset)

CRYSTFEL_HEADER_TEMPLATE = """\
; AGIPD-1M geometry file written by geoAssembler {version}
; You may need to edit this file to add:
; - data and mask locations in the file
; - mask_good & mask_bad values to interpret the mask
; - adu_per_eV & photon_energy
; - clen (detector distance)
;
; See: http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html

{header}
dim0 = %
res = 5000 ; 200 um pixels
rigid_group_q0 = p0a0,p0a1,p0a2,p0a3,p0a4,p0a5,p0a6,p0a7,p1a0,p1a1,p1a2,p1a3,p1a4,p1a5,p1a6,p1a7,p2a0,p2a1,p2a2,p2a3,p2a4,p2a5,p2a6,p2a7,p3a0,p3a1,p3a2,p3a3,p3a4,p3a5,p3a6,p3a7
rigid_group_q1 = p4a0,p4a1,p4a2,p4a3,p4a4,p4a5,p4a6,p4a7,p5a0,p5a1,p5a2,p5a3,p5a4,p5a5,p5a6,p5a7,p6a0,p6a1,p6a2,p6a3,p6a4,p6a5,p6a6,p6a7,p7a0,p7a1,p7a2,p7a3,p7a4,p7a5,p7a6,p7a7
rigid_group_q2 = p8a0,p8a1,p8a2,p8a3,p8a4,p8a5,p8a6,p8a7,p9a0,p9a1,p9a2,p9a3,p9a4,p9a5,p9a6,p9a7,p10a0,p10a1,p10a2,p10a3,p10a4,p10a5,p10a6,p10a7,p11a0,p11a1,p11a2,p11a3,p11a4,p11a5,p11a6,p11a7
rigid_group_q3 = p12a0,p12a1,p12a2,p12a3,p12a4,p12a5,p12a6,p12a7,p13a0,p13a1,p13a2,p13a3,p13a4,p13a5,p13a6,p13a7,p14a0,p14a1,p14a2,p14a3,p14a4,p14a5,p14a6,p14a7,p15a0,p15a1,p15a2,p15a3,p15a4,p15a5,p15a6,p15a7

rigid_group_p0 = p0a0,p0a1,p0a2,p0a3,p0a4,p0a5,p0a6,p0a7
rigid_group_p1 = p1a0,p1a1,p1a2,p1a3,p1a4,p1a5,p1a6,p1a7
rigid_group_p2 = p2a0,p2a1,p2a2,p2a3,p2a4,p2a5,p2a6,p2a7
rigid_group_p3 = p3a0,p3a1,p3a2,p3a3,p3a4,p3a5,p3a6,p3a7
rigid_group_p4 = p4a0,p4a1,p4a2,p4a3,p4a4,p4a5,p4a6,p4a7
rigid_group_p5 = p5a0,p5a1,p5a2,p5a3,p5a4,p5a5,p5a6,p5a7
rigid_group_p6 = p6a0,p6a1,p6a2,p6a3,p6a4,p6a5,p6a6,p6a7
rigid_group_p7 = p7a0,p7a1,p7a2,p7a3,p7a4,p7a5,p7a6,p7a7
rigid_group_p8 = p8a0,p8a1,p8a2,p8a3,p8a4,p8a5,p8a6,p8a7
rigid_group_p9 = p9a0,p9a1,p9a2,p9a3,p9a4,p9a5,p9a6,p9a7
rigid_group_p10 = p10a0,p10a1,p10a2,p10a3,p10a4,p10a5,p10a6,p10a7
rigid_group_p11 = p11a0,p11a1,p11a2,p11a3,p11a4,p11a5,p11a6,p11a7
rigid_group_p12 = p12a0,p12a1,p12a2,p12a3,p12a4,p12a5,p12a6,p12a7
rigid_group_p13 = p13a0,p13a1,p13a2,p13a3,p13a4,p13a5,p13a6,p13a7
rigid_group_p14 = p14a0,p14a1,p14a2,p14a3,p14a4,p14a5,p14a6,p14a7
rigid_group_p15 = p15a0,p15a1,p15a2,p15a3,p15a4,p15a5,p15a6,p15a7

rigid_group_collection_quadrants = q0,q1,q2,q3
rigid_group_collection_asics = p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12,p13,p14,p15

"""


CRYSTFEL_PANEL_TEMPLATE = """
{name}/dim1 = {p}
{name}/dim2 = ss
{name}/dim3 = fs
{name}/min_fs = 0
{name}/min_ss = {min_ss}
{name}/max_fs = 127
{name}/max_ss = {max_ss}
{name}/fs = {fs_vec}
{name}/ss = {ss_vec}
{name}/corner_x = {corner_x}
{name}/corner_y = {corner_y}
{name}/coffset = {coffset}
"""

GEOM_MODULES = {'AGIPD': AGIPDGeometry,
                'LPD': LPDGeometry}



if __name__ == '__main__':
    geom = AGIPD_1MGeometry.from_quad_positions(quad_pos=[
        (-525, 625),
        (-550, -10),
        (520, -160),
        (542.5, 475),
    ])

    geom.write_crystfel_geom('sample.geom')
    geom = AGIPD_1MGeometry.from_crystfel_geom('sample.geom')
