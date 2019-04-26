"""Provide AGIPD-D geometry information that supports quadrant moving."""

import logging
import os

import h5py
from karabo_data.geometry2 import (AGIPD_1MGeometry,
                                   LPD_1MGeometry, GeometryFragment)
import numpy as np
import pandas as pd

from . import __version__
from .defaults import *


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(os.path.basename(__file__))


class GeometryAssembler:
    """Base class for other methods.

    This base class provides methods for getting quad corners, moving them
    and positioning all modules.
    """

    filename = ''

    def move_quad(self, quad, inc):
        """Move the whole quad in a given direction.

        Parameters:
            quad (int): Quandrant number that is to be moved
            inc (collection): increment of the direction to be moved
        """
        pos = {1: 0, 2: 4, 3: 12, 4: 8}[quad]  # Translate quad into mod pos
        inc = np.array(list(inc)+[0])
        self.panel_gap = 4
        self.asic_gap = 4
        for i, module in enumerate(self.modules[pos:pos + 4]):
            n = pos + i
            for j, tile in enumerate(module):
                self.modules[n][j] = GeometryFragment(
                    tile.corner_pos+inc,
                    tile.ss_vec,
                    tile.fs_vec,
                    tile.ss_pixels,
                    tile.fs_pixels,
                )
        self._snapped_cache = None
        self.geom = self._snapped()

    def get_quad_corners(self, quad, centre):
        """Get the bounding box of a quad.

        Parameters:
            quad (int): quadrant number
            centre (tuple): y, x coordinates of the detector centre
        """
        pos = {1: 0, 2: 4, 3: 12, 4: 8}[quad]  # Translate quad into mod pos
        X = []
        Y = []
        for i, module in enumerate(self.geom.modules[pos:pos + 4]):
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

    def position(self, data, canvas=None):
        """Assemble data from this detector according to where the pixels are.

        Parameters
        ----------

        data : ndarray
          The last three dimensions should be channelno, pixel_ss, pixel_fs
          (lengths 16, 512, 128). ss/fs are slow-scan and fast-scan.

        Returns
        -------
        out : ndarray
          Array with one dimension fewer than the input.
          The last two dimensions represent pixel y and x in the detector space.
        centre : ndarray
          (y, x) pixel location of the detector centre in this geometry.
        """
        if canvas is None:
            size_yx, centre = self.geom._get_dimensions()
        else:
            size_yx = canvas
            centre = (canvas[0]//2, canvas[-1]//2)
        out = np.full(data.shape[:-3] + size_yx, np.nan, dtype=data.dtype)

        for i, module in enumerate(self.geom.modules):
            mod_data = data[..., i, :, :]
            tiles_data = self.split_tiles(mod_data)
            for j, tile in enumerate(module):
                tile_data = tiles_data[j]
                # Offset by centre to make all coordinates positive
                y, x = tile.corner_idx + centre
                h, w = tile.pixel_dims
                out[..., y: y + h, x: x + w] = tile.transform(tile_data)
        return out, centre

    def _get_offsets(self, quad, module, asic, unit):
        """Get the panel and asic offsets."""
        try:
            with h5py.File(self.filename, 'r') as f:
                mod_grp = f['Q{}/M{}'.format(quad, module)]
                mod_offset = mod_grp['Position'][:]
                tile_offset = mod_grp['T{:02}/Position'.format(asic)][:]
            return mod_offset, tile_offset
        except (FileNotFoundError, ValueError):
            px_conv = self.pixel_size / unit
            return px_conv * self.panel_gap, px_conf * self.asic_gap

    def write_geom(self, *args, **kwargs):
        """Write the current quad positions to a csv file."""
        df = self.quad_pos
        log.info(' Quadrant positions:\n{}'.format(df))
        df.to_csv(args[0])

    @property
    def quad_pos(self):
        """Get the quadrant positions from the geometry object."""
        quads = {mod // 4 + 1: [] for mod in range(len(self.modules))}
        quad_pos = np.zeros((len(quads), 2))
        unit = 1e-3
        px_conversion = self.pixel_size / unit
        for m, mod in enumerate(self.modules):
            q = m // 4 + 1
            mm = m % 4 + 1
            for asic, frag in enumerate(mod):
                cr_pos = (frag.corner_pos +
                          (frag.ss_vec * self.frag_ss_pixels) +
                          (frag.fs_vec * self.frag_fs_pixels))[:2]
                cr_pos *= px_conversion
                mod_offset, tile_offset = self._get_offsets(
                    q, mm, asic+1, unit)
                quad_pos[q-1] = (cr_pos - tile_offset - mod_offset)
        return pd.DataFrame(quad_pos,
                            columns=['Y', 'X'],
                            index=['q{}'.format(i+1) for i in range(4)])


class AGIPDGeometry(GeometryAssembler, AGIPD_1MGeometry):
    """Detector layout for AGIPD-1M.

    The coordinates used in this class are 3D (x, y, z), and represent multiples
    of the pixel size.
    """

    def __init__(self, modules, **kwargs):
        """Inherit from AGIPD_1MGeometry in karabo_data."""
        super(AGIPD_1MGeometry, self).__init__(modules)
        self.geom = self._snapped()

    @classmethod
    def load(cls, geom_file=None, quad_pos=None):
        """Create geometry from geometry file or quad positions."""
        quad_pos = quad_pos or FALLBACK_QUAD_POS['AGIPD']
        try:
            return cls.from_crystfel_geom(geom_file)
        except (FileNotFoundError, ValueError):
            log.warning(' Using fallback option')
            return cls.from_quad_positions(list(quad_pos))

    def write_geom(self, *args, **kwargs):
        """Overwrite the write_crystfel_geom method to provide a header."""
        filename = args[0]
        header = kwargs.get('header', '')
        version = __version__
        panel_chunks = []
        for p, module in enumerate(self.modules):
            for a, fragment in enumerate(module):
                panel_chunks.append(fragment.to_crystfel_geom(p, a))

        with open(filename, 'w') as f:
            f.write(CRYSTFEL_HEADER_TEMPLATE.format(version=version,
                                                    header=header))
            for chunk in panel_chunks:
                f.write(chunk)

        @property
        def quad_pos(self):
            return None


class LPDGeometry(GeometryAssembler, LPD_1MGeometry):
    """Detector layout for LPD."""

    def __init__(self, modules, **kwargs):
        """Inherit from LPD_1MGeometry in karabo_data."""
        super(LPD_1MGeometry, self).__init__(modules)
        self.geom = self._snapped()

    @classmethod
    def load(cls, geom_file=None, quad_pos=None):
        """Create geometry from geometry file or quad positions."""
        quad_pos = quad_pos or FALLBACK_QUAD_POS['LPD']
        try:
            C = cls.from_h5_file_and_quad_positions(geom_file, list(quad_pos))
            C.filename = geom_file
            C.asic_gap = None
            C.panel_gap = None
            return C
        except (FileNotFoundError, ValueError):
            log.warning(' Using fallback option')
            C = cls.from_quad_positions(list(quad_pos))
            C.filename = None
            C.asic_gap = 4
            C.panel_gap = 4
            return C


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

if __name__ == '__main__':
    geom = AGIPD_1MGeometry.from_quad_positions(quad_pos=[
        (-525, 625),
        (-550, -10),
        (520, -160),
        (542.5, 475),
    ])

    geom.write_crystfel_geom('sample.geom')
    geom = AGIPD_1MGeometry.from_crystfel_geom('sample.geom')
