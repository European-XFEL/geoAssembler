import os
import sys

import numpy as np
from pyqtgraph import (QtCore, QtGui)
from PyQt5.QtTest import QTest

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
        data = np.zeros([16, 512, 128])
        dirname = os.path.dirname(__file__)
        self.calib = CalibrateQt(data, geofile=os.path.join(dirname, 'test.geom'))

    def test_defaults(self):
        """Test the Gui in its default state."""
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        self.assertEqual(len(self.calib.circles), 0)

    def test_load_geo(self):
        """Test the correct loading fo geometry."""
        #Push the geometry load button
        QTest.mouseClick(self.calib.load_geom_btn, QtCore.Qt.LeftButton)
        self.assertEqual(type(self.test_geo), type(self.calib.geom))

    def test_circles(self):
        """Test adding circles."""
        #Draw image
        QTest.mouseClick(self.calib.load_geom_btn, QtCore.Qt.LeftButton)
        QTest.mouseClick(self.calib.clear_btn, QtCore.Qt.LeftButton)
        #Draw circle
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        self.assertEqual(len(self.calib.circles), 1)

    def test_circle_properties(self):
        """Test changeing properties of the circles."""
        QTest.mouseClick(self.calib.load_geom_btn, QtCore.Qt.LeftButton)
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.calib.radius_setter.spin_box.value(), 695)
        self.calib.radius_setter.spin_box.setValue(800)
        self.assertEqual(self.calib.selected_circle.size()[0], 800)

    def test_bottom_buttons(self):
        """Test the circle selection buttons on the bottom."""
        QTest.mouseClick(self.calib.load_geom_btn, QtCore.Qt.LeftButton)
        QTest.mouseClick(self.calib.add_circ_btn, QtCore.Qt.LeftButton)
        self.assertEqual(len(self.calib.bottom_buttons), 1)
        self.assertEqual(self.calib.bottom_buttons[0].text(), 'Circ.')

    def test_save_geo(self):
        """Test saving the geom file."""
        QTest.mouseClick(self.calib.load_geom_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.calib.geom_selector.line.text(), 'sample.geom')
        self.calib.geom_selector.clear(linetxt='sample_unit.geom')
        QTest.mouseClick(self.calib.save_geom_btn, QtCore.Qt.LeftButton)
        self.assertEqual(os.path.isfile('sample_unit.geom'), True)
        os.remove('sample_unit.geom')
