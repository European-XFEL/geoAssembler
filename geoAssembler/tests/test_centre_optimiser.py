import geoAssembler.optimiser as centreOptimiser
import geoAssembler

from extra_data import RunDirectory, stack_detector_data
from extra_geom import AGIPD_1MGeometry

import numpy as np

import os.path

geom = AGIPD_1MGeometry.from_quad_positions(quad_pos=[
        (-525, 625),
        (-550, -10),
        (520, -160),
        (542.5, 475),
    ])

frame_path = os.path.dirname(geoAssembler.__file__) + "/tests/optimiser-test-frame.npy"
frame = np.load(frame_path)


def test_integrator():
    optimiser = centreOptimiser.CentreOptimiser(geom, frame, sample_dist_m=0.2)

    misaligned_2dint = optimiser.integrate2d(frame).intensity
    misaligned_2dint_r = optimiser.integrate2d(frame).radial
    misaligned_2dint_a = optimiser.integrate2d(frame).azimuthal

    assert misaligned_2dint.shape == (957, 832)
    assert misaligned_2dint_r.shape == (832,)
    assert misaligned_2dint_a.shape == (957,)

    misaligned_1dint = np.nanmean(misaligned_2dint, axis=0)[100:-100]
    misaligned_1dint_x = optimiser.integrate2d(frame).radial[100:-100]

    brightest_ring_idx = np.where(
        misaligned_1dint == np.max(misaligned_1dint
    ))[0][0]

    assert brightest_ring_idx == 106
