import numpy as np
import pandas as pd
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from collections import namedtuple
from itertools import product
import sys
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients


class MyCircleOverlay(pg.EllipseROI):
    '''An Elliptic Region of interest'''

    def __init__(self, pos, size, **args):
        pg.ROI.__init__(self, pos, size, **args)
        self.aspectLocked = True


class MyRectOverlay(pg.RectROI):
    '''An Rectangular Region of interest'''

    def __init__(self, pos, size, sideScalers=True, **args):
        pg.ROI.__init__(self, pos, size, **args)
        self.aspectLocked = False

        self.addScaleHandle((-size/2, -size/2),
                            pos, lockAspect=False)


class MyCrosshairOverlay(pg.CrosshairROI):
    '''A cross-hair region of interest'''

    def __init__(self, pos, size, **kargs):
        self._shape = None
        pg.ROI.__init__(self, pos, size, **kargs)
        self.sigRegionChanged.connect(self.invalidate)
        self.aspectLocked = True


class PanelView(object):
    '''Class that plots detector data that has been roughly arranged'''

    def __init__(self, data, geometry, vmin=-1000, vmax=5000,
                 test=False, init=True, pre_points=[]):
        '''Parameters:
            data (2d-array)  : The 2d roughly assembled detector data that has
                               to be re-aligned

            Keywords:
            bounding_boxes (dict) : The x,y corners that define the quadrant
                                     postions in the data-array, if
                                     bounding_boxes is None (default), the
                                     quadrants are assumed to be the same as
                                     the ones that devide the data array into
                                     4 slices.
           vmin (int) : minimal value in the data array (default: -1000)
                        anything below this value will be masked
           vmax (int) : maximum value in the data array (default: 5000)
                        anything above this value will be masked
        '''
        #data = np.nanmean(data[:10,0],axis=0).astype(np.float)
        #data = np.nanmean(data[:10],axis=0).astype(np.float)
        #from matplotlib import pyplot as plt
        #plt.imshow(data)
        #plt.show()
        self.raw_data = data
        self.vmin = vmin
        self.vmax = vmax
        self.data, self.centre = geometry.position_all_modules(data)
        self.data = np.clip(self.data, vmin, vmax)
        self.margin = np.empty(np.array(self.data.shape)+100) * np.nan
        self.margin[50:-50,50:-50] = self.data
        # If no bounding boxes are given (default) define them by
        # cutting the data into 4 even pieces

        y1, y2, y3 = 0, self.margin.shape[-1]/2, self.margin.shape[-1]
        x1, x2, x3 = 0, self.margin.shape[-2]/2, self.margin.shape[-2]
        self.bounding_boxes = {1: (x1, x2, y2, y3),
                               2: (x1, x2, y1, y2),
                               3: (x2, x3, y1, y2),
                               4: (x2, x3, y2, y3)}
        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        self.app = QtGui.QApplication([])
        self.geom  = geometry
        # Create window with ImageView widget
        self.win = QtGui.QWindow()
        self.win.resize(800, 800)
        #self.win.setWindowTitle('Select Points on a Circle')
        # Create new image view
        self.imv = pg.ImageView()
        # self.win.setCentralWidget(self.imv)

        self.pen = QtGui.QPen(QtCore.Qt.red, 1)
        self.positions = -1  # Postions of the circle points
        self.fit_method = 'circle'  # The default fit-method to create the rings
        # Circle Points by Quadrant
        self.circles = []
        # Display the data and assign each frame a time value from 1.0 to 3.0
        self.imv.setImage(self.margin, xvals=np.linspace(1., 3., self.margin.shape[0]))
        self.imv.getImageItem().mouseClickEvent = self.click

        # Set a custom color map
        # Get the colormap
        cmap = pg.ColorMap(*zip(*Gradients["grey"]["ticks"]))
        self.imv.setColorMap(cmap)
        self.exit = 0
        if init:
            for action, keys in ((self.moveLeft, ('left','H')),
                                 (self.moveUp, ('up','K')),
                                 (self.moveDown, ('down','J')),
                                 (self.moveRight, ('right','L'))):
                for key in keys:
                    shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+%s"%key),
                                               self.imv)
                    shortcut.activated.connect(action)
            self.init()
            pg.LabelItem(justify='right')

            self.w.setLayout(self.layout)
            self.w.show()
            self.app.exec_()
    
        return action

            
    def init(self):

        self.w = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()
        self.sel1 = QtGui.QRadioButton('Circle Fit')
        self.sel1.setChecked(True)
        self.sel1.toggled.connect(lambda: self.__set_method(self.sel1))
        self.sel2 = QtGui.QRadioButton('Ellipse Fit')
        self.sel2.toggled.connect(lambda: self.__set_method(self.sel2))

        # Add widgets to the layout in their proper positions
        self.btn1 = QtGui.QPushButton('Apply Coordinates')
        self.btn2 = QtGui.QPushButton('Set Test-Coordinates')
        self.btn3 = QtGui.QPushButton('Clear Circles')
        self.btn4 = QtGui.QPushButton('Get helper circle')
        self.btn5 = QtGui.QPushButton('Cancel')
        
        self.btn5.clicked.connect(self.__destroy)
        self.btn4.clicked.connect(self.__drawCircle)
        self.btn2.clicked.connect(self.__preset)
        self.btn1.clicked.connect(self.__apply)
        self.btn3.clicked.connect(self.__clear)
        # plot goes on right side, spanning 3 rows
        self.layout.addWidget(self.imv,  1, 0, 5, 5)
        # button goes to the bottom
        self.layout.addWidget(self.btn1, 5, 0, 1, 1)
        # button goes to the bottom
        self.layout.addWidget(self.btn2, 5, 1, 1, 1)
        # button goes to the bottom
        self.layout.addWidget(self.btn3, 5, 2, 1, 1)
        # button goes to the bottom
        self.layout.addWidget(self.btn4, 5, 3, 1, 1)
        self.layout.addWidget(self.btn5, 5, 4, 1, 1)

        self.layout.addWidget(self.sel1, 0, 0, 1, 1)
        self.layout.addWidget(self.sel2, 0, 1, 1, 1)
    
    def moveDown(self):
        self.__move('d')
    def moveUp(self):
        self.__move('u')
    def moveRight(self):
        self.__move('r')
    def moveLeft(self):
        self.__move('l')

    def __move(self, d):

        quad = self.positions
        if not quad > 0:
            return
        inc = 2
        dd = dict(u=(-inc, 0), d=(inc, 0), r=(0, inc), l=(0, -inc))[d]
        self.geom.move_quad(quad, np.array(dd))
        data, self.centre = self.geom.position_all_modules(self.raw_data,
                canvas=self.margin.shape)
        self.data = np.clip(data, self.vmin, self.vmax)
        dx = (self.margin.shape[1] - self.data.shape[1]) // 2
        dy = (self.margin.shape[0] - self.data.shape[0]) // 2
        self.dr1 += dd[1]
        self.dr2 += dd[0]
        self.click(quad)
        self.imv.setImage(self.data, xvals=np.linspace(1., 3., self.data.shape[0]))

        



    def __drawCircle(self):
        y, x = int(self.centre[0]), int(self.centre[1])
        y, x = int(self.margin.shape[0]//2), int(self.margin.shape[1]//2)
        pen = QtGui.QPen(QtCore.Qt.blue, 0.002)
        
        circle = MyCircleOverlay(pos=(x-x//4,y-x//4), size=x//2,
                removable=True, movable=False, pen=pen)

        circle.handleSize = 5
        # Add top and right Handles
        circle.addScaleHandle([0.5, 0], [0.5, 1])
        circle.addScaleHandle([0, 0.5], [0.5, 0.5])
        circle.addScaleHandle([1, 0.5], [0.5, 0.5])
        circle.addScaleHandle([0.5, 1], [0.5, 0])
        #circle.addScaleHandle([0.5, 0.5], [0, 0])
        self.imv.getView().addItem(circle)
        self.circles.append(circle)


    def __set_method(self, b):

        if b.text().lower().startswith("circle"):
            if b.isChecked() == True:
                self.fit_method = 'circle'
                self.sel2.setChecked(False)

        if b.text().lower().startswith('ellipse'):
            if b.isChecked() == True:
                self.fit_method = 'ellipse'
                self.sel1.setChecked(False)

    def __test_points(self):
        '''Display pre-selected points on the circle for testing'''
        pp = pd.read_csv('points.csv')
        X = np.array(pp.X)
        Y = np.array(pp.Y)
        try:
            pp = pd.read_csv('points.csv')
            X = np.array(pp.X)
            Y = np.array(pp.Y)
        except :
            X = np.array([501, 448, 354, 316, 281, 260, 215, 196, 854, 830,
                          784, 721, 661, 846, 763, 206, 276, 373, 311, 188,
                          178, 830, 547, 579, 688, 708, 725, 743, 773, 818, 838])

            Y = np.array([271, 279, 320, 347, 380, 406, 497, 585, 568, 491, 413,
                          355, 320, 534, 390, 746, 844, 909, 873, 693, 646, 699,
                          960, 954, 908, 894, 880, 862, 827, 741, 658])

        for i in range(len(X)):
            r = MyCrosshairOverlay(pos=(X[i], Y[i]), size=15,
                                   pen=self.pen, movable=True, removable=True)

            self.positions.append(r)

    def __clear(self):
        for roi in self.circles:
            self.imv.getView().removeItem(roi)

    def __destroy(self):
        '''destroy the window'''

        self.app.closeAllWindows()
        self.exit = 1
        sys.exit(1)

    def __apply(self):
        '''get the coordinates of the selected points and destroy the window'''
        for roi in self.positions:
            x, y = roi.pos()
            # Get the quadrant of the position
            quad = self.get_quadrant(int(x), int(y))
            self.points[quad].x.append(int(x))
            self.points[quad].y.append(int(y))
        # Test if there are enough points in each quadrant
        for quad, points in self.points.items():
            if len(points.x) < 4:
                import warnings
                warnings.warn('Each Quadrant should have more than 4 points',
                              UserWarning)
                return

        self.app.closeAllWindows()
        del self.layout, self.w, self.app  # self.win
        QtCore.QCoreApplication.quit()

    def __preset(self):
        '''Apply a set of test_points to the region (testing purpose)'''
        self.__test_points()
        # This is only for testing, display only all pre-defined points

    def get_quadrant(self, x, y):
        ''' Return the quadrant that a given set of coordinates lies in'''
        for quadrant, bbox in self.bounding_boxes.items():
            if x >= bbox[0] and x < bbox[1] and y >= bbox[2] and y < bbox[3]:
                return quadrant

    def click(self, event):
        '''Event for mouse-click into ImageRegion'''
        try:
            event.accept()
            # Get postion of mouse-click and display it
            pos = event.pos()
            x = int(pos.x())
            y = int(pos.y())
            delete = False
        
            quad = self.get_quadrant(x, y)
        except:
            quad = event
            delete = True
        if quad != self.positions or delete:
            try:
                self.imv.getView().removeItem(self.rect)
            except:
                pass
            self.positions = quad

            dr1 = (self.margin.shape[1] - self.data.shape[1]) // 2
            dr2 = (self.margin.shape[0] - self.data.shape[0]) // 2
            if dr1 > 0:
                self.dr1 = dr1
            if dr2 > 0:
                self.dr2 = dr1
            print(self.dr1, self.dr2)
            P, dx, dy = self.geom.get_quad_corners(quad)
            pen = QtGui.QPen(QtCore.Qt.red, 0.002)
            self.rect = pg.RectROI(pos=(P[0]+min(self.dr1,50), P[1]+min(self.dr2,50)), size=(dx,dy),
                                   removable=False, pen=pen, invertible=False)
            self.rect.handleSize = 0
            self.imv.getView().addItem(self.rect)
            [self.rect.removeHandle(handle) for handle in self.rect.getHandles()]
        print(self.positions)


class ResultView(PanelView):
    '''Display the result of the goemetric assemply'''

    def __init__(self, data, geo, shift=0, vmin=None, vmax=None, bounding_boxes=None):
        PanelView.__init__(self, data, vmin=vmin, vmax=vmax, init=False)
        self.w = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()
        self.shift = shift
        self.apply = True
        # Add widgets to the layout in their proper positions
        self.btn2 = QtGui.QPushButton('Get Geometry')
        self.btn1 = QtGui.QPushButton('Back to Selection')
        self.btn3 = QtGui.QPushButton('Plot Fit-Object')
        self.btn4 = QtGui.QPushButton('Cancel')

        self.btn4.clicked.connect(self.__cancel)
        self.btn2.clicked.connect(self.__saveGeo)
        self.btn1.clicked.connect(self.__back)
        self.btn3.clicked.connect(self.plot_circle)
        # plot goes on right side, spanning 3 rows
        self.layout.addWidget(self.imv,  0, 0, 4, 4)
        # button goes to the bottom
        self.layout.addWidget(self.btn1, 4, 0, 1, 1)
        # button goes to the bottom
        self.layout.addWidget(self.btn2, 4, 1, 1, 1)
        # button goes to the bottom
        self.layout.addWidget(self.btn3, 4, 2, 1, 1)
        # button goes to the bottom
        self.layout.addWidget(self.btn4, 4, 3, 1, 1)

        pg.LabelItem(justify='right')
        self.positions = []
        self.w.setLayout(self.layout)
        self.geo = geo
        self.center, self.circle = None, None
        self.w.show()
        self.app.exec_()

    def plot_data(self):
        pen = QtGui.QPen(QtCore.Qt.blue, 1)
        for p in range(len(self.geo.points.x)):
            x, y = self.geo.points.x[p], self.geo.points.y[p]
            r = MyCircleOverlay(pos=(x, y), size=5,
                                pen=pen, movable=False, removable=False)
            self.imv.getView().addItem(r)

    def plot_circle(self):
        if self.center is None and self.circle is None:
            pen = QtGui.QPen(QtCore.Qt.red, 0.002)
            pen2 = QtGui.QPen(QtCore.Qt.red, 3)
            d = 2*self.geo.radius
            x, y = self.geo.center[0]-d/2, self.geo.center[1]-d/2
            self.circle = MyCircleOverlay(pos=(x, y), size=d, pen=pen,
                                          movable=False, removable=False)
            self.imv.getView().addItem(self.circle)
            self.center = MyCrosshairOverlay(pos=self.geo.center, size=8, pen=pen2,
                                             movable=False, removable=False)
            self.imv.getView().addItem(self.center)
        else:
            self.imv.getView().removeItem(self.center)
            self.imv.getView().removeItem(self.circle)
            self.center, self.circle = None, None

    def __saveGeo(self):
        '''This should crate a geometry file'''
        self.geo.get_corners(self.geo.center, self.shift)
        self.app.closeAllWindows()
        QtCore.QCoreApplication.quit()
        del self.layout, self.w  # self.win

        return

    def __back(self):
        '''Set back stage'''
        self.apply = False
        self.app.closeAllWindows()
        for point in self.points.values():
            for i in range(len(point.x)):
                x, y = point.x[i], point.y[i]
                r = MyCrosshairOverlay(pos=(x, y), size=15,
                                       pen=self.pen, movable=True, removable=True)
                self.positions.append(r)
        del self.layout, self.w  # self.win

    def __cancel(self):
        sys.exit(0)


if __name__ == '__main__':

    #import sys
    data = np.load('image.npz')['image']
    data[data >= 5000] = np.nan
    data[data <= -1000] = np.nan
    Viewer = PanelView(data)
    Point = namedtuple('Point', 'x y')
    #test_plot(data, Viewer.points)
    #shift(data, points = Viewer.points)
    #image_n = shift(data)
    #np.savez('data.npz', image=data)
