""" Qt Version of the detector geometry calibration
    for powder ring based calibration."""


import logging
import os
import re

import karabo_data as kd
import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

from .geometry import AGIPD_1MGeometry

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(os.path.basename(__file__))

#Fallback quad positions if no geometry file is given as a starting point:
FALLBACK_QUAD_POS = [(-540, 610), (-540, -15), (540, -143), (540, 482)]

#Definition of increments (INC) the quadrants should move to once a direction
#(u = up, d = down, r = right, l = left is given:
INC = 1
DIRECTION = {'u' : (-INC,    0),
             'd' : ( INC,    0),
             'r' : (   0,  INC),
             'l' : (   0, -INC)}

CANVAS_MARGIN = 300 #pixel, used as margin on each side of detector quadrants

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
        self.roi = roi
        if len(label): #If label is not empty add QSpinBox
            hbox = QtWidgets.QHBoxLayout()
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
        self.spin_box.setMinimum(0.001)
        self.spin_box.setMaximum(10000)
        self.spin_box.setValue(size)
        self.spin_box.valueChanged.connect(self._update_circle_prop)

    def _update_circle_prop(self):
        """Update the size and centre of circ. form button-click."""
        # Circles have only radii and
        size = max(self.spin_box.value(), 0.0001)
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


class RunDirSelecter(QtWidgets.QFrame):
    """A widget that defines run-directory, trainId and pulse selection"""

    def __init__(self, run_dir):
        """Create a btn for run-dir select and 2 spin boxes for train, puls

        Parameters:
            run_dir (str) : The default run directory
        """

        super(RunDirSelecter, self).__init__()
        self._rundir = run_dir
        self.rundir = None
        self.tid = None
        self._img = None

        #Creat an hbox with a title, a field to add a filename and a button
        hbox = QtWidgets.QHBoxLayout()

        self.run_sel = QtGui.QPushButton("Run-dir")
        self.run_sel.setToolTip('Select a Run directory')
        self.run_sel.clicked.connect(self._get_run)
        hbox.addWidget(self.run_sel)

        self.line = QtGui.QLineEdit(run_dir)
        self.line.setMaximumHeight(22)
        hbox.addWidget(self.line)

        hbox.addWidget(QtGui.QLabel('TrainId:'))
        self.tid_sel = QtGui.QSpinBox()
        self.tid_sel.setToolTip('Select TrainId')
        self.tid_sel.setValue(0)
        self.tid_sel.valueChanged.connect(self._update)
        self.tid_sel.setEnabled(False)
        hbox.addWidget(self.tid_sel)

        hbox.addWidget(QtGui.QLabel('Pulse#:'))
        self.pulse_sel = QtGui.QSpinBox()
        self.pulse_sel.setToolTip('Select TrainId')
        self.pulse_sel.setValue(0)
        self.pulse_sel.setMinimum(0)
        self.pulse_sel.setEnabled(False)
        hbox.addWidget(self.pulse_sel)

        pulse = QtGui.QRadioButton('Sel. #')
        pulse.setChecked(False)
        pulse.setEnabled(False)
        pulse.clicked.connect(lambda:self._set_sel_method(0))
        hbox.addWidget(pulse)

        max_fun = QtGui.QRadioButton('Max.')
        max_fun.setChecked(False)
        max_fun.setEnabled(False)
        max_fun.clicked.connect(lambda:self._set_sel_method(1))
        hbox.addWidget(max_fun)

        mean_fun = QtGui.QRadioButton('Mean.')
        mean_fun.setChecked(False)
        mean_fun.setEnabled(False)
        mean_fun.clicked.connect(lambda:self._set_sel_method(2))
        hbox.addWidget(mean_fun)

        self.setLayout(hbox)
        self._sel = (pulse, max_fun, mean_fun)
        #If a run directory was already given read it
        if run_dir:
            self._get_run(rundir=run_dir)
        #Apply no selection method (max, mean) to select pulses by default
        self._sel_method = None
        self._read_train = True


    def activate_spin_boxes(self, tid_range):
        """Set min/max sizes of the spinbox according to trainId's and img's"""

        self.tid_sel.setMinimum(tid_range[0])
        self.tid_sel.setMaximum(tid_range[-1])
        self.tid_sel.setValue(tid_range[0])
        self.tid_sel.setEnabled(True)
        self.pulse_sel.setEnabled(True)
        for sel in self._sel:
            sel.setEnabled(True)
        self._sel[0].setChecked(True)
        self._update()

    def _set_sel_method(self, btn_num):
        """Set the pulse selection method (pulse #, mean, max)"""

        for sel in self._sel:
            sel.setChecked(False)
        self._sel[btn_num].setChecked(True)
        if btn_num == 0:
            self.pulse_sel.setEnabled(True)
        else:
            self.pulse_sel.setEnabled(False)
        #Get the pulse selection method
        self._sel_method = {0:None, 1:np.nanmax, 2:np.nanmean}[btn_num]

    def _update(self):
        """Update train_id and img"""

        self.tid = self.tid_sel.value()
        det_info = self.rundir.detector_info(tuple(self.rundir.detector_sources)[0])
        self.pulse_sel.setMaximum(det_info['frames_per_train'])
        self._read_train = True

    def _get_run(self, rundir=None):
        """Get a run directory"""
        if not rundir:
            rundir = QtGui.QFileDialog.getExistingDirectory(self,
                                                        'Select run directory')

        if not rundir:
            return
        #This is for testing and should become /gpfs/exfel/exp/bla
        m = re.match('/home/bergeman/gpfs/exfel/exp/(?P<expt>[^/]+)/(?P<cycle>[^/]+)/(?P<prop>[^/]+)/proc/(?P<run>[^/]+)/?$',
                 rundir)
        if not m:
            raise ValueError("Expected a path like /gpfs/exfel/exp/(exp)/(cycle)/(proposal)/proc/(run)")
        self.line.setText(rundir)
        log.info('Opening run directory {}'.format(self._rundir))
        self.rundir = kd.RunDirectory(rundir)
        self.activate_spin_boxes((self.rundir.train_ids[0],
                                self.rundir.train_ids[-1]))


    def get(self):
        """Get the image of selected train"""
        if self._read_train:
            log.info('Reading train #: {}'.format(self.tid))
            _, data = self.rundir.train_from_id(self.tid)
            self._img = kd.stack_detector_data(data, 'image.data', only='DET')
            self._read_train = False

        if self._sel_method is None:
            #Read the selected train number
            pulse_num = self.pulse_sel.value()
            return self._img[pulse_num]
        else:
            return self._sel_method(self._img, axis=0)


class GeometryFileSelecter(QtWidgets.QFrame):
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
        super(GeometryFileSelecter, self).__init__()
        #Creat an hbox with a title, a field to add a filename and a button
        hbox = QtWidgets.QHBoxLayout()
        self.label = QtGui.QLabel(txt)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        hbox.addWidget(self.label)
        self.line = QtGui.QLineEdit(content)
        self.line.setMaximumHeight(22)
        hbox.addWidget(self.line)

        self.file_sel = QtGui.QPushButton("Load")
        self.file_sel.clicked.connect(self._get_files)
        hbox.addWidget(self.file_sel)
        self.apply_btn = QtGui.QPushButton('Assemble')
        self.apply_btn.setToolTip('Assemble Data')
        self.save_btn = QtGui.QPushButton('Save')
        self.save_btn.setToolTip('Save geometry')
        self.save_btn.setEnabled(False)
        hbox.addWidget(self.apply_btn)
        hbox.addWidget(self.save_btn)
        #self.setLayout(hbox)

        vlayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(hbox)
        vlayout.addLayout(hbox)
        info = QtGui.QLabel(
                'Click on Quadrant to select; '
                'CTRL+arrow-keys to move them; '
                'Click "Assemble" to apply set changes')
        info.setToolTip('Click into the Image to select a Quadrant')
        vlayout.addWidget(info)


    def _get_files(self):
        """Open a dialog box to select a file"""
        fname, _ = QtGui.QFileDialog.getOpenFileName(self,
                                                     'Load geometry file',
                                                     '.',
                                                     'CFEL file format (*.geom)')
        if fname:
            self.line.setText(fname)
        else:
            self.line.setText(None)


    @property
    def value(self):
        """Return the text of the QLinEdit element."""
        return self.line.text()

    def activate(self):
        """Change the content of buttons and QLineEdit elements."""
        self.save_btn.setEnabled(True)


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

    def __init__(self, run_dir=None, geofile=None, levels=None, header=None):
        """Display detector data and arrange panels.

        Keywords:
            run_dir (str-object)  : Directory that contains the run data
            geofile (str/AGIPD_1MGeometry)  : The geometry file can either be
                                               an AGIPD_1MGeometry object or
                                               the filename to the geometry
                                               file in CFEL fromat
            levels (tuple) : min/max values to be displayed (default: -1000)
            header (str)  : header for the geometry file
        """
        self.geofile = geofile
        self.levels = levels
        self.raw_data = None
        self.header = header or ''

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        # Create window with ImageView widget
        self.win = QtGui.QWindow()
        self.win.resize(800, 800)
        # Create new image view
        self.imv = pg.ImageView()

        self.quad = 0  # The selected quadrants
        self.selected_circle = None  #Default fit-method to create the rings
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
        self.geom_selector = GeometryFileSelecter(154, 'Geometry File:', geofile)
        self.layout.addWidget(self.geom_selector, 0, 9, 1, 1)

        # plot goes into the centre on right side, spanning 10 rows
        self.layout.addWidget(self.imv,  1, 0, 10, 10)

        #These buttons are on the top
        self.load_geom_btn = self.geom_selector.apply_btn
        self.load_geom_btn.clicked.connect(self._apply)
        self.save_geom_btn = self.geom_selector.save_btn
        self.save_geom_btn.clicked.connect(self._save_geom)
        # buttons go to the bottom
        self.clear_btn = QtGui.QPushButton('Clear Helpers')
        self.clear_btn.setToolTip('Remove All Buttons')
        self.clear_btn.clicked.connect(self._clear)
        self.layout.addWidget(self.clear_btn, 11, 0, 1, 1)
        self.add_circ_btn = QtGui.QPushButton('Draw Helper Objects')
        self.add_circ_btn.setToolTip('Add Circles to the Image')
        self.add_circ_btn.clicked.connect(self._drawCircle)
        self.layout.addWidget(self.add_circ_btn, 11, 1, 1, 1)
        self.cancel_btn = QtGui.QPushButton('Cancel')
        self.cancel_btn.clicked.connect(self._destroy)
        self.layout.addWidget(self.cancel_btn, 11, 2, 1, 1)
        self.run_selector = RunDirSelecter(run_dir)
        self.layout.addWidget(self.run_selector, 11, 3, 1, 8)
        self.info = QtGui.QLabel(
            'Click on Quadrant to select; CTRL+arrow-keys to move')
        self.info.setToolTip('Click into the Image to select a Quadrant')
        #self.layout.addWidget(self.info, 1, 4, 1, 8)
        pg.LabelItem(justify='right')
        self.window.setLayout(self.layout)

        self.isDisplayed = False


    def _apply(self):
        """Read the geometry file and position all modules."""
        if self.run_selector.rundir is None:
            return
        log.info(' Starting to assemble ... ')

        if len(self.geom_selector.value):
            try:
                self.geom = AGIPD_1MGeometry.from_crystfel_geom(
                    self.geom_selector.value)
            except TypeError:
                # Fallback to evenly align quadrant positions
                log.warn(' Using fallback option')
                self.geom = AGIPD_1MGeometry.from_quad_positions(
                    quad_pos=FALLBACK_QUAD_POS)
        else:
            log.warn(' Using fallback option')
            self.geom = AGIPD_1MGeometry.from_quad_positions(
                    quad_pos=FALLBACK_QUAD_POS)

        self.raw_data = self.run_selector.get()
        data, self.centre = self.geom.position_all_modules(self.raw_data)
        self.canvas = np.full(np.array(data.shape) + CANVAS_MARGIN, np.nan)

        self.data, self.centre =\
            self.geom.position_all_modules(self.raw_data,
                                           canvas=self.canvas.shape)
        # Display the data and assign each frame a time value from 1.0 to 3.0
        if not self.isDisplayed:
            if self.levels:
                self.imv.setImage(np.clip(self.data, *self.levels),
                        levels=self.levels,
                        xvals=np.linspace(1., 3., self.canvas.shape[0]))
            else:
                self.imv.setImage(self.data,
                        levels=self.levels,
                        xvals=np.linspace(1., 3., self.canvas.shape[0]))
            self.isDisplayed = True

        else:
            imageItem = self.imv.getImageItem()
            self.levels = tuple(imageItem.levels)
            self.imv.setImage(np.clip(self.data, *self.levels),
                    levels=self.levels,
                    xvals=np.linspace(1., 3., self.canvas.shape[0]))

        self.imv.getImageItem().mouseClickEvent = self._click
        # Set a custom color map
        self.imv.setColorMap(pg.ColorMap(*zip(*Gradients['grey']['ticks'])))
        self.geom_selector.activate()
        imageItem = self.imv.getImageItem()
        self.levels = tuple(imageItem.levels)
        self.quad = -1
    def _save_geom(self):
        """ Save the adapted geometry to a file in cfel output format"""

        fname, _ = QtGui.QFileDialog.getSaveFileName(self.geom_selector,
                                                     'Save geometry file',
                                                     'geo_assembled.geom',
                                                     'CFEL file format (*.geom)')
        if fname:
            log.info(' Saving output to {}'.format(self.geofile))
            try:
                os.remove(fname)
            except (FileNotFoundError, PermissionError):
                pass
            self.data, self.centre = self.geom.position_all_modules(
                    self.raw_data)
            self.geom.write_crystfel_geom(fname, header=self.header)
            QtCore.QCoreApplication.quit()

    def _move(self, d):
        """Move the quadrant."""
        quad = self.quad
        if  quad <= 0:
            return
        self.geom.move_quad(quad, np.array(DIRECTION[d]))
        self.data, self.centre =\
            self.geom.position_all_modules(self.raw_data,
                                           canvas=self.canvas.shape)
        self._draw_rect(quad)
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
        """Delete all helper objects."""
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
                               3: (x2, x3, y2, y3),
                               4: (x1, x2, y2, y3)}
        for quadrant, bbox in self.bounding_boxes.items():
            if bbox[0] <= x < bbox[1] and bbox[2] <= y < bbox[3]:
                return quadrant

    def _draw_rect(self, quad):
        """Draw rectangle around quadrant"""
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



    def _click(self, event):
        """Event for mouse-click into ImageRegion."""
        if self.quad == 0:
            return
        event.accept()
        # Get postion of mouse-click and display it
        pos = event.pos()
        x = int(pos.x())
        y = int(pos.y())
        quad = self._get_quadrant(x, y)
        if quad is None:
            self.imv.getView().removeItem(self.rect)
            self.rect = None
            self.quad = -1
            return
        if quad != self.quad:
            self._draw_rect(quad)

    def _move_up(self):
        self._move('u')

    def _move_down(self):
        self._move('d')

    def _move_right(self):
        self._move('r')

    def _move_left(self):
        self._move('l')



if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    calib = CalibrateQt(np.load('data.npz')['data'])
    calib.w.show()
    app.exec_()
