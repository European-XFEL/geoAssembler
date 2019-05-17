import pyqtgraph as pg
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

class CircleROI(pg.EllipseROI):
    """Define a Elliptic ROI with a fixed aspect ratio (aka circle)."""

    def __init__(self, pos, size):
        """Create a circular region of interest.

        Parameters:
           pos (int) : centre of the circle
           size (int) : diameter of the circle
        """
        pen = QtGui.QPen(QtCore.Qt.red, 0.002)
        pg.ROI.__init__(self,
                        pos=pos,
                        size=size,
                        removable=True,
                        movable=False,
                        invertible=False,
                        pen=pen)
        self.aspectLocked = True
        self.handleSize = 0
        _ = [self.removeHandle(handle) for handle in self.getHandles()]

class SquareROI(pg.RectROI):
    """Define a rectangular ROI with a fixed aspect ratio (aka square)."""

    def __init__(self, pos, size):
        """Create a squared region of interest.

        Parameters:
           pos (int) : centre of the circle
           size (int) : diameter of the circle
        """
        pen = QtGui.QPen(QtCore.Qt.red, 0.002)
        pg.ROI.__init__(self,
                        pos=pos,
                        size=size,
                        removable=True,
                        movable=False,
                        invertible=False,
                        pen=pen)
        self.aspectLocked = True
        self.handleSize = 0
        _ = [self.removeHandle(handle) for handle in self.getHandles()]


