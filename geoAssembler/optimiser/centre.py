from collections import namedtuple
from itertools import product
from typing import Union

import numpy as np
from extra_geom.detectors import DetectorGeometryBase
from scipy.optimize import differential_evolution

from .utility import Integrator


class CentreOptimiser:
    """
    Object used to manage the optimisation of the centre position
    via maximization of the azimuthal integration result.

    The centre position leading to the highest azimuthal integration
    value at a radial bin should be the one where the diffraction
    rings form as straight a line as possible, and the rings becoming
    straight lines in polar coordinates indicates an accurate centre.
    """
    def __init__(self, geom: DetectorGeometryBase,
                 frame: np.ndarray, sample_dist_m: Union[int, float],
                 unit: str = "2th_deg"):
        self.frame = frame
        self.integrator = Integrator(geom, sample_dist_m, unit)
        self.integrate2d = self.integrator.integrate2d

        #  Slightly dodgy way to pull the quadrant corner positions out of geom
        #  TODO: Suggest adding this in to extra-geom?
        self.original_quadrant_pos = [
            m[0].corners()[0, :2]/geom.pixel_size
            for m
            in geom.modules
        ][::4]

    def _loss_function(self, centre_offset):
        """
        Simple cost function which computes the 1d azimuthal integration
        result with a centre offset, it then returns one over this result
        so that it can be minimised.

        Note: the first and last 100 radial bins are excluded, as these can
        lead to artefacts which cause the optimisation to fail.

        Parameters
        ----------

        centre_offset: pair of values
            Sets the centre position of the search grid.
        """
        res = self.integrator.integrate2d(
            self.frame,
            centre_offset=centre_offset
        ).intensity

        #  Slice off the ends as they are not reliable
        return 1/np.max(np.nanmean(res, axis=0)[100:-100])

    def optimise(self, bounds=[(-50, 50), (-50, 50)], workers=1, verbose=False):
        """
        Function which performs a grid-search which goes from coarse to fine
        coordinates, defined by `r_step_pairs`.

        Parameters
        ----------

        r_step_pairs: list of tuples
            A list of tuple pair of radius and step size, where the optimum
            coordinates of the previous grid are used as the centre for the
            subsequent grid.

            e.g. `[(50, 10), (10, 2)]` creates a grid of pixel of pixel
            coordinates from -50 to +50, with steps of 10, so an 11x11 grid.

            The optimal position is then fed into the next step, which uses a
            grid from -10 to +10, with steps of 2, centred on the previous pos.

        pool: a multiprocessing Pool object
            Used to enable multiprocessing over multiple threads, it is
            recommended to only use 32 threads, the number of threads
            should increase if larger grids are used.
        """
        res_tuple = namedtuple(
            "OptimiseResult", "optimal_quad_positions optimal_offset results"
        )

        results = differential_evolution(
            self._loss_function,
            bounds,
            workers=workers,
            disp=verbose
        )

        centre_offset = results.x

        #  Subtract the centre offset to move the modules in the correct
        #  way to shift the centre
        optimal_quad_positions = [
            tuple(qp - centre_offset)
            for qp
            in self.original_quadrant_pos
        ]

        oqp = (
            "[",
            "".join([f"\n    {c}," for c in optimal_quad_positions]),
            "\n]"
        )
        print("Optimal quad positions: ", "".join(oqp))

        return res_tuple(optimal_quad_positions, centre_offset, results)
