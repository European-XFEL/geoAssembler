from copy import deepcopy
from typing import Tuple, Union

import numpy as np
from extra_data import stack_detector_data
from extra_data.reader import DataCollection
from extra_geom.detectors import DetectorGeometryBase
from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
from pyFAI.detectors import Detector


class Integrator:
    """
    Object wrapping pyFAI and extra-geom geometries to provides a more
    convenient way of integrating 2d detector images.

    Creating the integrator requires a geometry, as well as the distance
    from the sample to the detector in mm. If unknown, 200mm seems to be
    a good 'normal' guess for AGIPD.

    Once created, use the `integrate2d` method to get a 2d unrolled view
    of the detector image. You can them sum over the image to get a 1d
    integration result.
    """

    def __init__(self, geom: DetectorGeometryBase,
                 sample_dist_m: Union[int, float], unit: str = "2th_deg"):
        self.unit = unit
        self.sample_dist_m = sample_dist_m

        fakedata = np.zeros(geom.expected_data_shape)
        fakeimage, centre_geom = geom.position_modules_fast(fakedata)
        self.size = fakeimage.shape

        self.centre = [centre_geom[0], centre_geom[1]]

        ai = AzimuthalIntegrator(
            dist=self.sample_dist_m,
            pixel1=geom.pixel_size,
            pixel2=geom.pixel_size,
            poni1=self.centre[0] * geom.pixel_size,
            poni2=self.centre[1] * geom.pixel_size,
        )
        self.ai = ai

        self.radius = ((self.size[0]/2)**2 + (self.size[1]/2)**2)**(1/2)
        self.azimuth_bins = self.radius * (self.size[0]/self.size[1])

    def integrate2d(self, frame: np.ndarray,
                    centre_offset: Tuple[float, float]=None):
        """
        Unroll the image - changes the axis from cartesian x/y to
        polar radius/azimuthal angle.

        A sum over the angle can be performed to get a result for
        the azimuthal integration.

        Returns a pyFAI `Integrate2dResult` object, check pyFAI
        docs for more information.

        Parameters
        ----------
        frame : np.ndarray
            A 2d detector image
        centre_offset : Tuple[float, float], optional
            Centre offset to apply before the integration, added to the original
            offset value, by default None

        Returns
        -------
        pyFAI.Integrate2dResult
            [description]
        """
        ai = deepcopy(self.ai)

        if centre_offset is not None:
            #  The centre offset is flipped here for... reasons. The correct
            #  order of x y for both the centre position and for the centre
            #  offset between pyFAI and extra-geom is not clear to me at all
            ai.setPyFAI(
                pixel1=self.ai.get_pixel1(), #  setPyFai loses pixel size info
                pixel2=self.ai.get_pixel2(), #  so re-set it here
                dist=self.sample_dist_m,
                poni1=(centre_offset[1] + self.centre[0]) * ai.pixel1,
                poni2=(centre_offset[0] + self.centre[1]) * ai.pixel2,
            )

        return ai.integrate2d(
            frame,
            self.radius,
            self.azimuth_bins,
            unit=self.unit,
            dummy=np.nan,
            method='cython'
        )
