import os

import numpy as np
from pyqtgraph import QtCore
from PyQt5.QtTest import QTest

from ..geometry import AGIPDGeometry
from ..widgets.pyqt import QtMainWidget


def test_defaults(mock_dialog, mock_run, gui_app):
    """Test default settings."""
    # Click add circle btn when no image is selected, check for circles
    test_calib = QtMainWidget(gui_app, mock_run, geofile=None, levels=[0, 1500])
    QTest.mouseClick(test_calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    assert len(test_calib.shapes) == 0
    # Click the add image button in test mode and check if a run-dir
    # can selected (shouldn't be)
    QTest.mouseClick(test_calib.apply_btn, QtCore.Qt.LeftButton)
    assert test_calib.run_selector_btn.isEnabled() == True
    with mock_dialog:
        QTest.mouseClick(test_calib.run_selector_btn, QtCore.Qt.LeftButton)
    #Test if geometry was correctly applied
    assert type(test_calib.geom) == AGIPDGeometry
    #Test if the preset levels are correct
    levels = tuple(test_calib.imv.getImageItem().levels)
    assert levels[0] == 0
    assert levels[1] == 1500

def test_preset(mock_dialog, calib):
    """Test pre defined settings."""
    with mock_dialog:
            QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    assert calib.run_selector.tid == 10000
    assert calib.run_selector._sel_method == None
    assert calib.run_selector._read_train == True

def test_load_geo(mock_dialog, mock_open, calib, geomfile):
    """Test the correct loading fo geometry."""
    with mock_dialog:
        QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    # Push the geometry load button and load a geo file via mock dialog
    with mock_open:
        QTest.mouseClick(calib.load_geom_btn, QtCore.Qt.LeftButton)
    # Push apply btn and check if the geo file was loaded
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    assert calib.geom_selector.value == os.path.abspath(geomfile)
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    assert type(calib.geom) == AGIPDGeometry

def test_levels(mock_dialog, calib):
    """Test for behavior of default levels."""
    with mock_dialog:
        QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    parent = os.path.dirname(__file__)
    raw_data = np.load(os.path.join(parent, 'data_agipd.npz'))['data']
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    levels = tuple(calib.imv.getImageItem().levels.astype(np.float32))
    assert levels[0] == 0

def test_circles(mock_dialog, calib):
    """Test adding circles."""
    # Draw image
    with mock_dialog:
        QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.clear_btn, QtCore.Qt.LeftButton)
    # Press the add circle button twice, check for num of circles
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    assert len(calib.circles) == 2

def test_circle_properties(mock_dialog, calib):
    """Test changeing properties of the circles."""
    with mock_dialog:
        QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    # Add a circle
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    # Set the size of the spinbox to 800 and check for circ. radius
    calib.radius_setter.spin_box.setValue(800)
    assert calib.selected_circle.size()[0] == 800
    # Add another circle, select the first one and check for size again
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    calib.bottom_buttons[1].click()
    assert calib.selected_circle.size()[0] == 690

def test_bottom_buttons(mock_dialog, calib):
    """Test the circle selection buttons on the bottom."""
    with mock_dialog:
            QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    assert calib.bottom_buttons[0].text() == 'Circ.'
    QTest.mouseClick(calib.clear_btn, QtCore.Qt.LeftButton)
    assert len(calib.bottom_buttons) == 0

def test_save_geo(mock_dialog, mock_save, mock_warning, save_geo, calib):
    """Test saving the geom file."""
    with mock_dialog, mock_warning:
        QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    assert calib.save_btn.isEnabled() ==  True
    with mock_save, mock_warning:
        QTest.mouseClick(calib.save_btn, QtCore.Qt.LeftButton)
    geom = AGIPDGeometry.from_crystfel_geom(save_geo)
    assert isinstance(geom, AGIPDGeometry)
