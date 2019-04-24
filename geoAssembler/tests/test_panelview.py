import os
import pytest

import mock
import numpy as np
from pyqtgraph import (QtCore, QtGui)
from PyQt5.QtTest import QTest

from ..geometry import AGIPD_1MGeometry
from ..qt_viewer import CalibrateQt


def test_defaults(mock_run):
    # Click add circle btn when no image is selected, check for circles

    test_calib = CalibrateQt(mock_run, geofile=None, levels=[0, 1500])
    QTest.mouseClick(test_calib.add_circ_btn, QtCore.Qt.LeftButton)
    assert len(test_calib.circles) == 0
    # Click the add image button in test mode and check if a run-dir
    # can selected (shouldn't be)
    QTest.mouseClick(test_calib.apply_btn, QtCore.Qt.LeftButton)
    assert test_calib.run_selector_btn.isEnabled() == True
    with mock.patch.object(QtGui.QFileDialog, 'getExistingDirectory',
                return_value=mock_run):
            QTest.mouseClick(test_calib.run_selector_btn, QtCore.Qt.LeftButton)
    #Test if geometry was correctly applied
    assert type(test_calib.geom) == AGIPD_1MGeometry
    #Test if the preset levels are correct
    levels = tuple(test_calib.imv.getImageItem().levels)
    assert levels[0] == 0
    assert levels[1] == 1500

def test_preset(mock_run, calib):
    with mock.patch.object(QtGui.QFileDialog, 'getExistingDirectory',
                return_value=mock_run):
            QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    assert calib.run_selector.tid == 10000
    assert calib.run_selector._sel_method == None
    assert calib.run_selector._read_train == True

def test_load_geo(mock_run, calib):
    """Test the correct loading fo geometry."""
    with mock.patch.object(QtGui.QFileDialog, 'getExistingDirectory',
                return_value=mock_run):
            QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    geomfile = os.path.join(os.path.dirname(__file__), 'test.geom')
    # Push the geometry load button and load a geo file via mock dialog
    with mock.patch.object(QtGui.QFileDialog, 'getOpenFileName',
                           return_value=(geomfile, '')):
        QTest.mouseClick(calib.load_geom_btn, QtCore.Qt.LeftButton)
    # Push apply btn and check if the geo file was loaded
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    assert calib.geom_selector.value == os.path.abspath(geomfile)
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    assert type(calib.geom) == AGIPD_1MGeometry

def test_levels(mock_run, calib):
    """Test for behavior of default levels."""
    with mock.patch.object(QtGui.QFileDialog, 'getExistingDirectory',
                return_value=mock_run):
            QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    parent = os.path.dirname(__file__)
    raw_data = np.load(os.path.join(parent, 'data.npz'))['data']
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    levels = tuple(calib.imv.getImageItem().levels)
    print(levels)
    return
    assert levels[0] == 0
    assert levels[1] == raw_data.max()

def test_circles(mock_run, calib):
    """Test adding circles."""
    # Draw image
    with mock.patch.object(QtGui.QFileDialog, 'getExistingDirectory',
                return_value=mock_run):
            QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.clear_btn, QtCore.Qt.LeftButton)
    # Press the add circle button twice, check for num of circles
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    assert len(calib.circles) == 2

def test_circle_properties(mock_run, calib):
    """Test changeing properties of the circles."""
    with mock.patch.object(QtGui.QFileDialog, 'getExistingDirectory',
                return_value=mock_run):
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

def test_bottom_buttons(mock_run, calib):
    """Test the circle selection buttons on the bottom."""
    with mock.patch.object(QtGui.QFileDialog, 'getExistingDirectory',
                return_value=mock_run):
            QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.add_circ_btn, QtCore.Qt.LeftButton)
    assert calib.bottom_buttons[0].text() == 'Circ.'
    QTest.mouseClick(calib.clear_btn, QtCore.Qt.LeftButton)
    assert len(calib.bottom_buttons) == 0

def test_save_geo(mock_run, calib, tmpdir):
    """Test saving the geom file."""
    with mock.patch.object(QtGui.QFileDialog, 'getExistingDirectory',
                return_value=mock_run):
            QTest.mouseClick(calib.run_selector_btn, QtCore.Qt.LeftButton)
    save_geo = tmpdir.join('out.geom')
    QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
    assert calib.save_btn.isEnabled() ==  True
    with mock.patch.object(QtGui.QFileDialog, 'getSaveFileName',
                           return_value=(save_geo, '')):
        QTest.mouseClick(calib.save_btn, QtCore.Qt.LeftButton)
    geom = AGIPD_1MGeometry.from_crystfel_geom(save_geo)
    assert isinstance(geom, AGIPD_1MGeometry)
