import os

from h5py import File
import numpy as np

from karabo_data.tests.mockdata.detectors import DetectorModule
from karabo_data.tests.mockdata import write_file


class AGIPDModule(DetectorModule):
        image_dims = (512, 128)
        detector_data_size = 5408
        firsttrain = 100
        chuncksize = 1
        ntrains = 1

def create_test_directory(path_dir):
    """Create a mock RunDirectory and add test-data to it."""
    test_file = os.path.join(os.path.dirname(__file__), 'data.npz')
    raw_data = np.load(test_file)['data']
    for modno in range(16):
        fname = 'CORR-R0273-AGIPD{:0>2}-S00000.h5'.format(modno)
        path = os.path.join(path_dir, fname)
        write_file(path, [AGIPDModule('SPB_DET_AGIPD1M-1/DET/{}CH0'.format(modno),
                                     frames_per_train=5)],
                        ntrains=1, chunksize=1)
        with File(os.path.join(path_dir, fname), 'a') as f:
            group = '/INSTRUMENT/SPB_DET_AGIPD1M-1/DET/{}CH0:xtdf/image/data'.format(modno)
            for i in range(len(f[group][:])):
                f[group][i] = raw_data[modno]


