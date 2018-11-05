import numpy as np
import pandas as pd
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from collections import namedtuple
from itertools import product
from geometry import AGIPD_1MGeometry
import sys
from copy import deepcopy
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients


class RadiusSetter(QtWidgets.QFrame):
    def __init__(self, labels, button, fit_object):
        super(RadiusSetter, self).__init__()
        self.widgets = RadiusSetterWidget(labels, button, fit_object,
                                          parent=self)


class RadiusSetterWidget(QtWidgets.QHBoxLayout):
    def __init__(self, labels, button, fit_object,parent=None):
        super(RadiusSetterWidget, self).__init__(parent)
        self.sp = []
        self.fit_object = fit_object
        self.button = button
        for nn, label in enumerate(labels):
            self.label = QtGui.QLabel(label)
            self.addWidget(self.label)
            if len(label):
                size = int(self.fit_object.size()[nn])
                self.sp.append(QtGui.QSpinBox())
                self.sp[-1].setMinimum(0)
                self.sp[-1].setMaximum(10000)
                self.sp[-1].setValue(size)
                self.sp[-1].valueChanged.connect(self.valuechange)
                self.addWidget(self.sp[-1])
    def update(self, fit_object):
        self.fit_object = fit_object
        for nn in range(len(self.sp)):
            size = int(fit_object.size()[nn])
            self.sp[nn].setValue(size)

    def valuechange(self):
        size = []
        for nn, sp1 in enumerate(self.sp):
            size.append(self.sp[nn].value())

        if len(size) == 1:
            size += size
        pos = self.fit_object.pos()
        centre = pos[0] + self.fit_object.size()[0]//2, pos[1] + self.fit_object.size()[1]//2
        new_pos = centre[0] - size[0]//2, centre[1] - size[1]//2
        self.fit_object.setPos(new_pos)
        self.fit_object.setSize(size)


class FixedWidthLineEdit(QtWidgets.QFrame):
    def __init__(self, width, txt, preset):
        super(FixedWidthLineEdit, self).__init__()
        self.widget = FixedWidthLineEditWidget(width, txt, preset, self)
        self.button = self.widget.button
        self.line = self.widget.line
    @property
    def value(self):
        return self.line.text()

    def clear(self, buttontxt='Apply', linetxt=None, buttonfunc=lambda : None):
        self.line.setText(linetxt)
        #self.button.clicked.connect(buttonfunc)
        self.button.setText(buttontxt)


class FixedWidthLineEditWidget(QtWidgets.QHBoxLayout):
    def __init__(self, width, txt, preset, parent=None):
        super(FixedWidthLineEditWidget, self).__init__(parent)

        self.label = QtGui.QLabel(txt)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.addWidget(self.label)
        self.line = QtGui.QLineEdit(preset)
        self.line.setMaximumHeight(22)
        #self.label.setFixedWidth(width)
        self.addWidget(self.line)

        self.button=QtGui.QPushButton("Apply")
        self.addWidget(self.button)


class CustomGroupBox(QtGui.QGroupBox):
    GROUP_BOX_STYLE_SHEET = 'QGroupBox:title {' \
                            'border: 1px;' \
                            'subcontrol-origin: margin;' \
                            'subcontrol-position: top left;' \
                            'padding-left: 10px;' \
                            'padding-top: 10px;' \
                            'margin-top: 0.0em;}'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(self.GROUP_BOX_STYLE_SHEET)


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

    def __init__(self, data, geofile, vmin=-1000, vmax=5000):
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

        self.raw_data = np.clip(data, vmin, vmax)
        geofile = 'sample.geom'
        self.geofile = geofile
        size_xy = data.shape[-2:]
        self.canvas = np.full(( (size_xy[1]+29)*8 + 200,
                                2*size_xy[0]+8*3+29), np.nan)
        # If no bounding boxes are given (default) define them by
        # cutting the data into 4 even pieces

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        self.app = QtGui.QApplication([])
        # Create window with ImageView widget
        self.win = QtGui.QWindow()
        self.win.resize(800, 800)
        #self.win.setWindowTitle('Select Points on a Circle')
        # Create new image view
        self.imv = pg.ImageView()
        # self.win.setCentralWidget(self.imv)

        self.pen = QtGui.QPen(QtCore.Qt.red, 1)
        self.quad = 0  #  The selected quadrants
        self.fit_method = MyCircleOverlay  # The default fit-method to create the rings
        # Circle Points by Quadrant
        self.circles = {}
        self.fit_type = 'Circ.'
        self.bottom_buttons = {}
        self.bottom_select = None
        for action, keys in ((self.__move_left, ('left','H')),
                             (self.__move_up, ('up','K')),
                             (self.__move_down, ('down','J')),
                             (self.__move_right, ('right','L'))):
            for key in keys:
                shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+%s"%key),
                                           self.imv)
                shortcut.activated.connect(action)

        # Add widgets to the layout in their proper positions
        self.w = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()

        # circle/ellipse selection and input dialogs go to the top
        self.sel1 = QtGui.QRadioButton('Circle Helper')
        self.sel1.setChecked(True)
        self.sel1.clicked.connect(lambda: self.__set_method(self.sel1))
        self.layout.addWidget(self.sel1, 0, 0, 1, 1)
        self.sel2 = QtGui.QRadioButton('Ellipse Helper')
        self.sel2.clicked.connect(lambda: self.__set_method(self.sel2))
        self.layout.addWidget(self.sel2, 0, 1, 1, 1)
        self.sel3 = RadiusSetter(('',''), self.bottom_select, None)
        self.layout.addWidget(self.sel3, 0, 2, 1, 1)
        self.sel4 = FixedWidthLineEdit(254, 'Geometry File:', geofile)
        self.layout.addWidget(self.sel4, 0, 9, 1, 1)

        # plot goes into the centre on right side, spanning 10 rows
        self.layout.addWidget(self.imv,  1, 0, 4, 10)

        # buttons go to the bottom
        self.btn1 = self.sel4.button
        self.btn1.clicked.connect(self.__apply)
        self.btn2 = QtGui.QPushButton('Clear Helpers')
        self.btn2.clicked.connect(self.__clear)
        self.layout.addWidget(self.btn2, 4, 0, 1, 1)
        self.btn3 = QtGui.QPushButton('Draw Helper Objects')
        self.btn3.clicked.connect(self.__drawCircle)
        self.layout.addWidget(self.btn3, 4, 1, 1, 1)
        self.btn4 = QtGui.QPushButton('Cancel')
        self.btn4.clicked.connect(self.__destroy)
        self.layout.addWidget(self.btn4, 4, 2, 1, 1)



        pg.LabelItem(justify='right')

        self.w.setLayout(self.layout)
        self.w.show()
        self.app.exec_()

    def __apply(self):
        '''Read the geometry file and position all modules'''
        if self.quad == 0:
            try:
                self.geom = AGIPD_1MGeometry.from_crystfel_geom(self.sel4.value)
            except:
                quad_pos = [ (-540, 610), (-540, -15), (540, -143), (540, 482)]
                self.geom =  AGIPD_1MGeometry.from_quad_positions(quad_pos=quad_pos)

            data, self.centre = self.geom.position_all_modules(self.raw_data)
            self.canvas = np.full(np.array(data.shape) + 300, np.nan)

            d_size = np.array(self.canvas.shape) - np.array(data.shape)
            self.data, self.centre = self.geom.position_all_modules(self.raw_data,
                                                           canvas=self.canvas.shape)
            # Display the data and assign each frame a time value from 1.0 to 3.0
            self.imv.setImage(self.data,
                              xvals=np.linspace(1., 3., self.canvas.shape[0]))
            self.imv.getImageItem().mouseClickEvent = self.__click

            # Set a custom color map
            # Get the colormap
            cmap = pg.ColorMap(*zip(*Gradients["grey"]["ticks"]))
            self.imv.setColorMap(cmap)

            self.sel4.clear(buttontxt='Save', linetxt='sample.geom')
            self.quad = -1
        else:
            if not self.sel4.line.text():
                self.geofile = 'sample.geom'
            else:
                self.geofile = self.sel4.line.text()

            try:
                os.remove(self.geofile)
            except:
                pass
            self.geom.write_crystfel_geom(self.geofile)
            self.app.closeAllWindows()
            self.data, self.centre = self.geom.position_all_modules(self.raw_data)
            QtCore.QCoreApplication.quit()

    def __move(self, d):

        quad = self.quad
        if not quad > 0:
            return
        inc = 1
        dd = dict(u=(-inc, 0), d=(inc, 0), r=(0, inc), l=(0, -inc))[d]
        self.geom.move_quad(quad, np.array(dd))
        self.data, self.centre = self.geom.position_all_modules(self.raw_data,
                                                           canvas=self.canvas.shape)
        self.__click(quad)
        self.imv.getImageItem().updateImage(self.data)

    def __drawCircle(self):
        #y, x = int(self.centre[0]), int(self.centre[1])
        if self.quad == 0 or len(self.circles) > 9:
            return
        y, x = int(self.canvas.shape[0]//2), int(self.canvas.shape[1]//2)
        pen = QtGui.QPen(QtCore.Qt.red, 0.002)
        fit_helper = self.fit_method(pos=(x-x//4,y-x//4), size=x//2,
                removable=True, movable=False, pen=pen)

        fit_helper.handleSize = 5
        # Add top and right Handles
        fit_helper.addScaleHandle([0.5, 0], [0.5, 1])
        fit_helper.addScaleHandle([0.5, 1], [0.5, 0])
        self.imv.getView().addItem(fit_helper)
        sel1 = QtGui.QRadioButton(self.fit_type)
        sel1.setChecked(True)
        num = len(self.circles)
        [sel.setChecked(False) for sel in self.bottom_buttons.values()]
        self.bottom_buttons[num] = sel1
        if len(self.circles) == 0:
            self.bottom_select = sel1
        self.circles[num] = (fit_helper, self.fit_type)
        sel1.clicked.connect(lambda: self.__set_bottom(sel1, num, fit_helper))
        self.layout.addWidget(sel1, 5, num, 1, 1)

        labels = dict(c=('r:',''), e=('a:','b:'))[self.fit_type.lower()[0]]
        self.layout.removeWidget(self.sel3)
        self.sel3.close()
        self.sel3 = RadiusSetter(labels, self.bottom_select, fit_helper)
        self.layout.addWidget(self.sel3, 0, 2, 1, 1)
        self.layout.update()

    def __set_bottom(self, b, num, fit_helper):
        self.sel3.widgets.fit_method = self.circles[num][0]
        self.sel3.widgets.update(self.circles[num][0])
        self.sel3.widgets.button = b
        self.bottom_select.setChecked(False)
        self.bottom_select = b
        [sel.setChecked(False) for sel in self.bottom_buttons.values()]
        b.setChecked(True)


    def __set_method(self, b):
        if b.text().lower().startswith("circle"):
            if b.isChecked() == True:
                self.fit_method = MyCircleOverlay
                self.sel2.setChecked(False)
                self.fit_type = 'Circ.'

        if b.text().lower().startswith('ellipse'):
            if b.isChecked() == True:
                self.fit_method =  pg.EllipseROI
                self.sel1.setChecked(False)
                self.fit_type = 'Ellip.'

        self.sel2.setChecked(False)
        self.sel1.setChecked(False)
        b.setChecked(True)

    def __clear(self):
        for num in list(self.circles.keys()):
            self.imv.getView().removeItem(self.circles[num][0])
            del self.circles[num]

    def __destroy(self):
        '''destroy the window'''

        self.app.closeAllWindows()
        self.exit = 1
        sys.exit(1)

    def __get_quadrant(self, y, x):
        ''' Return the quadrant that a given set of coordinates lies in'''
        y1, y2, y3 = 0, self.data.shape[-1]/2, self.data.shape[-1]
        x1, x2, x3 = 0, self.data.shape[-2]/2, self.data.shape[-2]
        self.bounding_boxes = {1: (x2, x3, y1, y2),
                               2: (x1, x2, y1, y2),
                               3: (x1, x2, y2, y3),
                               4: (x2, x3, y2, y3)}
        self.lookup ={1:2, 3:4, 2:1, 4:3}
        for quadrant, bbox in self.bounding_boxes.items():
            if x >= bbox[0] and x < bbox[1] and y >= bbox[2] and y < bbox[3]:
                return quadrant

    def __click(self, event):
        '''Event for mouse-click into ImageRegion'''
        if self.quad == 0:
            return

        try:
            event.accept()
            # Get postion of mouse-click and display it
            pos = event.pos()
            x = int(pos.x())
            y = int(pos.y())
            delete = False
            quad  = self.__get_quadrant(x, y)
        except:
            quad = event
            delete = True
        if quad is None:
            self.imv.getView().removeItem(self.rect)
            self.rect = None
            self.quad = -1
            return

        if quad != self.quad or delete:
            try:
                self.imv.getView().removeItem(self.rect)
            except:
                pass
            self.quad = quad
            P, dx, dy = self.geom.get_quad_corners(quad,
                                                   np.array(self.data.shape,
                                                            dtype='i')//2 )
            pen = QtGui.QPen(QtCore.Qt.red, 0.002)
            self.rect = pg.RectROI(pos=P, size=(dx,dy), movable=False,
                                   removable=False, pen=pen, invertible=False)
            self.rect.handleSize = 0
            self.imv.getView().addItem(self.rect)
            [self.rect.removeHandle(handle) for handle in self.rect.getHandles()]

    def __move_up(self):
        self.__move('u')

    def __move_down(self):
        self.__move('d')

    def __move_right(self):
        self.__move('r')

    def __move_left(self):
        self.__move('l')


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
