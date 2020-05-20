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

stacked_mean_path = os.path.dirname(geoAssembler.__file__) + "/tests/optimiser-test-frame.npy"


def test_integrator():
    stacked_mean = np.load(stacked_mean_path)

    optimiser = centreOptimiser.CentreOptimiser(geom, stacked_mean, sample_dist_m=0.2)

    integrated_result = optimiser.integrate2d(optimiser.frame)
    misaligned_2dint = integrated_result.intensity
    misaligned_2dint_r = integrated_result.radial
    misaligned_2dint_a = integrated_result.azimuthal

    assert 827 < misaligned_2dint_r.shape[0] < 837
    assert 952 < misaligned_2dint_a.shape[0] < 962

    misaligned_1dint = np.nanmean(misaligned_2dint, axis=0)[100:-100]

    brightest_ring_idx = np.where(
        misaligned_1dint == np.max(misaligned_1dint
    ))[0][0]

    assert 100 < brightest_ring_idx < 110
