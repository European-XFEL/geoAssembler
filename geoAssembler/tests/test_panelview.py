import os

import numpy as np
from pyqtgraph import QtCore
from PyQt5.QtTest import QTest

from ..geometry import AGIPDGeometry
from geoAssembler.qt.app import QtMainWidget


def test_defaults(mock_dialog, gui_app):
    """Test default settings."""
    # Click add circle btn when no image is selected, check for circles
    test_calib = QtMainWidget(gui_app, levels=[0, 1500])
    QTest.mouseClick(test_calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    assert len(test_calib.shapes) == 0

    # Check that we can select a run directory using the button
    assert test_calib.run_selector.bt_select_run_dir.isEnabled()
    with mock_dialog:
        QTest.mouseClick(test_calib.run_selector.bt_select_run_dir, QtCore.Qt.LeftButton)
    #Test if geometry was correctly applied
    assert isinstance(test_calib.geom_obj, AGIPDGeometry)
    #Test if the preset levels are correct
    levels = tuple(test_calib.imv.getImageItem().levels)
    assert levels[0] == 0
    assert levels[1] == 1500
    test_calib.close()

def test_preset(mock_dialog, calib):
    """Test pre defined settings."""
    with mock_dialog:
        QTest.mouseClick(calib.run_selector.bt_select_run_dir, QtCore.Qt.LeftButton)
    assert calib.run_selector.get_train_id() == 10000
    assert calib.run_selector._sel_method == None
    assert calib.run_selector._read_train == True

def test_load_geo(mock_dialog, mock_open, calib, geomfile):
    """Test the correct loading fo geometry."""
    with mock_dialog:
        QTest.mouseClick(calib.run_selector.bt_select_run_dir, QtCore.Qt.LeftButton)
    # Push the geometry load button and load a geo file via mock dialog
    QTest.mouseClick(calib.geom_selector.bt_load, QtCore.Qt.LeftButton)
    with mock_open:
        QTest.mouseClick(calib.geom_selector._geom_window.bt_load_geometry, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.geom_selector._geom_window.bt_ok, QtCore.Qt.LeftButton)
    # Check that the geo file was loaded
    assert calib.geom_file == os.path.abspath(geomfile)
    assert isinstance(calib.geom_obj, AGIPDGeometry)

def test_levels(mock_dialog, calib):
    """Test for behavior of default levels."""
    with mock_dialog:
        QTest.mouseClick(calib.run_selector.bt_select_run_dir, QtCore.Qt.LeftButton)
    parent = os.path.dirname(__file__)
    levels = tuple(calib.imv.getImageItem().levels.astype(np.float32))
    assert levels[0] == 0

def test_circles(mock_dialog, calib):
    """Test adding circles."""
    # Draw image
    with mock_dialog:
        QTest.mouseClick(calib.run_selector.bt_select_run_dir, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.fit_widget.bt_clear_shape, QtCore.Qt.LeftButton)
    # Press the add circle button twice, check for num of circles
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    assert len(calib.shapes) == 2

def test_circle_properties(mock_dialog, calib):
    """Test changeing properties of the circles."""
    with mock_dialog:
        QTest.mouseClick(calib.run_selector.bt_select_run_dir, QtCore.Qt.LeftButton)
    # Add a circle
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    # Set the size of the spinbox to 800 and check for circ. radius
    calib.fit_widget.sb_shape_size.setValue(800)
    assert calib.current_shape.size()[0] == 800
    # Add another circle, select the first one and check for size again
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    # calib.bottom_buttons[1].click()
    assert calib.current_shape.size()[0] == 690

def test_shapes_dropdown(mock_dialog, calib):
    """Test the circle selection buttons on the bottom."""
    with mock_dialog:
            QTest.mouseClick(calib.run_selector.bt_select_run_dir, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    assert calib.fit_widget.cb_shape_number.currentText().startswith('Circle')
    QTest.mouseClick(calib.fit_widget.bt_clear_shape, QtCore.Qt.LeftButton)
    assert calib.fit_widget.cb_shape_number.count() == 0

def test_save_geo(mock_dialog, mock_save, mock_warning, save_geo, calib):
    """Test saving the geom file."""
    with mock_dialog, mock_warning:
        QTest.mouseClick(calib.run_selector.bt_select_run_dir, QtCore.Qt.LeftButton)
    assert calib.geom_selector.bt_save.isEnabled()
    with mock_save, mock_warning:
        QTest.mouseClick(calib.geom_selector.bt_save, QtCore.Qt.LeftButton)
    geom = AGIPDGeometry.from_crystfel_geom(save_geo)
    assert isinstance(geom, AGIPDGeometry)
