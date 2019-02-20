import os
import sys

#import numpy as np
from pyqtgraph import (QtCore, QtGui)
from PyQt5.QtTest import QTest

import mock
import unittest

from ..qt_viewer import CalibrateQt
from ..geometry import AGIPD_1MGeometry

app = QtGui.QApplication(sys.argv)

class TestQt_Gui(unittest.TestCase):
    """Define unit test cases for the gui."""
    def setUp(self):
        """Set up and create the gui."""
        quad_pos = [ (-540, 610), (-540, -15), (540, -143), (540, 482)]
        self.test_geo =  AGIPD_1MGeometry.from_quad_positions(quad_pos=quad_pos)
        #data = np.zeros([16, 512, 128])
        dirname = os.path.dirname(__file__)
        self.geomfile = os.path.join(dirname, 'test.geom')
        self.savefile = os.path.join(dirname, 'sample_unit.geom')
        self.calib = CalibrateQt(None,
                                 geofile=None,
                                 test=True)

    def test_defaults(self):
        """Test the Gui in its default state."""
        # Click add circle btn when no image is selected, check for circles
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        self.assertEqual(len(self.calib.circles), 0)
        # Click the add image button in test mode and check if a run-dir
        # can selected (shouldn't be)
        QTest.mouseClick(self.calib.apply_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.calib.run_selector_btn.isEnabled(), False)

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
        # Check for the default circle size
        self.assertEqual(self.calib.radius_setter.spin_box.value(), 690)
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
        os.remove(self.savefile)
