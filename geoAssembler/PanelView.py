import os
import logging

from ipywidgets import widgets, Layout
from IPython.display import display
from matplotlib import pyplot as plt, cm
import matplotlib.patches as patches
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

from .geometry import AGIPD_1MGeometry

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(os.path.basename(__file__))


class RadiusSetter(QtWidgets.QFrame):
    """Add nested widgets to set radii"""

    def __init__(self, labels, button, fit_object):
        super(RadiusSetter, self).__init__()
        self.widgets = RadiusSetterWidget(labels, button, fit_object,
                                          parent=self)


class RadiusSetterWidget(QtWidgets.QHBoxLayout):
    """Add widgets to the nested Radius widget"""

    def __init__(self, labels, button, fit_object, parent=None):
        super(RadiusSetterWidget, self).__init__(parent)
        self.sp = []
        self.fit_object = fit_object
        self.button = button
        for nn, label in enumerate(labels):
            self.addWidget(QtGui.QLabel(label))
            if len(label):
                size = int(self.fit_object.size()[nn])
                spin_box = QtGui.QSpinBox()
                spin_box.setMinimum(0)
                spin_box.setMaximum(10000)
                spin_box.setValue(size)
                spin_box.valueChanged.connect(self.valuechange)
                self.addWidget(spin_box)
                self.sp.append(spin_box)

    def update(self, fit_object):
        """Recycle the widget"""
        self.fit_object = fit_object
        self.sp = []
        for nn in range(len(self.sp)):
            size = int(fit_object.size()[nn])
            spin_box = QtGui.QSpinBox()
            spin_box.setMinimum(0)
            spin_box.setMaximum(10000)
            spin_box.setValue(size)
            spin_box.valueChanged.connect(self.valuechange)
            self.sp.append(spin_box)

    def valuechange(self):
        """Update the size of the roi form button-click"""
        size = []
        # Circles have only radii and Ellipses major and minor axis
        for nn, sp1 in enumerate(self.sp):
            size.append(self.sp[nn].value())

        if len(size) == 1:
            size += size
        pos = self.fit_object.pos()
        centre = pos[0] + self.fit_object.size()[0]//2, pos[1] + \
            self.fit_object.size()[1]//2
        new_pos = centre[0] - size[0]//2, centre[1] - size[1]//2
        self.fit_object.setPos(new_pos)
        self.fit_object.setSize(size)

    def set_val(self, fit_object):
        """Update the value of the spin_box from roi-drag"""
        for n, spin_box in enumerate(self.sp):
            spin_box.setValue(int(fit_object.size()[n]))
        fit_object.setPen(QtGui.QPen(QtCore.Qt.red, 0.002))


class FixedWidthLineEdit(QtWidgets.QFrame):
    """Create nested Widgets"""

    def __init__(self, width, txt, preset):
        super(FixedWidthLineEdit, self).__init__()
        self.widget = FixedWidthLineEditWidget(width, txt, preset, self)
        self.button = self.widget.button
        self.line = self.widget.line

    @property
    def value(self):
        return self.line.text()

    def clear(self, buttontxt='Apply', linetxt=None,
              tooltip='Assemble Data', buttonfunc=lambda: None):
        self.line.setText(linetxt)
        self.button.setText(buttontxt)
        self.button.setToolTip(tooltip)


class FixedWidthLineEditWidget(QtWidgets.QHBoxLayout):
    """Add stuff to the nested widget"""

    def __init__(self, width, txt, preset, parent=None):
        super(FixedWidthLineEditWidget, self).__init__(parent)
        self.label = QtGui.QLabel(txt)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.addWidget(self.label)
        self.line = QtGui.QLineEdit(preset)
        self.line.setMaximumHeight(22)
        self.addWidget(self.line)
        self.button = QtGui.QPushButton("Apply")
        self.button.setToolTip('Assemble Data')
        self.addWidget(self.button)


class MyCircleOverlay(pg.EllipseROI):
    """An Elliptic Region of interest"""

    def __init__(self, pos, size, **args):
        pg.ROI.__init__(self, pos, size, **args)
        self.aspectLocked = True


class MyRectOverlay(pg.RectROI):
    """An Rectangular Region of interest"""

    def __init__(self, pos, size, sideScalers=True, **args):
        pg.ROI.__init__(self, pos, size, **args)
        self.aspectLocked = False

        self.addScaleHandle((-size/2, -size/2),
                            pos, lockAspect=False)


class MyCrosshairOverlay(pg.CrosshairROI):
    """A cross-hair region of interest"""

    def __init__(self, pos, size, **kargs):
        self._shape = None
        pg.ROI.__init__(self, pos, size, **kargs)
        self.sigRegionChanged.connect(self.invalidate)
        self.aspectLocked = True


class Calibrate_Qt(object):
    """Class that plots detector data to bee roughly arranged (PyQt-Version)"""

    def __init__(self, raw_data, geofile=None, vmin=-1000, vmax=5000, **kwargs):
        """Parameters:
            data (2d-array)  : File name of the geometry file, if none is given
                               (default) the image will be assembled with 29 Px
                               gaps between all modules.

            Keywords:
             geom (str/AGIPD_1MGeometry) :  The geometry file can either be
                                            an AGIPD_1MGeometry object or
                                            the filename to the geometry file
                                            in CFEL fromat
             vmin (int) : minimal value in the data array (default: -1000)
                          anything below this value will be clipped
             vmax (int) : maximum value in the data array (default: 5000)
                          anything above this value will be clipped
        """
        assert raw_data.shape == (
            16, 512, 128)  # Only one image should be passed
        self.raw_data = np.clip(raw_data, vmin, vmax)
        self.geofile = geofile

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        # Create window with ImageView widget
        self.win = QtGui.QWindow()
        self.win.resize(800, 800)
        # Create new image view
        self.imv = pg.ImageView()

        self.pen = QtGui.QPen(QtCore.Qt.red, 1)
        self.quad = 0  # The selected quadrants
        self.fit_method = MyCircleOverlay  # The default fit-method to create the rings
        # Circle Points by Quadrant
        self.circles = {}
        self.fit_type = 'Circ.'
        self.bottom_buttons = {}
        self.bottom_select = None
        for action, keys in ((self._move_left, ('left', 'H')),
                             (self._move_up, ('up', 'K')),
                             (self._move_down, ('down', 'J')),
                             (self._move_right, ('right', 'L'))):
            for key in keys:
                shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+%s" % key),
                                           self.imv)
                shortcut.activated.connect(action)

        # Add widgets to the layout in their proper positions
        self.w = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()

        # circle/ellipse selection and input dialogs go to the top
        self.sel1 = QtGui.QRadioButton('Circle Helper')
        self.sel1.setChecked(True)
        self.sel1.clicked.connect(lambda: self._set_method(self.sel1))
        self.layout.addWidget(self.sel1, 0, 0, 1, 1)
        self.sel2 = QtGui.QRadioButton('Ellipse Helper')
        self.sel2.clicked.connect(lambda: self._set_method(self.sel2))
        self.layout.addWidget(self.sel2, 0, 1, 1, 1)
        self.sel3 = RadiusSetter(('', ''), self.bottom_select, None)
        self.layout.addWidget(self.sel3, 0, 2, 1, 1)
        self.sel4 = FixedWidthLineEdit(254, 'Geometry File:', geofile)
        self.layout.addWidget(self.sel4, 0, 9, 1, 1)

        # plot goes into the centre on right side, spanning 10 rows
        self.layout.addWidget(self.imv,  1, 0, 10, 10)

        # buttons go to the bottom
        self.btn1 = self.sel4.button
        self.btn1.clicked.connect(self._apply)
        self.btn2 = QtGui.QPushButton('Clear Helpers')
        self.btn2.setToolTip('Remove All Buttons')
        self.btn2.clicked.connect(self._clear)
        self.layout.addWidget(self.btn2, 11, 0, 1, 1)
        self.btn3 = QtGui.QPushButton('Draw Helper Objects')
        self.btn3.setToolTip('Add Circles to the Image')
        self.btn3.clicked.connect(self._drawCircle)
        self.layout.addWidget(self.btn3, 11, 1, 1, 1)
        self.btn4 = QtGui.QPushButton('Cancel')
        self.btn4.clicked.connect(self._destroy)
        self.layout.addWidget(self.btn4, 11, 2, 1, 1)
        self.info = QtGui.QLabel(
            'Click on Quadrant to select; CTRL+arrow-keys to move')
        self.info.setToolTip('Click into the Image to select a Quadrant')
        self.layout.addWidget(self.info, 11, 3, 1, 8)

        pg.LabelItem(justify='right')
        self.w.setLayout(self.layout)

    def _apply(self):
        """Read the geometry file and position all modules"""
        if self.quad == 0:
            log.info(' Starting to assemble ... ')
            try:
                self.geom = AGIPD_1MGeometry.from_crystfel_geom(
                    self.sel4.value)
            except:
                # Fallback to evenly align quadrant positions
                quad_pos = [(-540, 610), (-540, -15), (540, -143), (540, 482)]
                self.geom = AGIPD_1MGeometry.from_quad_positions(
                    quad_pos=quad_pos)

            data, self.centre = self.geom.position_all_modules(self.raw_data)
            self.canvas = np.full(np.array(data.shape) + 300, np.nan)

            self.data, self.centre = self.geom.position_all_modules(self.raw_data,
                                                                    canvas=self.canvas.shape)
            # Display the data and assign each frame a time value from 1.0 to 3.0
            self.imv.setImage(self.data,
                              xvals=np.linspace(1., 3., self.canvas.shape[0]))
            self.imv.getImageItem().mouseClickEvent = self._click

            # Set a custom color map
            # Get the colormap
            cmap = pg.ColorMap(*zip(*Gradients["grey"]["ticks"]))
            self.imv.setColorMap(cmap)

            self.sel4.clear(buttontxt='Save', linetxt='sample.geom',
                            tooltip='Save Geometry File')
            self.quad = -1
        else:
            log.info(' Saving output to %s' % self.geofile)
            if not self.sel4.line.text():
                self.geofile = 'sample.geom'
            else:
                self.geofile = self.sel4.line.text()

            try:
                os.remove(self.geofile)
            except:
                pass
            self.data, self.centre = self.geom.position_all_modules(
                self.raw_data)
            if self.geofile.split('.')[-1].lower() == 'geom':
                self.geom.write_crystfel_geom(self.geofile)
            elif 'tif' in self.geofil.split('.')[-1]:
                from PIL import Image

                data = np.ma.masked_invalid(self.data)
                im = Image.fromarray(
                    np.ma.masked_outside(data, self.vmin, self.vmax).filled(0))

                im.save(self.geofile)
            QtCore.QCoreApplication.quit()

    def _move(self, d):
        """Move the quadrant"""
        quad = self.quad
        if not quad > 0:
            return
        inc = 1
        dd = dict(u=(-inc, 0), d=(inc, 0), r=(0, inc), l=(0, -inc))[d]
        self.geom.move_quad(quad, np.array(dd))
        self.data, self.centre = self.geom.position_all_modules(self.raw_data,
                                                                canvas=self.canvas.shape)
        self._click(quad)
        self.imv.getImageItem().updateImage(self.data)

    def _drawCircle(self):
        """add a fit object to the image"""
        if self.quad == 0 or len(self.circles) > 9:
            return
        y, x = int(self.canvas.shape[0]//2), int(self.canvas.shape[1]//2)
        pen = QtGui.QPen(QtCore.Qt.red, 0.002)
        fit_helper = self.fit_method(pos=(x-x//2, y-x//2), size=x//1,
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
        self.circles[num] = (fit_helper, self.fit_method)
        self.bottom_select = sel1
        sel1.clicked.connect(lambda: self._set_bottom(sel1, num, fit_helper))
        self._update_bottom(fit_helper)
        self.layout.addWidget(sel1, 12, num, 1, 1)
        fit_helper.sigRegionChangeFinished.connect(
            lambda: self.sel3.widgets.set_val(fit_helper))
        # Set all previous circle colors to blue
        for n, (rio, _) in self.circles.items():
            if n != num:
                rio.setPen(QtGui.QPen(QtCore.Qt.blue, 0.002))

    def _set_bottom(self, b, num, fit_helper):
        """add a selection button for a fit object to the bottom region"""
        self.sel3.widgets.fit_method = self.circles[num][0]
        self.sel3.widgets.update(self.circles[num][0])
        self.sel3.widgets.button = b
        self.bottom_select.setChecked(False)
        self.bottom_select = b
        [sel.setChecked(False) for sel in self.bottom_buttons.values()]
        b.setChecked(True)
        # Set all unselected circles to blue
        for n, (rio, _) in self.circles.items():
            if n != num:
                rio.setPen(QtGui.QPen(QtCore.Qt.blue, 0.002))
            else:
                rio.setPen(QtGui.QPen(QtCore.Qt.red, 0.002))
        self.fit_method = self.circles[num][-1]
        self._update_bottom(fit_helper)

    def _del_bottom(self):
        """del. selected fit method from the bottom region"""
        if not len(self.circles):
            return
        btn_nums = list(self.bottom_buttons.keys())
        for num in btn_nums:
            if self.bottom_buttons[num].isChecked():
                self.bottom_buttons[num].close()
                break

        nn = num - 1
        self.bottom_buttons[num].close()
        del self.bottom_buttons[num]
        self.imv.getView().removeItem(self.circles[num][0])
        del self.circles[num]
        for btn in self.bottom_buttons.values():
            self.layout.removeWidget(btn)
            btn.close()
            self.layout.update()
        circles, bottom_buttons = {}, {}
        for n, num in enumerate(self.circles.keys()):
            circles[n] = self.circles[num]
            sel1 = QtGui.QRadioButton(circles[n][1])
            sel1.setChecked(False)
            sel1.clicked.connect(lambda: self._set_bottom(sel1, n,
                                                          self.circles[n][0]))
            if n == nn:
                sel1.setChecked(True)
            self.layout.addWidget(sel1, 5, n, 1, 1)
            bottom_buttons[n] = sel1
        self.circles, self.bottom_buttons = circles, bottom_buttons

    def _update_bottom(self, fit_helper):
        """update the selection region of the fit objects at the bottom"""
        self.fit_type = self.bottom_select.text()
        labels = dict(c=('r:', ''), e=('a:', 'b:'), n=('', ''))[
            self.fit_type.lower()[0]]
        self.layout.removeWidget(self.sel3)
        self.sel3.close()
        self.sel3 = RadiusSetter(labels, self.bottom_select, fit_helper)
        self.layout.addWidget(self.sel3, 0, 2, 1, 1)
        self.layout.update()

    def _set_method(self, b):
        """update the helper and the referred widget"""
        if b.text().lower().startswith("circle"):
            if b.isChecked() == True:
                self.fit_method = MyCircleOverlay
                self.sel2.setChecked(False)
                self.fit_type = 'Circ.'

        if b.text().lower().startswith('ellipse'):
            if b.isChecked() == True:
                self.fit_method = pg.EllipseROI
                self.sel1.setChecked(False)
                self.fit_type = 'Ellip.'

        self.sel2.setChecked(False)
        self.sel1.setChecked(False)
        b.setChecked(True)

    def _clear(self):
        """delate all helper objects"""
        for num in list(self.circles.keys()):
            self.imv.getView().removeItem(self.circles[num][0])
            del self.circles[num]
            self.layout.removeWidget(self.bottom_buttons[num])
            self.bottom_buttons[num].close()
            self.layout.update()
            del self.bottom_buttons[num]

    def _destroy(self):
        """destroy the window and exit"""
        QtCore.QCoreApplication.quit()

    def _get_quadrant(self, y, x):
        """ Return the quadrant for a given set of coordinates"""
        y1, y2, y3 = 0, self.data.shape[-1]/2, self.data.shape[-1]
        x1, x2, x3 = 0, self.data.shape[-2]/2, self.data.shape[-2]
        self.bounding_boxes = {1: (x2, x3, y1, y2),
                               2: (x1, x2, y1, y2),
                               3: (x1, x2, y2, y3),
                               4: (x2, x3, y2, y3)}
        for quadrant, bbox in self.bounding_boxes.items():
            if x >= bbox[0] and x < bbox[1] and y >= bbox[2] and y < bbox[3]:
                return quadrant

    def _click(self, event):
        """Event for mouse-click into ImageRegion"""
        if self.quad == 0:
            return

        try:
            event.accept()
            # Get postion of mouse-click and display it
            pos = event.pos()
            x = int(pos.x())
            y = int(pos.y())
            delete = False
            quad = self._get_quadrant(x, y)
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
                                                            dtype='i')//2)
            pen = QtGui.QPen(QtCore.Qt.red, 0.002)
            self.rect = pg.RectROI(pos=P, size=(dx, dy), movable=False,
                                   removable=False, pen=pen, invertible=False)
            self.rect.handleSize = 0
            self.imv.getView().addItem(self.rect)
            [self.rect.removeHandle(handle)
             for handle in self.rect.getHandles()]

    def _move_up(self):
        self._move('u')

    def _move_down(self):
        self._move('d')

    def _move_right(self):
        self._move('r')

    def _move_left(self):
        self._move('l')


class CalibTab(widgets.VBox):
    """Calibration-tab"""

    def __init__(self, parent):
        self.parent = parent
        self.title = 'Calibration'
        self.counts = 0

        self.sel = widgets.Dropdown(options=['None', '1', '2', '3', '4'],
                                    value='None',
                                    description='Quadrant',
                                    disabled=False)
        self.cir_btn = widgets.Button(description='Add circle',
                                      disabled=False, button_style='', icon='',
                                      tooltip='Add Helper Circle',
                                      layout=Layout(width='100px', height='30px'))
        self.clr_btn = widgets.Button(description='Clear Circle',
                                      tooltip='Remove All Circles',
                                      disabled=False, button_style='', icon='',
                                      layout=Layout(width='100px', height='30px'))

        self.cir_btn.on_click(self._add_circle)
        self.clr_btn.on_click(self._clear_circles)
        self.buttons = [self.sel]
        self.circle = None
        self.row1 = widgets.HBox([self.sel])
        self.row2 = widgets.HBox([self.cir_btn, self.clr_btn])
        super(widgets.VBox, self).__init__([self.row1, self.row2])

    def _clear_circles(self, *args):
        """delete all circles from the image"""
        for n, circle in self.parent.circles.items():
            circle.remove()
        self.parent.circles = {}
        self.row2 = widgets.HBox([self.cir_btn, self.clr_btn])
        self.children = [self.row1, self.row2]

    def _add_circle(self, *args):
        """add a circel to the image"""
        num = len(self.parent.circles.keys())
        if num >= 10:
            return
        r = 350
        for circ in self.parent.circles.values():
            circ.set_edgecolor('gray')
        self.parent._draw_circle(r, num)
        self.circle = num
        self.cir_drn = widgets.Dropdown(options=list(self.parent.circles.keys()),
                                        value=num, disabled=False,
                                        description='Sel.:',
                                        layout=Layout(width='150px', height='30px'))

        self.set_r = widgets.BoundedFloatText(value=350, min=0, max=10000,
                                              step=1, disabled=False, description='Radius')
        self.cir_drn.observe(self._sel_circle)
        self.set_r.observe(self._set_radius)
        self.row2 = widgets.HBox([self.cir_btn, self.clr_btn,
                                  self.cir_drn, self.set_r])
        self.children = [self.row1, self.row2]

    def _set_radius(self, sel):
        """Set the circle radius"""
        if sel['new'] and sel['old']:
            try:
                r = int(sel['new'])
            except TypeError:
                return
        else:
            return
        circle = self.parent.circles[self.circle]
        circle.set_radius(r)

    def _sel_circle(self, sel):
        """Select-helper circles"""
        if not isinstance(sel['new'], int):
            return
        self.circle = int(sel['new'])
        r = int(self.parent.circles[self.circle].get_radius())
        for num, circ in self.parent.circles.items():
            if num != self.circle:
                circ.set_edgecolor('gray')
            else:
                circ.set_edgecolor('r')
        self.set_r = widgets.BoundedFloatText(value=r, min=0, max=10000, step=1,
                                              disabled=False,
                                              continuous_update=True,
                                              description='Radius')
        self.cir_drn.observe(self._sel_circle)
        self.set_r.observe(self._set_radius)
        self.row2 = widgets.HBox([self.cir_btn, self.clr_btn,
                                  self.cir_drn, self.set_r])
        self.children = [self.row1, self.row2]

    def _move_quadrants(self, pos):
        """Shift a quadrant"""
        if pos['new'] and pos['old']:
            d = pos['owner'].description.lower()[0]
            if isinstance(pos['new'], dict):
                pn = int(pos['new']['value'])
            else:
                pn = int(pos['new'])
            if isinstance(pos['old'], dict):
                po = int(pos['old']['value'])
            else:
                try:
                    po = int(pos['old'])
                except:
                    po = 0
        else:
            return

        sign = np.sign(po - pn)
        if d == 'h':
            pos = np.array((0, sign))
        else:
            pos = np.array((sign, 0))
        self.parent.geom.move_quad(self.parent.quad, pos)
        self.parent._draw_rect(
            {0: None, 1: 2, 2: 1, 3: 4, 4: 3}[self.parent.quad])
        self.parent.update_plot(None)

    def _update_navi(self, pos):
        """Add navigation buttons"""
        posx_sel = widgets.BoundedIntText(value=0, min=-1000, max=1000, step=1,
                                          disabled=False, continuous_update=True,
                                          description='Horizontal')
        posy_sel = widgets.BoundedIntText(value=0, min=-1000, max=1000, step=1,
                                          disabled=False, continuous_update=True,
                                          description='Vertical')
        posx_sel.observe(self._move_quadrants)
        posy_sel.observe(self._move_quadrants)

        if pos is None:
            #self.children = (self.buttons[0],)
            self.buttons = [self.buttons[0]]

        elif len(self.buttons) == 1:
            self.buttons += [posx_sel, posy_sel]
        else:
            self.buttons[1] = posx_sel
            self.buttons[2] = posy_sel
        self.row1 = widgets.HBox(self.buttons)
        self.children = [self.row1, self.row2]

    def _set_quad(self, prop):
        """Select a quadrant"""
        self.counts += 1
        if (self.counts % 5 != 1):
            return
        pos = {0: None, 1: 2, 2: 1, 3: 4, 4: 3}[prop['new']['index']]
        try:
            self.parent.rect.remove()
        except:
            pass
        if pos is None:
            self._update_navi(pos)
            self.parent.quad = None
            return
        self.parent._draw_rect(prop['new']['index'])
        if pos != self.parent.quad:
            self._update_navi(pos)
        self.parent.quad = pos


class Calibrate_Nb(object):
    def __init__(self, raw_data, geom=None, vmin=-1000, vmax=5000,
                 figsize=(8, 8), bg='w', **kwargs):
        """Parameters:
            data (2d-array)  : File name of the geometry file, if none is given
                               (default) the image will be assembled with 29 Px
                               gaps between all modules.

            Keywords:
             geom (str/AGIPD_1MGeometry) :  The geometry file can either be
                                            an AGIPD_1MGeometry object or
                                            the filename to the geometry file
                                            in CFEL fromat
             vmin (int) : minimal value in the data array (default: -1000)
                          anything below this value will be clipped
             vmax (int) : maximum value in the data array (default: 5000)
                          anything above this value will be clipped
        """
        self.raw_data = np.clip(raw_data, vmin, vmax)
        self.data = raw_data
        self.im = None
        self.vmin = vmin
        self.vmax = vmax
        self.figsize = figsize
        self.circles = {}
        self.quad = None
        self.bg = bg
        self.cmap = cm.get_cmap('gist_earth')
        try:
            self.cmap.set_bad(bg)
        except:
            pass
        try:
            # Try to assemble the data (if geom is a AGIPD_Geometry class)
            data, _ = geom.position_all_modules(self.raw_data)
            self.geom = geom
        except AttributeError:
            # That did not work, lets try reading geometry file
            try:
                self.geom = AGIPD_1MGeometry.from_crystfel_geom(geom)
            except:
                # Fallback to evenly align quadrant positions
                quad_pos = [(-540, 610), (-540, -15), (540, -143), (540, 482)]
                self.geom = AGIPD_1MGeometry.from_quad_positions(
                    quad_pos=quad_pos)

        data, _ = self.geom.position_all_modules(self.raw_data)
        # Create a canvas
        self.canvas = np.full(np.array(data.shape) + 300, np.nan)
        self._add_widgets()
        self.update_plot(val=(vmin, vmax))
        self.rect = None
        self.sl = widgets.HBox([self.val_slider, self.cmap_sel])
        for wdg in (self.sl, self.tabs):
            display(wdg)

    @property
    def centre(self):
        return self.geom.position_all_modules(self.raw_data)[1]

    def _draw_circle(self, r, num):
        """Draw circel of radius r and add it to the circle collection"""
        centre = self.geom.position_all_modules(self.raw_data,
                                                canvas=self.canvas.shape)[1]
        self.circles[num] = plt.Circle(centre[::-1], r,
                                       facecolor='none', edgecolor='r', lw=1)
        self.ax.add_artist(self.circles[num])

    def _draw_rect(self, pos):
        """Draw a rectangle around around a given quadrant"""
        pp = {0: None, 1: 2, 2: 1, 3: 4, 4: 3}[pos]
        try:
            # Remove the old one first if there is any
            self.rect.remove()
        except:
            pass
        if pp is None:
            # If none then no new rectangle should be drawn
            return
        P, dx, dy = self.geom.get_quad_corners(pp,
                                               np.array(self.data.shape, dtype='i')//2)
        self.rect = patches.Rectangle(P, dx, dy, linewidth=1.5,
                                      edgecolor='r', facecolor='none')
        self.ax.add_patch(self.rect)
        self.update_plot(val=None)

    def _add_tabs(self):
        """Add panel tabs"""
        self.tabs = widgets.Tab()
        self.tabs.children = (CalibTab(self),)
        for i, tab in enumerate(self.tabs.children):
            self.tabs.set_title(i, tab.title)

        self.tabs.children[0].sel.observe(self.tabs.children[0]._set_quad)

    def _add_widgets(self):
        """Add widgets to the layour"""
        # Slider for the max, vmin view
        self.val_slider = widgets.FloatRangeSlider(
            value=[self.vmin, self.vmax],
            min=self.vmin-np.fabs(self.vmax-self.vmin)*0.2,
            max=self.vmax+np.fabs(self.vmax-self.vmin)*0.2,
            step=0.1,
            description='Boost:',
            disabled=False,
            continuous_update=False,
            orientation='horizontal',
            readout=True,
            readout_format='d',
            layout=Layout(width='70%'))
        self.cmap_sel = widgets.Dropdown(options=['gist_earth',
                                                  'gist_ncar', 'bone',
                                                  'winter', 'summer',
                                                  'hot', 'copper',
                                                  'OrRd', 'coolwarm',
                                                  'CMRmap', 'jet'],
                                         value='gist_earth',
                                         description='Color Map:',
                                         disabled=False,
                                         layout=Layout(width='200px'))
        self.cmap_sel.observe(self._set_cmap)
        self.val_slider.observe(self._set_clim)
        self._add_tabs()

    def _set_clim(self, val):
        """Update the color limits"""
        try:
            self.im.set_clim(*val['new'])
            self.cbar.update_bruteforce(self.im)
            cbar_ticks = np.linspace(val['new'][0], val['new'][1], 6)
            self.cbar.set_ticks(cbar_ticks)
        except:
            return

    def _set_cmap(self, val):
        """Update the colormap"""
        try:
            cmap = cm.get_cmap(str(val['new']))
            cmap.set_bad(self.bg)
            self.im.set_cmap(cmap)
        except:
            return

    def update_plot(self, val=(100, 1500), cmap='gist_earth'):
        """Update the plotted image"""
        # Update the image first
        self.data, centre = self.geom.position_all_modules(self.raw_data,
                                                           canvas=self.canvas.shape)
        cy, cx = centre
        if not self.im is None:
            if not val is None:
                self.im.set_clim(*val)
            else:
                self.im.set_array(self.data)
            h1, h2 = self.cent_cross
            h1.remove(), h2.remove()
            h1 = self.ax.hlines(cy, cx-20, cx+20, colors='r', linewidths=1)
            h2 = self.ax.vlines(cx, cy-20, cy+20, colors='r', linewidths=1)
            self.cent_cross = (h1, h2)
        else:
            self.fig = plt.figure(figsize=self.figsize, num='HDFSee',
                                  clear=True, facecolor=self.bg)
            self.ax = self.fig.add_subplot(111)
            self.im = self.ax.imshow(
                self.data, vmin=val[0], vmax=val[1], cmap=self.cmap)
            self.ax.set_xticks([]), self.ax.set_yticks([])
            h1 = self.ax.hlines(cy, cx-20, cx+20, colors='r', linewidths=1)
            h2 = self.ax.vlines(cx, cy-20, cy+20, colors='r', linewidths=1)
            self.cent_cross = (h1, h2)
            self.fig.subplots_adjust(bottom=0, top=1, hspace=0, wspace=0,
                                     right=1, left=0)
            self.cbar = self.fig.colorbar(self.im, shrink=0.8, anchor=(0.01, 0),
                                          pad=0.01, aspect=50)

            cbar_ticks = np.linspace(val[0], val[1], 6)
            self.cbar.set_ticks(cbar_ticks)


if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    Calib = Calibrate_Qt(np.load('data.npz')['data'])
    Calib.w.show()
    app.exec_()
