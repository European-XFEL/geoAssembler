import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
from collections import namedtuple


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
            test=False):
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
        self.win = QtGui.QMainWindow()
        self.win.setWindowTitle('Select Points on a Circle')
        self.win.resize(800,800)
        ## Create new image view
        self.imv = pg.ImageView()
        self.win.setCentralWidget(self.imv)

        self.pen = QtGui.QPen(QtCore.Qt.red, 0.2)

        self.posistions=[] ## Postions of the circle points

        ## Circle Points by Quadrant
        P = namedtuple('Point', 'x y')
        self.points = {1:P(x=[], y=[]), 2:P(x=[], y=[]),
                       3:P(x=[], y=[]), 4:P(x=[], y=[])}

        ## Display the data and assign each frame a time value from 1.0 to 3.0
        self.imv.setImage(data, xvals=np.linspace(1., 3., data.shape[0]))
        self.imv.getImageItem().mouseClickEvent = self.click
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
        self.imv.setColorMap(cmap)

        ## Add widgets to the layout in their proper positions
        self.btn = QtGui.QPushButton('Apply Coordinates')
        layout = QtGui.QGridLayout()
        w = QtGui.QWidget()
        w.setLayout(layout)
        self.btn.clicked.connect(self.destroy)
        layout.addWidget(self.imv, 0, 0, 3, 1)  ## plot goes on right side, spanning 3 rows
        layout.addWidget(self.btn, 3, 0)   ## button goes to the bottom
        pg.LabelItem(justify='right')

        w.show()
        if test:
            self.__test_points()
        self.app.exec_()


    def __test_points(self):
        '''Display pre-selected points on the circle for testing'''
            X = [378, 351, 301, 429, 474, 276, 249, 193, 167, 148, 117,
                  111, 103, 105, 920, 929, 935, 939, 894, 871, 825, 765,
                  725, 686, 634, 565, 85, 96, 131, 164, 201, 329, 293,
                  378, 432, 485, 593, 639, 696, 743, 770, 878, 863, 844,
                  824, 922, 921, 916, 910]

            Y = [198, 209, 236, 182, 176, 251, 272, 335, 371, 408, 492,
                 522, 572, 545, 485, 513, 539, 574, 416, 383, 326, 269,
                 245, 224, 209, 196, 665, 716, 804, 855, 901, 992, 972,
                 1010, 1022, 1029, 1041, 1028, 1004, 975, 954, 812, 843,
                 871, 896, 641, 668, 703, 731]

            for i in range(len(X)):
                r = MyCircleOverlay(pos=(X[i],Y[i]), size=15,
                        pen=self.pen, movable=True, removable=False)

                self.posistions.append(r)

    def destroy(self):
        '''Close all Windows and the coordinates of the selected points'''
        self.app.closeAllWindows()
        for roi in self.posistions:
            x, y  = roi.pos()
            ## Get the quadrant of the position
            quad = self.get_quadrant(int(x), int(y))
            self.points[quad].x.append(int(x))
            self.points[quad].y.append(int(y))

    def get_quadrant(self, x, y):
        ''' Return the quadrant that a given set of coordinates lies in'''
        for quadrant, bbox in self.bounding_boxes.items():
            if x >= bbox[0] and x < bbox[1] and y >= bbox[2] and y < bbox[3]:
                return quadrant

    def click(self, event):
        '''Event for mouse-click into ImageRegion'''
        event.accept()
        if self.test:
            ## This is only for testing, display only all pre-defined points
            for r in self.posistions:
                self.imv.getView().addItem(r)
        else:
            # Get postion of mouse-click and display it
            pos = event.pos()
            x = int(pos.x())
            y = int(pos.y())
            r = MyCircleOverlay(pos=(x,y), size=15, pen=self.pen, movable=True,
                    removable=False)
            self.imv.getView().addItem(r)
            self.posistions.append(r)

def shift(image, points=None, vmax=5000, vmin=-1000):
    if points is None:
        Point = namedtuple('Point', 'x y')
        P= {1: Point(x=[378, 351, 301, 429, 474, 276, 249, 193, 167, 148, 117, 111, 103, 105],
                     y=[198, 209, 236, 182, 176, 251, 272, 335, 371, 408, 492, 522, 572, 545]),
            2: Point(x=[920, 929, 935, 939, 894, 871, 825, 765, 725, 686, 634, 565],
                     y=[485, 513, 539, 574, 416, 383, 326, 269, 245, 224, 209, 196]),
            3: Point(x=[85, 96, 131, 164, 201, 329, 293, 378, 432, 485],
                     y=[665, 716, 804, 855, 901, 992, 972, 1010, 1022, 1029]),
            4: Point(x=[593, 639, 696, 743, 770, 878, 863, 844, 824, 922, 921, 916, 910],
                     y=[1041, 1028, 1004, 975, 954, 812, 843, 871, 896, 641, 668, 703, 731])}
    else:
        P = points
    center = []
    radius =[]


    for quad, pnt in P.items():
        x, y, c_x, c_y, r = fit_circle(pnt)
        center.append(np.array([c_x, c_y]))
        radius.append(r)

    from Assembler import Assemble, Test
    A = Assemble()
    data = Test()
    for n,k in enumerate(data.keys()):
         data[k]['image.data'] = np.load('image.npz')['image.%02i'%n]

    A.stack(data)
    radius = np.array(radius)
    center = np.array(center)
    shift = center[0] - center[1:,]
    X=A.df.Xoffset.values
    Y=A.df.Yoffset.values
    box = np.array([(1,1),(1,1),(1,1)])
    theta_fit = np.linspace(-np.pi, np.pi, 180)

    R=[radius[0]]
    C=[(center[0,0], center[0,1])]
    names=['Quad. 1']
    for i in range(len(shift)):
        quad=i+2
        print(quad, shift[i,0], shift[i,1])
        idx=np.array(A.df.loc[A.df.Quadrant == quad].index)
        X[idx] += int(shift[i,1].astype('i')*box[i,1])
        Y[idx] += int(shift[i,0].astype('i')*box[i,0])
        c = center[i+1]
        R.append(radius[i+1])
        C.append((c[0]+shift[i,0], c[1]+shift[i,1]))
        names.append('Quad. %i'%quad)

    C=np.array(C)
    R=np.array(R)
    A.df['Xoffset']=X
    A.df['Yoffset']=Y
    img = A.apply_geo(data)
    shape1 = np.array(img.shape)
    shape2 = np.array(image.shape)
    dx = np.fabs(shape1-shape2).max()
    dy = np.fabs(shape1-shape2).min()
    ds = dx - dy
    from matplotlib import pyplot as plt
    img[img>vmax] = np.nan
    img[img<vmin] = np.nan
    plt.imshow(img, vmin=-1000, vmax=5000)
    for i in range(4):
        print(R[i], names[i])
    x_fit2 = C[:,0].mean()+ds-13 + R.mean()*np.cos(theta_fit)
    y_fit2 = C[:,1].mean()+ds+3 + R.mean()*np.sin(theta_fit)
    plt.plot(x_fit2, y_fit2, linestyle='--', lw=1, label='Mean', color='r')
    plt.scatter(C[:,0]+ds-13,C[:,1]+ds+3, s= 20, color='r')
    plt.legend(loc=0)
    plt.show()
    return img
if __name__ == '__main__':

    #import sys
    data = np.load('image.npz')['image']
    data[data>=5000] = np.nan
    data[data<=-1000] = np.nan
    Viewer=PanelView(data, test=False)
    #print(Viewer.points)
    Point = namedtuple('Point', 'x y')
    #test_plot(data, Viewer.points)
    #shift(data, points = Viewer.points)
    #image_n = shift(data)
    np.savez('data.npz', image=data)

