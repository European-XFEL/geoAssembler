import numpy as np

from collections import namedtuple
from itertools import product

from .utility import Integrator

from karabo_data.geometry2 import DetectorGeometryBase
from typing import Union, Tuple


class CentreOptimiser:
    def __init__(self, geom: DetectorGeometryBase,
                 frame: np.ndarray, sample_dist_mm: Union[int, float],
                 unit: str = "2th_deg"):
        self.frame = frame
        self.integrator = Integrator(geom, sample_dist_mm, unit)

    def _minimiser(self, centre_offset):
        res = self.integrator.integrate2d(
            self.frame,
            centre_offset=centre_offset
        ).intensity

        #  Slice off the ends as they are not reliable
        #  also multiply by 1e6 to scale the results up
        #  otherwise they could get very small
        return 1e6/np.max(np.nanmean(res, axis=0)[100:-100])

    def _find_centre(self,
                     radius: Union[int, float], stepsize: Union[int, float],
                     base_offset=[0, 0], pool=None, verbose=False):
        res_tuple = namedtuple("Result", "centre array xs ys")
        xs = np.arange(-radius, radius+stepsize, stepsize) + base_offset[0]
        ys = np.arange(-radius, radius+stepsize, stepsize) + base_offset[1]

        print(f"Trying {len(xs)**2} combinations, "
              f"radius {radius}, stepsize {stepsize} - ", end='')

        if pool is not None:
            min_array = pool.map(self._minimiser, product(xs, ys))
        else:
            min_array = map(self._minimiser, product(xs, ys))

        min_array = np.array(list(min_array))
        min_array = np.reshape(min_array, (len(xs), len(ys)))

        centre_idx = [x[0] for x in np.where(min_array == np.amin(min_array))]
        centre = np.array([xs[centre_idx[0]], ys[centre_idx[1]]])

        if verbose:
            print(f"found centre at -> {centre}")

        res = res_tuple(
            centre,
            min_array,
            xs, ys
        )

        return res

    def optimise(self, r_step_pairs=[(50, 10), (10, 2), (3, 0.5)], pool=None):
        centre_offset = [0, 0]
        results = []

        for radius, stepsize in r_step_pairs:
            res = self._find_centre(
                radius, stepsize,
                centre_offset,
                verbose=True,
                pool=pool
            )

            centre_offset = res.centre

            results.append(res)

        return centre_offset, results
