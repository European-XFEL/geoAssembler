import os.path
import pytest
from unittest import mock

@pytest.fixture(scope='session', autouse=True)
def gui_app():
    import sys
    from pyqtgraph import QtGui
    app = QtGui.QApplication(sys.argv)
    yield app

@pytest.fixture(scope='session')
def mock_run():
    """Create a test run with predev ring data."""
    from .utils import create_test_directory
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as td:
         create_test_directory(td)
         yield td

@pytest.fixture(scope='module')
def mock_dialog(mock_run):
    """Create a mock dialog for opening a mock_run."""
    from pyqtgraph import QtGui as QG

    patch = mock.patch.object
    yield patch(QG.QFileDialog, 'getExistingDirectory', return_value=mock_run)

@pytest.fixture(scope='module')
def mock_save(save_geo):
    """Create a mock dialog for saving mock files."""
    from pyqtgraph import QtGui as QG

    patch = mock.patch.object
    yield patch(QG.QFileDialog, 'getSaveFileName', return_value=(save_geo, ''))

@pytest.fixture(scope='module')
def mock_warning():
    """Create a mock dialog for saving mock files."""
    from pyqtgraph import QtGui as QG

    patch = mock.patch.object
    yield patch(QG.QMessageBox, 'exec_', return_value=QG.QDialog.Accepted)

@pytest.fixture(scope='module')
def mock_open(geomfile):
    """Create a mock dialog for opening mock files."""
    from pyqtgraph import QtGui as QG

    patch = mock.patch.object
    yield patch(QG.QFileDialog, 'getOpenFileName', return_value=(geomfile, ''))

@pytest.fixture(scope='session')
def geomfile():
    """Define the geometry file."""
    return os.path.join(os.path.dirname(__file__), 'test.geom')

@pytest.fixture(scope='session')
def save_geo():
    from tempfile import NamedTemporaryFile as TF
    with TF(prefix='out_geom' , suffix='.geom') as save_geo:
        yield save_geo.name

@pytest.fixture()
def calib(gui_app):
    """Create the calibration gui"""
    from geoAssembler.qt.app import QtMainWidget

    main_gui = QtMainWidget(gui_app)
    yield main_gui
    main_gui.close()
