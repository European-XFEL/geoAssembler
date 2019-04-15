import pytest


@pytest.fixture(scope='session')
def gui_app():
    import sys
    from pyqtgraph import QtGui
    app = QtGui.QApplication(sys.argv)
    yield app

@pytest.fixture(scope='module')
def mock_run():
    """Create a test run with predev ring data."""
    from .utils import create_test_directory
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as td:
         create_test_directory(td)
         yield td

@pytest.fixture()
def calib():
    """Create the calibration gui"""
    # Define a header for the cfel geometry file
    header="""
    ;
    clen = 5.5;
    adu_per_eV = 0.0075
    photon_energy = 10235;
    """
    from ..qt_viewer import CalibrateQt

    yield CalibrateQt(None, None, header=header)
