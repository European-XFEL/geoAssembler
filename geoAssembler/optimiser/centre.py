import numpy as np

from collections import namedtuple
from itertools import product

from .utility import Integrator

from extra_geom.detectors import DetectorGeometryBase
from typing import Union


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
        self.original_centre = [
            m[0].corners()[0, :2]*geom._get_plot_scale_factor('px')
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

    def _find_centre(self,
                     radius: Union[int, float], stepsize: Union[int, float],
                     centre_offset=[0, 0], pool=None, verbose=False):
        """
        Creates a grid of (2*radius/stepsize)^2 coordinates around the given
        centre offset, applies the `_loss_function` to the grid and returns the
        coordinates of the minimum value.

        Can optionally take in a `pool` for parallelisation.

        Parameters
        ----------

        radius: int or float
            Half of the width of the coordinate grid used during the search,
            not really a radius as the grid is square. The grid is inclusive
            and will range from -r to +r.

        stepsize: int or float
            Size of steps used when creating the grid, if the radius is 10
            and the steps are 2 then it will go: [-10, -8, ..., 0, ... 8, 10]

        centre_offset: pair of values
            Sets the centre position of the search grid.

        pool: a multiprocessing Pool object
            Used to enable multiprocessing over multiple threads, it is
            recommended to only use 32 threads, the number of threads
            should increase if larger grids are used.

        verbose: Bool
            Set to true to print status and progress messages.
        """
        res_tuple = namedtuple("FindCentreResult", "centre array xs ys")
        xs = np.arange(-radius, radius+stepsize, stepsize) + centre_offset[0]
        ys = np.arange(-radius, radius+stepsize, stepsize) + centre_offset[1]

        if verbose:
            print(f"Trying {len(xs)*len(ys)} combinations, "
                  f"radius {radius}, stepsize {stepsize} - ", end='')

        if pool is not None:
            min_array = pool.map(self._loss_function, product(xs, ys))
        else:
            min_array = map(self._loss_function, product(xs, ys))

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

    def optimise(self, r_step_pairs=[(50, 10), (10, 2), (3, 0.5)],
                 centre_offset=[0, 0], pool=None, verbose=True):
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

        results = []
        for radius, stepsize in r_step_pairs:
            res = self._find_centre(
                radius, stepsize,
                centre_offset,
                verbose=verbose,
                pool=pool
            )

            centre_offset = res.centre

            results.append(res)

        #  Subtract the centre offset to move the modules in the correct
        #  way to shift the centre
        optimal_quad_positions = [
            tuple(qp - centre_offset)
            for qp
            in self.original_centre
        ]

        oqp = (
            "[",
            "".join([f"\n    {c}," for c in optimal_quad_positions]),
            "\n]"
        )
        print("Optimal quad positions: ", "".join(oqp))

        return res_tuple(optimal_quad_positions, centre_offset, results)
