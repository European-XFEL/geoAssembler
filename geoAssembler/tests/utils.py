import os

from h5py import File
import numpy as np

from extra_data.tests.mockdata.detectors import AGIPDModule, LPDModule
from extra_data.tests.mockdata import write_file

# Define the keys and mock modules for each detector type
LOOKUP = {'AGIPD':(AGIPDModule, 'SPB_DET_AGIPD1M-1'),
          'LPD':(LPDModule, 'FXE_DET_LPD1M-1')}

def create_test_directory(path_dir, det='AGIPD'):
    """Create a mock RunDirectory and add test-data to it."""
    test_file = os.path.join(os.path.dirname(__file__),
                             'data_{}.npz'.format(det.lower()))
    raw_data = np.load(test_file)['data']
    DetModule, det_path = LOOKUP[det]
    for modno in range(raw_data.shape[0]):
        dset = '/INSTRUMENT/{}/DET/{}CH0:xtdf/image/data'.format(det_path,modno)
        fname = 'CORR-R0273-AGIPD{:0>2}-S00000.h5'.format(modno)
        path = os.path.join(path_dir, fname)
        write_file(path, [DetModule('{}/DET/{}CH0'.format(det_path, modno),
                                      raw=False, frames_per_train=5)],
                        ntrains=1, chunksize=1)
        with File(os.path.join(path_dir, fname), 'a') as f:
            f[dset][:] = raw_data[modno]


