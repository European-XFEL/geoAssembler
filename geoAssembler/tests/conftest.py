import os.path
import pytest
from unittest import mock

from extra_data import RunDirectory

from ..defaults import DefaultGeometryConfig as Defaults
from ..geometry import AGIPDGeometry

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
def mock_directory_dialog(mock_run):
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
def calib(gui_app, mock_run):
    """Create the calibration gui"""
    from geoAssembler.qt.app import QtMainWidget

    xd_run = RunDirectory(mock_run)
    geom = AGIPDGeometry.from_quad_positions(Defaults.fallback_quad_pos['AGIPD'])
    main_gui = QtMainWidget(gui_app, xd_run, mock_run, geom, det_type='AGIPD')
    yield main_gui
    main_gui.close()

@pytest.fixture()
def start_dialog(gui_app):
    from geoAssembler.qt.subwidgets import StartDialog
    dlg = StartDialog()
    yield dlg
    dlg.close()
