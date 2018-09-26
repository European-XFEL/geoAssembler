#!/usr/bin/env python
""" -*- coding: utf-8 -*-

 @Author: kirkwood
 @Date:   2018-09-11 12:30:25
 @Email: henry.kirkwood@xfel.eu

 --------------------------------

"""
import numpy as np
import matplotlib.pyplot as plt
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import sys

# this probably happens twice ( I think I call it in the other script)
app = QtGui.QApplication(sys.argv)

class liveImageView():
    """ very simple pyqt image display with updater"""
    def __init__(self):
        self.win = pg.GraphicsLayoutWidget()  
        self.win.resize(1800,600)
        self.vb = self.win.addViewBox(row=1, col=1)
        self.ImageItem = pg.ImageItem()
        self.pen = pg.mkPen('r', width=2 )
        # brush is what fills the points
        self.brush = pg.mkBrush(None)
        self.PlotItem = pg.ScatterPlotItem(pen=self.pen)
        # set marker size
        self.PlotItem.setSize(18)
        self.vb.addItem(self.ImageItem)
        self.vb.addItem(self.PlotItem)
        self.vb.setAspectLocked(True)
        self.PlotItem.setSymbol('o', )
        # attempt solution to catch ctrl+C
        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(lambda: None)
        self.viewtimer.start(500) # let timer run every 500 ms

    def updateIm(self,image, xydata = None, levels=None):
        self.ImageItem.setImage(image, levels=levels)
        if xydata is not None:
            x,y = xydata
            self.PlotItem.setData(x,y,pen=self.pen, symbol='o', brush=self.brush )
            
        QtGui.QApplication.processEvents()


class livePlotView():
    """ very simple pyqt image display with updater"""
    def __init__(self):
        self.win = pg.GraphicsLayoutWidget()
        self.vb = self.win.addViewBox(row=1, col=1)
        self.pen = pg.mkPen(None)
        self.PlotItem = pg.ScatterPlotItem(size=10,pen=self.pen)
        self.vb.addItem(self.PlotItem)
        self.vb.setAspectLocked(True)
        #self.PlotItem.setSymbol('o')
        #self.PlotItem.setPen(None)
        # attempt solution to catch ctrl+C
        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(lambda: None)
        self.viewtimer.start(500) # let timer run every 500 ms

    def updateIm(self,xydata):
        x,y = xydata
        self.PlotItem.setData(x,y)
        QtGui.QApplication.processEvents()


if __name__ == '__main__':

    imview = liveImageView()        
    imview.win.show()
    for n in range(100):
        imview.updateIm(np.random.random((512,512)))
    sys.exit(app.exec_())

