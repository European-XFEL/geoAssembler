import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
from collections import namedtuple
import sys
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

class MyCircleOverlay(pg.EllipseROI):
    '''An Elliptic Region of interest'''
    def __init__(self, pos, size, **args):
         pg.ROI.__init__(self, pos, size, **args)
         self.aspectLocked = True
class MyRectOverlay(pg.RectROI):
    '''An Rectangular Region of interest'''
    def __init__(self, pos, size, sideScalers=True,**args):
         pg.ROI.__init__(self, pos, size, **args)
         self.aspectLocked = False

         self.addScaleHandle((-size/2,-size/2),
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
    def __init__(self, data, bounding_boxes=None, vmin=-1000, vmax=5000,
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


        if vmin is not None:
            data[data<vmin] = np.nan
        if vmax is not None:
            data[data>vmax] = np.nan

        if bounding_boxes is None:
            ## If no bounding boxes are given (default) define them by
            ## cutting the data into 4 even pieces

            x1, x2, x3 = 0, data.shape[-1]/2, data.shape[-1]
            y1, y2, y3 = 0, data.shape[-2]/2, data.shape[-2]
            self.bounding_boxes = {1:(x1, x2, y1, y2),
                                   2:(x2, x3, y1, y2),
                                   3:(x1, x2, y2, y3),
                                   4:(x2, x3, y2, y3)}
        else:
            self.bounding_boxes = bounding_boxes
        ## Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        self.app = QtGui.QApplication([])

        ## Create window with ImageView widget
        self.win = QtGui.QWindow()
        self.win.resize(800,800)
        #self.win.setWindowTitle('Select Points on a Circle')
        ## Create new image view
        self.imv = pg.ImageView()
        #self.win.setCentralWidget(self.imv)

        self.pen = QtGui.QPen(QtCore.Qt.red, 1)

        self.positions = pre_points ## Postions of the circle points
        self.fit_method = 'circle' ## The default fit-method to create the rings
        ## Circle Points by Quadrant
        P = namedtuple('Point', 'x y')
        self.P = P
        self.points = {1:P(x=[], y=[]), 2:P(x=[], y=[]),
                       3:P(x=[], y=[]), 4:P(x=[], y=[])}

        ## Display the data and assign each frame a time value from 1.0 to 3.0
        self.imv.setImage(data, xvals=np.linspace(1., 3., data.shape[0]))
        self.imv.getImageItem().mouseClickEvent = self.click


        ## Set a custom color map
        # Get the colormap
        cmap =  pg.ColorMap(*zip(*Gradients["grey"]["ticks"]))
        self.imv.setColorMap(cmap)
        self.exit = 0
        if init:
            self.init()
            pg.LabelItem(justify='right')

            self.w.setLayout(self.layout)
            self.w.show()
            self.app.exec_()

    def init(self):

        ## This is only for testing, display only all pre-defined points
        for r in self.positions:
            self.imv.getView().addItem(r)


        self.w = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()
        self.sel1 = QtGui.QRadioButton('Circle Fit')
        self.sel1.setChecked(True)
        self.sel1.toggled.connect(lambda:self.__set_method(self.sel1))
        self.sel2 = QtGui.QRadioButton('Ellipse Fit')
        self.sel2.toggled.connect(lambda:self.__set_method(self.sel2))


        ## Add widgets to the layout in their proper positions
        self.btn1 = QtGui.QPushButton('Apply Coordinates')
        self.btn2 = QtGui.QPushButton('Set Test-Coordinates')
        self.btn3 = QtGui.QPushButton('Clear Points')
        self.btn4 = QtGui.QPushButton('Cancel')



        self.btn4.clicked.connect(self.__destroy)
        self.btn2.clicked.connect(self.__preset)
        self.btn1.clicked.connect(self.__apply)
        self.btn3.clicked.connect(self.__clear)
        self.layout.addWidget(self.imv,  1, 0, 5, 4)  ## plot goes on right side, spanning 3 rows
        self.layout.addWidget(self.btn1, 5, 0, 1, 1)   ## button goes to the bottom
        self.layout.addWidget(self.btn2, 5, 1, 1, 1)   ## button goes to the bottom
        self.layout.addWidget(self.btn3, 5, 2, 1, 1)   ## button goes to the bottom
        self.layout.addWidget(self.btn4, 5, 3, 1, 1)   ## button goes to the bottom

        self.layout.addWidget(self.sel1, 0, 0, 1, 1)
        self.layout.addWidget(self.sel2, 0, 1, 1, 1)
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
        X = np.array([447, 383, 320, 255, 191, 153, 127, 114, 109, 507,
                     925, 942, 887, 862, 824, 734, 670, 605, 545,
                     88, 96, 111, 137, 158, 176, 192, 256, 320, 384, 447,
                     606, 670, 733, 862, 891, 926])

        Y = np.array([184, 203, 231, 277, 347, 412, 480, 528, 571, 179,
               489, 562, 404, 368, 323, 252, 222, 206, 200, 650,
               701, 747, 810, 843, 868, 889, 952, 988, 1015, 1029,
               1043, 1022, 991, 860, 804, 672])

        for i in range(len(X)):
            r = MyCrosshairOverlay(pos=(X[i],Y[i]), size=15,
                    pen=self.pen, movable=True, removable=True)

            self.positions.append(r)

    def __clear(self):
        for roi in self.positions:
            self.imv.getView().removeItem(roi)
        self.positions = []
    def __destroy(self):
        '''destroy the window'''

        self.app.closeAllWindows()
        self.exit = 1
        sys.exit(1)

    def __apply(self):
        '''get the coordinates of the selected points and destroy the window'''
        for roi in self.positions:
            x, y  = roi.pos()
            ## Get the quadrant of the position
            quad = self.get_quadrant(int(x), int(y))
            self.points[quad].x.append(int(x))
            self.points[quad].y.append(int(y))
        ## Test if there are enough points in each quadrant
        for quad, points in self.points.items():
            if len(points.x) < 4:
                import warnings
                warnings.warn('Each Quadrant should have more than 4 points',
                        UserWarning)
                return

        
        self.app.closeAllWindows()
        del self.layout, self.w, self.app #self.win
        QtCore.QCoreApplication.quit()

    def __preset(self):
        '''Apply a set of test_points to the region (testing purpose)'''
        self.__test_points()
        ## This is only for testing, display only all pre-defined points
        for r in self.positions:
            self.imv.getView().addItem(r)


    def get_quadrant(self, x, y):
        ''' Return the quadrant that a given set of coordinates lies in'''
        for quadrant, bbox in self.bounding_boxes.items():
            if x >= bbox[0] and x < bbox[1] and y >= bbox[2] and y < bbox[3]:
                return quadrant

    def click(self, event):
        '''Event for mouse-click into ImageRegion'''
        event.accept()
        # Get postion of mouse-click and display it
        pos = event.pos()
        x = int(pos.x())
        y = int(pos.y())
        r = MyCrosshairOverlay(pos=(x,y), size=15, pen=self.pen, movable=True,
                removable=True)
        self.imv.getView().addItem(r)
        self.positions.append(r)

class ResultView(PanelView):
    '''Display the result of the goemetric assemply'''
    def __init__(self, data, geo, shift=0, vmin=None, vmax=None, bounding_boxes=None):
        PanelView.__init__(self, data, vmin=vmin, vmax=vmax, init=False)
        self.w = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()
        self.shift = shift
        self.apply = True
        self.points = geo.old_points
        ## Add widgets to the layout in their proper positions
        self.btn2 = QtGui.QPushButton('Get Geometry')
        self.btn1 = QtGui.QPushButton('Back to Selection')
        self.btn3 = QtGui.QPushButton('Cancel')



        self.btn3.clicked.connect(self.__cancel)
        self.btn2.clicked.connect(self.__saveGeo)
        self.btn1.clicked.connect(self.__back)
        self.layout.addWidget(self.imv,  0, 0, 4, 3)  ## plot goes on right side, spanning 3 rows
        self.layout.addWidget(self.btn1, 4, 0, 1, 1)   ## button goes to the bottom
        self.layout.addWidget(self.btn2, 4, 1, 1, 1)   ## button goes to the bottom
        self.layout.addWidget(self.btn3, 4, 2, 1, 1)   ## button goes to the bottom

        pg.LabelItem(justify='right')
        self.positions = []
        self.w.setLayout(self.layout)
        self.plot_data(geo)
        self.w.show()
        self.app.exec_()


    def plot_data(self, geo):
        pen = QtGui.QPen(QtCore.Qt.blue, 1)
        for p in range(len(geo.points.x)):
            x, y = geo.points.x[p], geo.points.y[p]
            r = MyCircleOverlay(pos=(x,y), size=5,
                    pen=pen, movable=False, removable=False)
            self.imv.getView().addItem(r)

    def __saveGeo(self):
        '''This should crate a geometry file'''
        self.app.closeAllWindows()
        QtCore.QCoreApplication.quit()
        del self.layout, self.w #self.win


        return

    def __back(self):
        '''Set back stage'''
        self.apply = False
        self.app.closeAllWindows()
        for point in self.points.values():
            for i in range(len(point.x)):
                x, y = point.x[i], point.y[i]
                r = MyCrosshairOverlay(pos=(x,y), size=15,
                    pen=self.pen, movable=True, removable=True)
                self.positions.append(r)
        del self.layout, self.w #self.win

    def __cancel(self):
        sys.exit(0)

if __name__ == '__main__':

    #import sys
    data = np.load('image.npz')['image']
    data[data>=5000] = np.nan
    data[data<=-1000] = np.nan
    Viewer=PanelView(data)
    Point = namedtuple('Point', 'x y')
    #test_plot(data, Viewer.points)
    #shift(data, points = Viewer.points)
    #image_n = shift(data)
    #np.savez('data.npz', image=data)

