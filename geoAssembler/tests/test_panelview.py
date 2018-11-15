import os
import sys

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QApplication
from PyQt5.QtTest import QTest

import unittest

from ..PanelView import Calibrate_Qt
from ..geometry import AGIPD_1MGeometry

app = QApplication(sys.argv)

class TestQt_Gui(unittest.TestCase):
    def setUp(self):
        '''Create the Gui'''
        quad_pos = [ (-540, 610), (-540, -15), (540, -143), (540, 482)]
        self.test_geo =  AGIPD_1MGeometry.from_quad_positions(quad_pos=quad_pos)
        data = np.zeros([16, 512, 128])
        self.calib = Calibrate_Qt(data, geofile=None)

    def test_defaults(self):
        '''Test the Gui in its default state'''
        self.assertEqual(self.calib.sel1.isChecked(), True)
        self.assertEqual(self.calib.sel2.isChecked(), False)
        self.assertEqual(len(self.calib.sel3.widgets.sp), 0)
        QTest.mouseClick(self.calib.btn3, Qt.LeftButton)
        self.assertEqual(len(self.calib.circles), 0)

    def test_load_geo(self):
        '''Test the correct loading fo geometry'''
        #Push the geometry load button
        QTest.mouseClick(self.calib.btn1, Qt.LeftButton)
        self.assertEqual(type(self.test_geo), type(self.calib.geom))

    def test_circles(self):
        '''Test adding circles'''
        #Draw image
        QTest.mouseClick(self.calib.btn1, Qt.LeftButton)
        QTest.mouseClick(self.calib.btn3, Qt.LeftButton)
        #Draw circle
        self.assertEqual(self.calib.fit_type , 'Circ.')
        QTest.mouseClick(self.calib.sel2, Qt.LeftButton)
        QTest.mouseClick(self.calib.sel2, Qt.LeftButton)
        self.calib.sel2.click()
        #Draw Set ellipse and draw
        QTest.mouseClick(self.calib.btn3, Qt.LeftButton)
        self.calib._update_bottom(self.calib.circles[1][0])
        self.assertEqual(len(self.calib.circles), 2)

    def test_circle_properties(self):
        '''Test changeing properties of the circles'''
        QTest.mouseClick(self.calib.btn1, Qt.LeftButton)
        self.assertEqual(len(self.calib.sel3.widgets.sp), 0)
        QTest.mouseClick(self.calib.btn3, Qt.LeftButton)
        for btn, length in ((self.calib.sel2, 2), (self.calib.sel1, 1)):
            btn.click()
            QTest.mouseClick(self.calib.btn3, Qt.LeftButton)
            self.assertEqual(len(self.calib.sel3.widgets.sp), length)

    def test_bottom_buttons(self):
        '''Test the circle selection buttons on the bottom'''
        QTest.mouseClick(self.calib.btn1, Qt.LeftButton)
        QTest.mouseClick(self.calib.btn3, Qt.LeftButton)
        self.assertEqual(len(self.calib.bottom_buttons), 1)
        self.assertEqual(self.calib.bottom_buttons[0].text(), 'Circ.')
        self.calib.sel2.click()
        QTest.mouseClick(self.calib.btn3, Qt.LeftButton)
        self.assertEqual(len(self.calib.bottom_buttons), 2)
        self.assertEqual(self.calib.bottom_buttons[1].text(), 'Ellip.')

    def test_save_geo(self):
        '''Test saving the geom file'''
        QTest.mouseClick(self.calib.btn1, Qt.LeftButton)
        self.assertEqual(self.calib.sel4.line.text(), 'sample.geom')
        self.calib.sel4.clear(linetxt='sample_unit.geom')
        QTest.mouseClick(self.calib.btn1, Qt.LeftButton)
        self.assertEqual(os.path.isfile('sample_unit.geom'), True)
        os.remove('sample_unit.geom')



