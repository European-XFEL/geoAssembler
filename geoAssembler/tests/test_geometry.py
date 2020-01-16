import numpy as np

from ..geometry import AGIPDGeometry

def test_snap_assemble_data():
    """Tes the crude assembly with quadrant positions."""
    geom = AGIPDGeometry.from_quad_positions(quad_pos=[
        (-525, 625),
        (-550, -10),
        (520, -160),
        (542.5, 475),
    ])

    stacked_data = np.zeros((16, 512, 128))
    img, centre = geom.position_all_modules(stacked_data)
    assert img.shape == (1256, 1092)
    assert tuple(centre) == (631, 550)
    assert np.isnan(img[0, 0])
    assert img[50, 50] == 0

def test_write_read_crystfel_file(tmpdir):
    """Try writing geometry to crysFEL files."""
    geom = AGIPDGeometry.from_quad_positions(quad_pos=[
        (-525, 625),
        (-550, -10),
        (520, -160),
        (542.5, 475),
    ])
    path = str(tmpdir / 'test.geom')
    geom.write_crystfel_geom(path)

    # We need to add some experiment details before cfelpyutils will read the
    # file
    with open(path, 'r') as f:
        contents = f.read()
    with open(path, 'w') as f:
        f.write('clen = 0.119\n')
        f.write('adu_per_eV = 0.0075\n')
        f.write(contents)

    loaded = AGIPDGeometry.from_crystfel_geom(path)
    np.testing.assert_allclose(loaded.modules[0][0].corner_pos,
                               geom.modules[0][0].corner_pos)
    np.testing.assert_allclose(loaded.modules[0][0].fs_vec,
                               geom.modules[0][0].fs_vec)

def test_move_quad():
    """Move the quadrant by left/right/up/down."""
    geom = AGIPDGeometry.from_quad_positions(quad_pos=[
        (-525, 625),
        (-550, -10),
        (520, -160),
        (542.5, 475),
    ])

    asic = geom.modules[0][0]
    corners_before = asic.corner_pos

    geom.move_quad(1, np.array((0,-1)))
    geom.move_quad(1, np.array((1,0)))

    delta = np.array([1, -1, 0]) * geom.pixel_size
    np.testing.assert_allclose(geom.modules[0][0].corner_pos,
                               corners_before + delta)

    # Move back to original position
    geom.move_quad(1, np.array((-1,0)))
    geom.move_quad(1, np.array((0,1)))

    np.testing.assert_allclose(geom.modules[0][0].corner_pos,
                               corners_before)

def get_quad_corners():
    """The the mothod returning the quadrant corners."""
    geom = AGIPDGeometry.from_quad_positions(quad_pos=[
        (-525, 625),
        (-550, -10),
        (520, -160),
        (542.5, 475),
    ])
    stacked_data = np.zeros((16, 512, 128))
    _, centre = geom.position_all_modules(stacked_data)
    corner, width, height = geom.get_quad_corners(1, centre)
    assert corner == (23, 655)
    assert width == 530
    assert height == 603

