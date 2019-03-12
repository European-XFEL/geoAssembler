"""Unit tests for the Qt Gui."""
import os
import pytest
import sys
from tempfile import TemporaryDirectory

import mock
import numpy as np
from pyqtgraph import (QtCore, QtGui)
from PyQt5.QtTest import QTest
import unittest

from .utils import create_test_directory

from ..qt_viewer import CalibrateQt
from ..geometry import AGIPD_1MGeometry

app = QtGui.QApplication(sys.argv)

class TestQt_Gui(unittest.TestCase):
    """Define unit test cases for the gui."""
    def setUp(self):
        """Set up and create the gui."""
        quad_pos = [ (-540, 610), (-540, -15), (540, -143), (540, 482)]
        self.test_geo =  AGIPD_1MGeometry.from_quad_positions(quad_pos=quad_pos)
        self.tempdir = TemporaryDirectory()
        parent = os.path.dirname(__file__)
        self.raw_data = np.load(os.path.join(parent, 'data.npz'))['data'].astype(np.uint16)
        self.geomfile = os.path.join(parent, 'test.geom')
        self.savefile = os.path.join(self.tempdir.name, 'sample_unit.geom')
        create_test_directory(self.tempdir.name)
        self.calib = CalibrateQt(self.tempdir.name, geofile=None)

    def _load_runDir(self):
        with mock.patch.object(QtGui.QFileDialog, 'getExistingDirectory',
                return_value=self.tempdir.name):
            QTest.mouseClick(self.calib.run_selector_btn, QtCore.Qt.LeftButton)

    def tearDown(self):
        """Delete the created test objects."""
        self.tempdir.cleanup()

    @pytest.mark.order1
    def test_defaults(self):
        """Test the Gui in its default state."""
        # Click add circle btn when no image is selected, check for circles
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        self.assertEqual(len(self.calib.circles), 0)
        # Click the add image button in test mode and check if a run-dir
        # can selected (shouldn't be)
        QTest.mouseClick(self.calib.apply_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.calib.run_selector_btn.isEnabled(), True)

    @pytest.mark.order2
    def test_load_rundir(self):
        """Test loding a run directory."""
        self._load_runDir()
        self.assertEqual(self.calib.run_selector.tid, 10000)
        self.assertEqual(self.calib.run_selector._sel_method, None)
        self.assertEqual(self.calib.run_selector._read_train, True)

    def test_preset(self):
        """Test creating a calibratoin object with presets."""
        #Create another instance with fixed levels, rundir and geomfile
        calib = CalibrateQt(self.tempdir.name, self.geomfile,
                levels=[0, 1500])
        # Check against the expected properties for those presets
        QTest.mouseClick(calib.apply_btn, QtCore.Qt.LeftButton)
        self.assertEqual(type(self.test_geo), type(calib.geom))
        levels = tuple(calib.imv.getImageItem().levels)
        self.assertEqual(levels[0], 0)
        self.assertEqual(levels[1], 1500)

    def test_levels(self):
        """Test for behavior of default levels."""
        QTest.mouseClick(self.calib.apply_btn, QtCore.Qt.LeftButton)
        levels = tuple(self.calib.imv.getImageItem().levels)
        self.assertEqual(levels[0], 0)
        self.assertEqual(levels[1], self.raw_data.max())

    def test_load_geo(self):
        """Test the correct loading fo geometry."""
        # Push the geometry load button and load a geo file via mock dialog
        with mock.patch.object(QtGui.QFileDialog, 'getOpenFileName',
                               return_value=(self.geomfile, '')):
            QTest.mouseClick(self.calib.load_geom_btn, QtCore.Qt.LeftButton)
        # Push apply btn and check if the geo file was loaded
        QTest.mouseClick(self.calib.apply_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.calib.geom_selector.value,
                         os.path.abspath(self.geomfile))
        QTest.mouseClick(self.calib.apply_btn, QtCore.Qt.LeftButton)
        self.assertEqual(type(self.test_geo), type(self.calib.geom))

    def test_circles(self):
        """Test adding circles."""
        # Draw image
        QTest.mouseClick(self.calib.apply_btn, QtCore.Qt.LeftButton)
        QTest.mouseClick(self.calib.clear_btn, QtCore.Qt.LeftButton)
        # Press the add circle button twice, check for num of circles
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        self.assertEqual(len(self.calib.circles), 2)

    def test_circle_properties(self):
        """Test changeing properties of the circles."""
        QTest.mouseClick(self.calib.apply_btn, QtCore.Qt.LeftButton)
        # Add a circle
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        # Set the size of the spinbox to 800 and check for circ. radius
        self.calib.radius_setter.spin_box.setValue(800)
        self.assertEqual(self.calib.selected_circle.size()[0], 800)
        # Add another circle, select the first one and check for size again
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        self.calib.bottom_buttons[0].click()
        self.assertEqual(self.calib.selected_circle.size()[0], 800)

    def test_bottom_buttons(self):
        """Test the circle selection buttons on the bottom."""
        QTest.mouseClick(self.calib.apply_btn, QtCore.Qt.LeftButton)
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        self.assertEqual(len(self.calib.bottom_buttons), 2)
        self.assertEqual(self.calib.bottom_buttons[0].text(), 'Circ.')
        QTest.mouseClick(self.calib.clear_btn, QtCore.Qt.LeftButton)
        self.assertEqual(len(self.calib.bottom_buttons), 0)

    def test_save_geo(self):
        """Test saving the geom file."""
        QTest.mouseClick(self.calib.apply_btn, QtCore.Qt.LeftButton)
        with mock.patch.object(QtGui.QFileDialog, 'getSaveFileName',
                               return_value=(self.savefile, '')):
            QTest.mouseClick(self.calib.save_btn, QtCore.Qt.LeftButton)
            self.assertEqual(self.calib.save_btn.isEnabled(), True)
        self.assertEqual(os.path.isfile(self.savefile), True)
