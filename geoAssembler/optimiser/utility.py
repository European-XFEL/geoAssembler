import numpy as np

from karabo_data import stack_detector_data
from pyFAI.detectors import Detector
from pyFAI.azimuthalIntegrator import AzimuthalIntegrator

from karabo_data.reader import DataCollection
from karabo_data.geometry2 import DetectorGeometryBase
from typing import Union, Tuple


class Integrator:
    """
    TODO: docstrings
    """

    def __init__(self, geom: DetectorGeometryBase,
                 sample_dist_mm: Union[int, float], unit: str = "2th_deg"):
        self.unit = unit
        self.sample_dist_mm = sample_dist_mm

        fakedata = np.zeros(geom.expected_data_shape)
        fakeimage, centre_geom = geom.position_modules_fast(fakedata)
        self.size = fakeimage.shape

        self.centre = [centre_geom[1], centre_geom[0]]

        # TODO: This works for square pixels, check what karabo_data
        # does for DSSC/non-square pixel sizes latercentre
        self.detector = Detector(
            pixel1=geom.pixel_size,
            pixel2=geom.pixel_size
        )

        ai = AzimuthalIntegrator(detector=self.detector)
        ai.setFit2D(self.sample_dist_mm, self.centre[0], self.centre[1])
        self.ai = ai

        self.raidus = ((self.size[0]/2)**2 + (self.size[1]/2)**2)**(1/2)
        self.azimuth_bins = self.raidus * (self.size[0]/self.size[1])

    def integrate2d(self, frame, centre_offset=None):
        if centre_offset is not None:
            self.ai.setFit2D(
                self.sample_dist_mm,
                centre_offset[0] + self.centre[0],
                centre_offset[1] + self.centre[1]
            )

        return self.ai.integrate2d(
            frame,
            self.raidus,
            self.azimuth_bins,
            unit=self.unit,
            dummy=np.nan,
            method='cython'
        )


def avg_frame(run: DataCollection, geom: DetectorGeometryBase,
              train_index: int, masking=True) -> Tuple[np.ndarray, Tuple]:
    run = run.select('*/DET/*', 'image.*')
    train_data = run.train_from_index(train_index)[1]

    stacked_image: np.array = stack_detector_data(train_data, 'image.data')
    stacked_mask: np.array = stack_detector_data(train_data, 'image.mask')

    if masking:
        #  Any non-zero masks are set to nan
        stacked_image[stacked_mask > 0] = np.nan

        #  Sub-zero and very large values set to nan
        stacked_image[stacked_image < 0] = np.nan
        stacked_image[stacked_image > 1e5] = np.nan

        #  Mask off bad part of ninth module
        stacked_image[:, 9, 192:512, :] = np.nan

    stacked_mean = np.nanmean(stacked_image, axis=0)
    stacked_mean = np.clip(stacked_mean, 0, 1024)

    if masking:
        #  Mask off edges of asics
        edge_mask = np.full((8, 16, 512//8, 128), np.nan)
        edge_mask[:, :, 1:-1, :] = 1
        edge_mask = edge_mask.reshape((16, 512, 128))

        stacked_mean = stacked_mean * edge_mask

    frame, centre = geom.position_modules_fast(stacked_mean)

    return frame, centre
