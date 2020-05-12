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

        self.detector = Detector(
            pixel1=geom.pixel_size,
            pixel2=geom.pixel_size
        )

        ai = AzimuthalIntegrator(detector=self.detector)
        ai.setPyFAI(
            detector=self.detector,
            dist=self.sample_dist_m,
            poni1=self.centre[0] * ai.pixel1,
            poni2=self.centre[1] * ai.pixel2,
        )
        self.ai = ai

        self.radius = ((self.size[0]/2)**2 + (self.size[1]/2)**2)**(1/2)
        self.azimuth_bins = self.radius * (self.size[0]/self.size[1])

    def integrate2d(self, frame: np.ndarray, centre_offset=None):
        """
        Unroll the image - changes the axis from cartesian x/y to
        polar radius/azimuthal angle.

        A sum over the angle can be performed to get a result for
        the azimuthal integration.

        Returns a pyFAI `Integrate2dResult` object, check pyFAI
        docs for more information.
        """
        ai = deepcopy(self.ai)

        if centre_offset is not None:
            #  The centre offset is flipped here for... reasons. The correct
            #  order of x y for both the centre position and for the centre
            #  offset between pyFAI and extra-geom is not clear to me at all
            ai.setPyFAI(
                detector=self.detector,
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


def avg_frame(run: DataCollection, geom: DetectorGeometryBase,
              train_index: int, pulse_pattern=None,
              masking=True,) -> Tuple[np.ndarray, Tuple]:
    """
    Returns the average value of a train with some built-in masking  of known
    bad pixels and some corrections. Designed for use with AGIPD only.

    Requires an extra-data run, extra-geom geometry, and a train index,
    optionally can provide a slice as the pulse pattern if required.

    Returns a 2d image, and the centre of the image as given by the geometry.
    """
    run = run.select('*/DET/*', 'image.*')
    train_data = run.train_from_index(train_index)[1]

    if pulse_pattern is not None:
        if type(pulse_pattern) != slice:
            print("`pulse_pattern` should be a python slice object, e.g."
                  "`slice(10)` for first 10 pulses, or `slice(None, None, 2)` "
                  "for every-other pulse")

            raise NotImplementedError("`pulse_pattern must be a `slice` not "
                                      f"`{type(pulse_pattern)}`")
    else:
        pulse_pattern = slice(None, None)  # Equivalent to selecting all pulses

    stacked_image = stack_detector_data(train_data, 'image.data')[pulse_pattern]
    stacked_mask = stack_detector_data(train_data, 'image.mask')[pulse_pattern]

    if masking:
        #  Any non-zero masks are set to nan
        stacked_image[stacked_mask > 0] = np.nan

        #  Sub-zero and very large values set to nan
        stacked_image[stacked_image < 0] = np.nan
        stacked_image[stacked_image > 1e5] = np.nan

    stacked_mean = np.nanmean(stacked_image, axis=0)
    stacked_mean = np.clip(stacked_mean, 0, 1024)

    if masking:
        #  Mask off edges of asics
        #  TODO: Replace with extra-geom built-in asic edge masking
        #  once that is merged
        edge_mask = np.full((8, 16, 512//8, 128), np.nan)
        edge_mask[:, :, 1:-1, :] = 1
        edge_mask = edge_mask.reshape((16, 512, 128))

        stacked_mean = stacked_mean * edge_mask

    frame, centre = geom.position_modules_fast(stacked_mean)

    return frame, centre
