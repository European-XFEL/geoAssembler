#-*- coding: utf-8 -*-
"""
This example demonstrates the use of ImageView, which is a high-level widget for 
displaying and analyzing 2D and 3D data. ImageView provides:

  1. A zoomable region (ViewBox) for displaying the image
  2. A combination histogram and gradient editor (HistogramLUTItem) for
     controlling the visual appearance of the image
  3. A timeline for selecting the currently displayed frame (for 3D data only).
  4. Tools for very basic analysis of image data (see ROI and Norm buttons)

"""
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg

class MyCircleOverlay(pg.EllipseROI):
     def __init__(self, pos, size, **args):
         pg.ROI.__init__(self, pos, size, **args)
         self.aspectLocked = True

class MyCrosshairOverlay(pg.CrosshairROI):
    def __init__(self, pos=None, size=None, **kargs):
        self._shape = None
        pg.ROI.__init__(self, pos, size, **kargs)
        self.sigRegionChanged.connect(self.invalidate)
        self.aspectLocked = True




data = np.load('image.npz')['image']
vmin=-1000
vmax=5000
#def View(data, vmin=None, vmax=None):
if vmin is not None:
    data[data<vmin] = np.nan
if vmax is not None:
    data[data>vmax] = np.nan
    
# Interpret image data as row-major instead of col-major
pg.setConfigOptions(imageAxisOrder='row-major')

app = QtGui.QApplication([])

## Create window with ImageView widget
win = QtGui.QMainWindow()
#win = pg.GraphicsWindow()
win.resize(800,800)
imv = pg.ImageView()
win.setCentralWidget(imv)
win.show()
win.setWindowTitle('pyqtgraph example: ImageView')
pen = QtGui.QPen(QtCore.Qt.red, 0.1)

#plot = pg.plot()
#plot = win.addPlot()
posistions=[]
def click(event):
        event.accept()  
        pos = event.pos()
        x = int(pos.x())
        y = int(pos.y())
        r = MyCircleOverlay(pos=(x, y), size=10, pen=pen, movable=True,
                removable=True)
        imv.getView().addItem(r)
        posistions.append(r)
        #print(r)

        #plot.plot([int(pos.x())], [int(pos.y())], pen=(0,0,200), symbolBrush=(0,0,200),
        #          symbolPen='w', symbol='o', symbolSize=14)
        #print (int(pos.x()),int(pos.y()))



## Display the data and assign each frame a time value from 1.0 to 3.0
imv.setImage(data, xvals=np.linspace(1., 3., data.shape[0]))
imv.getImageItem().mouseClickEvent = click
## Set a custom color map
colors = [
    (0, 0, 0),
    (45, 5, 61),
    (84, 42, 55),
    (150, 87, 60),
    (208, 171, 141),
    (255, 255, 255)
]
cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
imv.setColorMap(cmap)
#cross hair

label = pg.LabelItem(justify='right')

#proxy = pg.SignalProxy(imv.scene().sigMouseMoved, rateLimit=60,
#                        slot=mouseMoved)

#win.scene().sigMouseClicked.connect(onClick)

## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
    for i in posistions:
        print(i.pos())

