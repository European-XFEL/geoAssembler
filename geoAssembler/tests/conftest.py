import pytest
from tempfile import TemporaryDirectory
import sys

from pyqtgraph import QtGui

from .utils import create_test_directory
from ..qt_viewer import CalibrateQt

APP = QtGui.QApplication(sys.argv)

@pytest.fixture(scope='module')
def mock_run():
    """Create a test run with predev ring data."""
    with TemporaryDirectory() as td:
         create_test_directory(td)
         yield td

@pytest.fixture(scope='module')
def calib():
    """Create the calibration gui"""
    # Define a header for the cfel geometry file
    header="""
    ;
    clen = 5.5;
    adu_per_eV = 0.0075
    photon_energy = 10235;
    """

    yield CalibrateQt(None, None, header=header)
