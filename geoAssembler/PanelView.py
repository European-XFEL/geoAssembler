"""Detector geometry calibration  for powder ring based calibration."""

import os
import logging

from ipywidgets import widgets, Layout
from IPython.display import display
from matplotlib import pyplot as plt, cm
import matplotlib.patches as patches
import numpy as np
import pyqtgraph as pg
from PIL import Image
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

from .geometry import AGIPD_1MGeometry

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(os.path.basename(__file__))


class RadiusSetter(QtWidgets.QFrame):
    """Define a Hbox containing a Spinbox with a Label."""

    def __init__(self, label, roi):
        """Add a spin box with a label to set radii.

        Parameters:
           label (str) : label for the spin box

        Keywords:
           roi : selected region of interest
        """
        super(RadiusSetter, self).__init__()
        #Create a hbox with a title and a spin-box to select the circ. radius
        hbox = QtWidgets.QHBoxLayout()
        self.roi = roi
        if len(label): #If label is not empty add QSpinBox
            hbox.addWidget(QtGui.QLabel(label))
            size = int(self.roi.size()[0])
            self.spin_box = QtGui.QSpinBox()
            self.spin_box.setMinimum(0)
            self.spin_box.setMaximum(10000)
            self.spin_box.setValue(size)
            self.spin_box.valueChanged.connect(self._update_circle_prop)
            hbox.addWidget(self.spin_box)
            self.setLayout(hbox)

    def add_circle_prop(self):
        """Add properties for a new circle."""
        size = int(self.roi.size()[0])
        self.spin_box = QtGui.QSpinBox()
        self.spin_box.setMinimum(0)
        self.spin_box.setMaximum(10000)
        self.spin_box.setValue(size)
        self.spin_box.valueChanged.connect(self._update_circle_prop)

    def _update_circle_prop(self):
        """Update the size and centre of circ. form button-click."""
        # Circles have only radii and
        size = self.spin_box.value()
        pos = self.roi.pos()
        centre = (pos[0] + self.roi.size()[0]//2,
                  pos[1] + self.roi.size()[1]//2)
        new_pos = (centre[0] - size//2,
                   centre[1] - size//2)
        self.roi.setPos(new_pos)
        self.roi.setSize((size, size))

    def set_value(self, roi):
        """Update spin_box if ROI is changed by hand."""
        self.spin_box.setValue(int(roi.size()[0]))


class GeometrySelecter(QtWidgets.QFrame):
    """Define a Hbox containing a QLineEdit with a Label."""

    def __init__(self, width, txt, content=''):
        """Create nested widgets to select and save geometry files.

        Parameters:
             width (int) : width of the QLineEdit element
             txt (str) : label of the QLineEdit element

           Keywords:
               content (str) : pre filled content of the QLineEdit element
                               (dfault empty)
        """
        super(GeometrySelecter, self).__init__()
        #Creat an hbox with a title, a field to add a filename and a button
        hbox = QtWidgets.QHBoxLayout()
        self.label = QtGui.QLabel(txt)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        hbox.addWidget(self.label)
        self.line = QtGui.QLineEdit(content)
        self.line.setMaximumHeight(22)
        hbox.addWidget(self.line)
        self.button = QtGui.QPushButton('Apply')
        self.button.setToolTip('Assemble Data')
        hbox.addWidget(self.button)
        self.setLayout(hbox)

    @property
    def value(self):
        """Return the text of the QLinEdit element."""
        return self.line.text()

    def clear(self, buttontxt='Apply', linetxt=None,
              tooltip='Assemble Data', buttonfunc=lambda: None):
        """Change the content of buttons and QLineEdit elements."""
        self.line.setText(linetxt)
        self.button.setText(buttontxt)
        self.button.setToolTip(tooltip)


class CircleROI(pg.EllipseROI):
    """Define a Elliptic ROI with a fixed aspect ratio (aka circle)."""

    def __init__(self, pos, size, **args):
        """Create a circular region of interest.

        Parameters:
           pos (int) : centre of the circle
           size (int) : diameter of the circle
           args : other arguments passed to pg.ROI
        """
        pg.ROI.__init__(self, pos, size, **args)
        self.aspectLocked = True


class CalibrateQt:
    """Qt-Version of the Calibration Class."""

    def __init__(self, raw_data, geofile=None, vmin=-1000, vmax=5000, **kwargs):
        """Display detector data and arrange panels.

        Parameters:
            raw_data (3d-array)  : Data array, containing detector image
                                   (nmodules, y, x)
        Keywords:
            geofile (str/AGIPD_1MGeometry)  : The geometry file can either be
                                               an AGIPD_1MGeometry object or
                                               the filename to the geometry
                                               file in CFEL fromat
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

        self.quad = 0  # The selected quadrants
        self.selected_circle = CircleROI  #Default fit-method to create the rings
        # Circle Points by Quadrant
        self.circles = {}
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
        self.window = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()

        # circle/ellipse selection and input dialogs go to the top
        self.radius_setter = RadiusSetter('', None)
        self.layout.addWidget(self.radius_setter, 0, 2, 1, 1)
        self.geom_selector = GeometrySelecter(254, 'Geometry File:', geofile)
        self.layout.addWidget(self.geom_selector, 0, 9, 1, 1)

        # plot goes into the centre on right side, spanning 10 rows
        self.layout.addWidget(self.imv,  1, 0, 10, 10)

        # buttons go to the bottom
        self.geom_btn = self.geom_selector.button
        self.geom_btn.clicked.connect(self._apply)
        self.clear_btn = QtGui.QPushButton('Clear Helpers')
        self.clear_btn.setToolTip('Remove All Buttons')
        self.clear_btn.clicked.connect(self._clear)
        self.layout.addWidget(self.clear_btn, 11, 0, 1, 1)
        self.add_circ_btn = QtGui.QPushButton('Draw Helper Objects')
        self.add_circ_btn.setToolTip('Add Circles to the Image')
        self.add_circ_btn.clicked.connect(self._drawCircle)
        self.layout.addWidget(self.add_circ_btn, 11, 1, 1, 1)
        self.cancle_btn = QtGui.QPushButton('Cancel')
        self.cancle_btn.clicked.connect(self._destroy)
        self.layout.addWidget(self.cancle_btn, 11, 2, 1, 1)
        self.info = QtGui.QLabel(
            'Click on Quadrant to select; CTRL+arrow-keys to move')
        self.info.setToolTip('Click into the Image to select a Quadrant')
        self.layout.addWidget(self.info, 11, 3, 1, 8)
        pg.LabelItem(justify='right')
        self.window.setLayout(self.layout)

    def _apply(self):
        """Read the geometry file and position all modules."""
        if self.quad == 0:
            log.info(' Starting to assemble ... ')
            try:
                self.geom = AGIPD_1MGeometry.from_crystfel_geom(
                    self.geom_selector.value)
            except TypeError:
                # Fallback to evenly align quadrant positions
                quad_pos = [(-540, 610), (-540, -15), (540, -143), (540, 482)]
                self.geom = AGIPD_1MGeometry.from_quad_positions(
                    quad_pos=quad_pos)

            data, self.centre = self.geom.position_all_modules(self.raw_data)
            self.canvas = np.full(np.array(data.shape) + 300, np.nan)

            self.data, self.centre =\
                self.geom.position_all_modules(self.raw_data,
                                               canvas=self.canvas.shape)
            # Display the data and assign each frame a time value from 1.0 to 3.0
            self.imv.setImage(self.data,
                              xvals=np.linspace(1., 3., self.canvas.shape[0]))
            self.imv.getImageItem().mouseClickEvent = self._click

            # Set a custom color map
            # Get the colormap
            cmap = pg.ColorMap(*zip(*Gradients['grey']['ticks']))
            self.imv.setColorMap(cmap)

            self.geom_selector.clear(buttontxt='Save', linetxt='sample.geom',
                            tooltip='Save Geometry File')
            self.quad = -1
        else:
            log.info(' Saving output to %s' % self.geofile)
            if not self.geom_selector.line.text():
                self.geofile = 'sample.geom'
            else:
                self.geofile = self.geom_selector.line.text()

            try:
                os.remove(self.geofile)
            except (FileNotFoundError, PermissionError):
                pass
            self.data, self.centre = self.geom.position_all_modules(
                self.raw_data)
            if self.geofile.split('.')[-1].lower() == 'geom':
                self.geom.write_crystfel_geom(self.geofile)
            elif 'tif' in self.geofil.split('.')[-1]:
                data = np.ma.masked_invalid(self.data)
                im = Image.fromarray(
                    np.ma.masked_outside(data, self.vmin, self.vmax).filled(0))
                im.save(self.geofile)
            QtCore.QCoreApplication.quit()

    def _move(self, d):
        """Move the quadrant."""
        quad = self.quad
        if  quad <= 0:
            return
        inc = 1
        dd = {'u' : (-inc,    0),
              'd' : ( inc,    0),
              'r' : (   0,  inc),
              'l' : (   0, -inc)}[d]
        self.geom.move_quad(quad, np.array(dd))
        self.data, self.centre =\
            self.geom.position_all_modules(self.raw_data,
                                           canvas=self.canvas.shape)
        self._click(quad)
        self.imv.getImageItem().updateImage(self.data)

    def _drawCircle(self):
        """Add a fit object to the image."""
        if self.quad == 0 or len(self.circles) > 9:
            return
        y, x = int(self.canvas.shape[0]//2), int(self.canvas.shape[1]//2)
        fit_helper = CircleROI(pos=(x-x//2, y-x//2), size=x//1,
                                     removable=True, movable=False)
        # Add top and bottom Handles
        self._remove_handles()
        self._add_handles(fit_helper)
        self.imv.getView().addItem(fit_helper)
        circle_selection = QtGui.QRadioButton('Circ.')
        circle_selection.setChecked(True)
        self.radius_setter = RadiusSetter('Radius', fit_helper)
        num = len(self.circles)
        for sel in self.bottom_buttons.values():
            sel.setChecked(False)
        self.bottom_buttons[num] = circle_selection
        self.circles[num] = fit_helper
        self.bottom_select = circle_selection
        self.selected_circle = fit_helper
        circle_selection.clicked.connect(lambda:
                self._set_bottom(circle_selection, num))
        self._update_spinbox()
        self.layout.addWidget(circle_selection, 12, num, 1, 1)
        fit_helper.sigRegionChangeFinished.connect(
            lambda: self.radius_setter.set_value(fit_helper))

    def _add_handles(self, roi):
        """Add handles to a circle roi."""
        roi.setPen(QtGui.QPen(QtCore.Qt.red, 0.002))
        roi.handleSize = 5
        roi.addScaleHandle([0.5, 0], [0.5, 1])
        roi.addScaleHandle([0.5, 1], [0.5, 0])

    def _remove_handles(self):
        """Remove handles from all roi's."""
        for n, roi in self.circles.items():
            roi.setPen(QtGui.QPen(QtCore.Qt.gray, 0.002))
            for handle in roi.getHandles():
                roi.removeHandle(handle)

    def _set_bottom(self, b, num):
        """Add a selection button for a fit object to the bottom region."""
        self._remove_handles()
        self.selected_circle = self.circles[num]
        self.radius_setter.roi = self.circles[num]
        self._update_spinbox()
        self.radius_setter.add_circle_prop()
        self.radius_setter.button = b
        self.bottom_select.setChecked(False)
        self.bottom_select = b
        for sel in self.bottom_buttons.values():
            sel.setChecked(False)
        b.setChecked(True)
        # Set all unselected circles to blue
        self._add_handles(self.circles[num])

    def _update_spinbox(self):
        """Update the selection region of the fit objects at the bottom."""
        self.layout.removeWidget(self.radius_setter)
        self.radius_setter.close()
        self.radius_setter = RadiusSetter('Radius:', self.selected_circle)
        self.layout.addWidget(self.radius_setter, 0, 2, 1, 1)
        self.layout.update()

    def _clear(self):
        """Delate all helper objects."""
        for num in self.circles.keys():
            self.imv.getView().removeItem(self.circles[num])
            self.layout.removeWidget(self.bottom_buttons[num])
            self.bottom_buttons[num].close()
        self.bottom_buttons = {}
        self.circles = {}
        self.layout.removeWidget(self.radius_setter)
        self.radius_setter.close()
        self.radius_setter = RadiusSetter('', None)
        self.layout.addWidget(self.radius_setter, 0, 2, 1, 1)
        self.layout.update()

    def _destroy(self):
        """Destroy the window and exit."""
        QtCore.QCoreApplication.quit()

    def _get_quadrant(self, y, x):
        """Return the quadrant for a given set of coordinates."""
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
        """Event for mouse-click into ImageRegion."""
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
        except AttributeError:
            quad = event
            delete= True
        if quad is None:
            self.imv.getView().removeItem(self.rect)
            self.rect = None
            self.quad = -1
            return
        if quad != self.quad or delete:
            try:
                self.imv.getView().removeItem(self.rect)
            except AttributeError:
                pass
            self.quad = quad
            P, dx, dy =\
            self.geom.get_quad_corners(quad,
                                       np.array(self.data.shape, dtype='i')//2)
            pen = QtGui.QPen(QtCore.Qt.red, 0.002)
            self.rect = pg.RectROI(pos=P,
                                   size=(dx, dy),
                                   movable=False,
                                   removable=False,
                                   pen=pen,
                                   invertible=False)
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
    """Calibration-tab of type ipython widget vbox."""

    def __init__(self, parent):
        """Add tab to calibrate geometry to the main widget.

        Parameters:
           parent : CalibrateNb object
        """
        self.parent = parent
        self.title = 'Calibration'
        self.counts = 0

        self.selection = widgets.Dropdown(options=['None', '1', '2', '3', '4'],
                                          value='None',
                                          description='Quadrant',
                                          disabled=False)
        self.circ_btn = widgets.Button(description='Add circle',
                                      disabled=False,
                                      button_style='',
                                      icon='',
                                      tooltip='Add Helper Circle',
                                      layout=Layout(width='100px',
                                                    height='30px'))
        self.clr_btn = widgets.Button(description='Clear Circle',
                                      tooltip='Remove All Circles',
                                      disabled=False,
                                      button_style='',
                                      icon='',
                                      layout=Layout(width='100px',
                                                    height='30px'))

        self.circ_btn.on_click(self._add_circle)
        self.clr_btn.on_click(self._clear_circles)
        self.buttons = [self.selection]
        self.circle = None
        self.row1 = widgets.HBox([self.selection])
        self.row2 = widgets.HBox([self.circ_btn, self.clr_btn])
        super(CalibTab, self).__init__([self.row1, self.row2])

    def _clear_circles(self, *args):
        """Delete all circles from the image."""
        for n, circle in self.parent.circles.items():
            circle.remove()
        self.parent.circles = {}
        self.row2 = widgets.HBox([self.circ_btn, self.clr_btn])
        self.children = [self.row1, self.row2]

    def _add_circle(self, *args):
        """Add a circel to the image."""
        num = len(self.parent.circles)
        if num >= 10: #Draw only 10 circles at max
            return
        r = 350
        for circ in self.parent.circles.values():
            circ.set_edgecolor('gray')
        self.parent._draw_circle(r, num)
        self.circle = num
        self.circ_drn = widgets.Dropdown(options=list(self.parent.circles.keys()),
                                        value=num,
                                        disabled=False,
                                        description='Sel.:',
                                        layout=Layout(width='150px',
                                                      height='30px'))

        self.set_r = widgets.BoundedFloatText(value=350,
                                              min=0,
                                              max=10000,
                                              step=1,
                                              disabled=False,
                                              description='Radius')
        self.circ_drn.observe(self._sel_circle)
        self.set_r.observe(self._set_radius)
        self.row2 = widgets.HBox([self.circ_btn, self.clr_btn,
                                  self.circ_drn, self.set_r])
        self.children = [self.row1, self.row2]

    def _set_radius(self, selection):
        """Set the circle radius."""
        if selection['new'] and selection['old']:
            try:
                r = int(selection['new'])
            except TypeError:
                return
        else:
            return
        circle = self.parent.circles[self.circle]
        circle.set_radius(r)

    def _sel_circle(self, selection):
        """Select-helper circles."""
        if not isinstance(selection['new'], int):
            return
        self.circle = int(selection['new'])
        r = int(self.parent.circles[self.circle].get_radius())
        for num, circ in self.parent.circles.items():
            if num != self.circle:
                circ.set_edgecolor('gray')
            else:
                circ.set_edgecolor('r')
        self.set_r = widgets.BoundedFloatText(value=r,
                                              min=0,
                                              max=10000,
                                              step=1,
                                              disabled=False,
                                              continuous_update=True,
                                              description='Radius')
        self.set_r.observe(self._set_radius)
        self.row2 = widgets.HBox([self.circ_btn, self.clr_btn,
                                  self.circ_drn, self.set_r])
        self.children = [self.row1, self.row2]

    def _move_quadrants(self, pos):
        """Shift a quadrant."""
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
                except TypeError:
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
        """Add navigation buttons."""
        posx_sel = widgets.BoundedIntText(value=0,
                                          min=-1000,
                                          max=1000,
                                          step=1,
                                          disabled=False,
                                          continuous_update=True,
                                          description='Horizontal')
        posy_sel = widgets.BoundedIntText(value=0,
                                          min=-1000,
                                          max=1000,
                                          step=1,
                                          disabled=False,
                                          continuous_update=True,
                                          description='Vertical')
        posx_sel.observe(self._move_quadrants)
        posy_sel.observe(self._move_quadrants)

        if pos is None:
            self.buttons = [self.buttons[0]]

        elif len(self.buttons) == 1:
            self.buttons += [posx_sel, posy_sel]
        else:
            self.buttons[1] = posx_sel
            self.buttons[2] = posy_sel
        self.row1 = widgets.HBox(self.buttons)
        self.children = [self.row1, self.row2]

    def _set_quad(self, prop):
        """Select a quadrant."""
        self.counts += 1
        if (self.counts % 5 != 1):
            return
        pos = {0: None, 1: 2, 2: 1, 3: 4, 4: 3}[prop['new']['index']]
        try:
            self.parent.rect.remove()
        except (AttributeError, ValueError):
            pass
        if pos is None:
            self._update_navi(pos)
            self.parent.quad = None
            return
        self.parent._draw_rect(prop['new']['index'])
        if pos != self.parent.quad:
            self._update_navi(pos)
        self.parent.quad = pos


class CalibrateNb:
    """Ipython Widget version of the Calibration Class."""

    def __init__(self, raw_data, geometry=None, vmin=-1000, vmax=5000, **kwargs):
        """Display detector data and arrange panels.

        Parameters:
            raw_data (3d-array)  : Data array, containing detector image
                                   (nmodules, y, x)
        Keywords:
            geometry (str/AGIPD_1MGeometry)  : The geometry file can either be
                                               an AGIPD_1MGeometry object or
                                               the filename to the geometry
                                               file in CFEL fromat
            vmin (int) : minimal value in the data array (default: -1000)
                          anything below this value will be clipped
            vmax (int) : maximum value in the data array (default: 5000)
                          anything above this value will be clipped
            kwargs : additional keyword arguments that are parsed to matplotlib
        """
        self.raw_data = np.clip(raw_data, vmin, vmax)
        self.data = raw_data
        self.im = None
        self.vmin = vmin
        self.vmax = vmax
        try:
            self.figsize = kwargs['figsize']
        except KeyError:
            self.figsize = (8, 8)
        self.circles = {}
        self.quad = None
        try:
            self.bg = kwargs['bg']
        except KeyError:
            self.bg = 'w'
        self.cmap = cm.get_cmap('gist_earth')
        try:
            self.cmap.set_bad(self.bg)
        except (ValueError, KeyError):
            self.bg = 'w'
        try:
            # Try to assemble the data (if geom is a AGIPD_Geometry class)
            data, _ = geometry.position_all_modules(self.raw_data)
            self.geom = geometry
        except AttributeError:
            # That did not work, lets try reading geometry file
            try:
                self.geom = AGIPD_1MGeometry.from_crystfel_geom(geometry)
            except TypeError:
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
        """Return the centre of the image (beam)."""
        return self.geom.position_all_modules(self.raw_data)[1]

    def _draw_circle(self, r, num):
        """Draw circel of radius r and add it to the circle collection."""
        centre = self.geom.position_all_modules(self.raw_data,
                                                canvas=self.canvas.shape)[1]
        self.circles[num] = plt.Circle(centre[::-1], r,
                                       facecolor='none', edgecolor='r', lw=1)
        self.ax.add_artist(self.circles[num])

    def _draw_rect(self, pos):
        """Draw a rectangle around around a given quadrant."""
        pp = {0: None, 1: 2, 2: 1, 3: 4, 4: 3}[pos]
        try:
            # Remove the old one first if there is any
            self.rect.remove()
        except (AttributeError, ValueError):
            pass
        if pp is None:
            # If none then no new rectangle should be drawn
            return
        P, dx, dy =\
        self.geom.get_quad_corners(pp, np.array(self.data.shape, dtype='i')//2)

        self.rect = patches.Rectangle(P,
                                      dx,
                                      dy,
                                      linewidth=1.5,
                                      edgecolor='r',
                                      facecolor='none')
        self.ax.add_patch(self.rect)
        self.update_plot(val=None)

    def _add_tabs(self):
        """Add panel tabs."""
        self.tabs = widgets.Tab()
        self.tabs.children = (CalibTab(self),)
        for i, tab in enumerate(self.tabs.children):
            self.tabs.set_title(i, tab.title)

        self.tabs.children[0].selection.observe(self.tabs.children[0]._set_quad)

    def _add_widgets(self):
        """Add widgets to the layour."""
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
        """Update the color limits."""
        try:
            self.im.set_clim(*val['new'])
            self.cbar.update_bruteforce(self.im)
            cbar_ticks = np.linspace(val['new'][0], val['new'][1], 6)
            self.cbar.set_ticks(cbar_ticks)
        except (AttributeError, ValueError, KeyError):
            return

    def _set_cmap(self, val):
        """Update the colormap."""
        try:
            cmap = cm.get_cmap(str(val['new']))
            cmap.set_bad(self.bg)
            self.im.set_cmap(cmap)
        except (AttributeError, ValueError, KeyError):
            return

    def update_plot(self, val=(100, 1500), cmap='gist_earth'):
        """Update the plotted image."""
        # Update the image first
        self.data, centre =\
        self.geom.position_all_modules(self.raw_data, canvas=self.canvas.shape)
        cy, cx = centre
        if self.im is not None:
            if val is not None:
                self.im.set_clim(*val)
            else:
                self.im.set_array(self.data)
            h1, h2 = self.cent_cross
            h1.remove()
            h2.remove()
            h1 = self.ax.hlines(cy, cx-20, cx+20, colors='r', linewidths=1)
            h2 = self.ax.vlines(cx, cy-20, cy+20, colors='r', linewidths=1)
            self.cent_cross = (h1, h2)
        else:
            self.fig = plt.figure(figsize=self.figsize,
                                  clear=True, facecolor=self.bg)
            self.ax = self.fig.add_subplot(111)
            self.im = self.ax.imshow(
                self.data, vmin=val[0], vmax=val[1], cmap=self.cmap)
            self.ax.set_xticks([]), self.ax.set_yticks([])
            h1 = self.ax.hlines(cy, cx-20, cx+20, colors='r', linewidths=1)
            h2 = self.ax.vlines(cx, cy-20, cy+20, colors='r', linewidths=1)
            self.cent_cross = (h1, h2)
            self.fig.subplots_adjust(bottom=0,
                                     top=1,
                                     hspace=0,
                                     wspace=0,
                                     right=1,
                                     left=0)

            self.cbar = self.fig.colorbar(self.im,
                                          shrink=0.8,
                                          anchor=(0.01, 0),
                                          pad=0.01,
                                          aspect=50)

            cbar_ticks = np.linspace(val[0], val[1], 6)
            self.cbar.set_ticks(cbar_ticks)


if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    calib = CalibrateQt(np.load('data.npz')['data'])
    calib.w.show()
    app.exec_()
