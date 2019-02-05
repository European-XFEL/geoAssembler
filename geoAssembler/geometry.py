from cfelpyutils.crystfel_utils import load_crystfel_geometry
import numpy as np
from . import __version__

def _crystfel_format_vec(vec):
    """Convert an array of 3 numbers to CrystFEL format like "+1.0x -0.1y"
    """
    s = '{:+}x {:+}y'.format(*vec[:2])
    try:
        if vec[2] != 0:
            s += ' {:+}z'.format(vec[2])
    except IndexError:
        pass
    return s


class AGIPDGeometryFragment:
    ss_pixels = 64
    fs_pixels = 128

    # The coordinates in this class are (x, y, z), in pixel units
    def __init__(self, corner_pos, ss_vec, fs_vec):
        self.corner_pos = corner_pos
        self.ss_vec = ss_vec
        self.fs_vec = fs_vec

    @classmethod
    def from_panel_dict(cls, d):
        corner_pos = np.array([d['cnx'], d['cny']])
        ss_vec = np.array([d['ssx'], d['ssy']])
        fs_vec = np.array([d['fsx'], d['fsy']])
        return cls(corner_pos, ss_vec, fs_vec)

    def corners(self):
        return np.stack([
            self.corner_pos,
            self.corner_pos + (self.fs_vec * self.fs_pixels),
            self.corner_pos + (self.ss_vec * self.ss_pixels) +
            (self.fs_vec * self.fs_pixels),
            self.corner_pos + (self.ss_vec * self.ss_pixels),
        ])

    def centre(self):
        return self.corner_pos + (.5 * self.ss_vec * self.ss_pixels) \
                               + (.5 * self.fs_vec * self.fs_pixels)

    def snap(self):
        corner_pos = np.around(self.corner_pos[:2]).astype(np.int32)
        ss_vec = np.around(self.ss_vec[:2]).astype(np.int32)
        fs_vec = np.around(self.fs_vec[:2]).astype(np.int32)
        assert {tuple(np.abs(ss_vec)), tuple(
            np.abs(fs_vec))} == {(0, 1), (1, 0)}
        # Convert xy coordinates to yx indexes
        return GridGeometryFragment(corner_pos[::-1], ss_vec[::-1], fs_vec[::-1])


class GridGeometryFragment:
    ss_pixels = 64
    fs_pixels = 128

    # These coordinates are all (y, x), suitable for indexing a numpy array.
    def __init__(self, corner_pos, ss_vec, fs_vec):
        self.ss_vec = ss_vec
        self.fs_vec = fs_vec
        if fs_vec[0] == 0:
            # Flip without transposing
            fs_order = fs_vec[1]
            ss_order = ss_vec[0]
            self.transform = lambda arr: arr[..., ::ss_order, ::fs_order]
            corner_shift = np.array([
                min(ss_order, 0) * self.ss_pixels,
                min(fs_order, 0) * self.fs_pixels
            ])
            self.pixel_dims = np.array([self.ss_pixels, self.fs_pixels])
        else:
            # Transpose and then flip
            fs_order = fs_vec[0]
            ss_order = ss_vec[1]
            self.transform = lambda arr: arr.swapaxes(
                -1, -2)[..., ::fs_order, ::ss_order]
            corner_shift = np.array([
                min(fs_order, 0) * self.fs_pixels,
                min(ss_order, 0) * self.ss_pixels
            ])
            self.pixel_dims = np.array([self.fs_pixels, self.ss_pixels])
        self.corner_idx = corner_pos + corner_shift
        self.corner_pos = corner_pos
        self.opp_corner_idx = self.corner_idx + self.pixel_dims

    def to_crystfel_geom(self, p, a):
        name = 'p{}a{}'.format(p, a)
        c = self.corner_pos[::1]
        cr = CRYSTFEL_PANEL_TEMPLATE.format(
            name=name, p=p,
            min_ss=(a * self.ss_pixels), max_ss=(((a + 1) * self.ss_pixels) - 1),
            ss_vec=_crystfel_format_vec(self.ss_vec[::-1]),
            fs_vec=_crystfel_format_vec(self.fs_vec[::-1]),
            corner_x=c[1], corner_y=c[0], coffset=0,
        )
        return cr


class AGIPD_1MGeometry:
    """Detector layout for AGIPD-1M

    The coordinates used in this class are 3D (x, y, z), and represent multiples
    of the pixel size.
    """
    pixel_size = 2e-7  # 2e-7 metres == 0.2 mm

    def __init__(self, modules, quad_pos):
        self.modules = modules  # List of 16 lists of 8 fragments
        self.quad_pos = quad_pos

    @classmethod
    def from_quad_positions(cls, quad_pos, asic_gap=2, panel_gap=29):
        """Generate an AGIPD-1M geometry from quadrant positions.

        This produces an idealised geometry, assuming all modules are perfectly
        flat, aligned and equally spaced within their quadrant.

        The quadrant positions are given in pixel units, referring to the first
        pixel of the first module in each quadrant.
        """
        quads_x_orientation = [1, 1, -1, -1]
        quads_y_orientation = [-1, -1, 1, 1]
        modules = []
        for p in range(16):
            quad = p // 4
            quad_corner = quad_pos[quad]
            x_orient = quads_x_orientation[quad]
            y_orient = quads_y_orientation[quad]
            p_in_quad = p % 4
            corner_y = quad_corner[1] - (p_in_quad * (128 + panel_gap))

            tiles = []
            modules.append(tiles)

            for a in range(8):
                corner_x = quad_corner[0] + x_orient * (64 + asic_gap) * a
                tiles.append(AGIPDGeometryFragment(
                    corner_pos=np.array([corner_x, corner_y, 0.]),
                    ss_vec=np.array([x_orient, 0, 0]),
                    fs_vec=np.array([0, y_orient, 0]),
                ).snap())

        return cls(modules, quad_pos)

    def move_quad(self, quad, inc):
        pos = {1:0, 2:4, 3:12, 4:8}[quad] #Translate quad into mod pos

        for i, module in enumerate(self.modules[pos:pos + 4]):
            n = pos + i
            for j, tile in enumerate(module):

                self.modules[n][j] = GridGeometryFragment(tile.corner_pos+inc,
                                                          tile.ss_vec,
                                                          tile.fs_vec)

    def get_quad_corners(self, quad, centre):
        pos = {1:0, 2:4, 3:12, 4:8}[quad] #Translate quad into mod pos
        X = []
        Y = []
        for i, module in enumerate(self.modules[pos:pos + 4]):
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

    @classmethod
    def from_crystfel_geom(cls, filename):
        geom_dict = load_crystfel_geometry(filename)
        modules = []
        quad_pos = []
        for p in range(16):
            tiles = []
            modules.append(tiles)
            for a in range(8):
                d = geom_dict['panels']['p{}a{}'.format(p, a)]
                tiles.append(AGIPDGeometryFragment.from_panel_dict(d).snap())
                if p % 4 == 0 and a == 0:
                    quad_pos.append(tuple(tiles[-1].corner_pos[:-1]))
        return cls(modules, quad_pos)

    def write_crystfel_geom(self, filename, header=''):

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

    def position_all_modules(self, data, canvas=None):
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
        assert data.shape[-3:] == (16, 512, 128)
        if canvas is None:
            size_yx, centre = self._plotting_dimensions()
        else:
            size_yx = canvas
            centre = (canvas[0]//2, canvas[-1]//2)
        out = np.full(data.shape[:-3] + size_yx, np.nan, dtype=data.dtype)
        for i, module in enumerate(self.modules):
            mod_data = data[..., i, :, :]
            tiles_data = np.split(mod_data, 8, axis=-2)
            for j, tile in enumerate(module):
                tile_data = tiles_data[j]
                # Offset by centre to make all coordinates positive
                y, x = tile.corner_idx + centre
                h, w = tile.pixel_dims
                out[..., y:y+h, x:x+w] = tile.transform(tile_data)

        return out, centre

    def _plotting_dimensions(self):
        """Calculate appropriate dimensions for plotting assembled data

        Returns (size_y, size_x), (centre_y, centre_x)
        """
        corners = []
        for module in self.modules:
            for tile in module:
                corners.append(tile.corner_idx)
                corners.append(tile.opp_corner_idx)
        corners = np.stack(corners)

        # Find extremes
        min_yx = corners.min(axis=0)
        max_yx = corners.max(axis=0)

        size = max_yx - min_yx
        centre = -min_yx
        return tuple(size), centre


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
