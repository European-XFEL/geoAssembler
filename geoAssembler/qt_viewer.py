"""Qt Version of the detector geometry calibration."""

from collections import namedtuple
from itertools import product
import logging
import os

import karabo_data as kd
import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

from .defaults import *

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(os.path.basename(__file__))

Slot = QtCore.pyqtSlot

def _warning(txt, title="Warning"):
    """Inform user about missing information."""
    msg_box = QtWidgets.QMessageBox()
    msg_box.setIcon(QtWidgets.QMessageBox.Information)
    msg_box.setText(txt)
    msg_box.setWindowTitle(title)
    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg_box.exec()


class RadiusSetter(QtWidgets.QFrame):
    """Define a Hbox containing a Spinbox with a Label."""

    def __init__(self, label, roi, parent):
        """Add a spin box with a label to set radii.

        Parameters:
           label (str) : label for the spin box

        Keywords:
           roi : selected region of interest
        """
        super(RadiusSetter, self).__init__()
        # Create a hbox with a title and a spin-box to select the circ. radius
        self.roi = roi
        self.parent = parent
        if len(label):  # If label is not empty add QSpinBox
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
    """A widget that defines run-directory, trainId and pulse selection."""

    # A Pattern to validate the entry for the run direcotry
    PULSE_SEL = namedtuple('sel_method', 'num method button')
    PULSE_MEAN = namedtuple('sel_method', 'num method button')
    PULSE_SUM = namedtuple('sel_method', 'num method button')
    PULSE_SEL.method = None
    PULSE_MEAN.method = np.nanmean
    PULSE_SUM.method = np.nansum
    PULSE_SEL.num = 1
    PULSE_MEAN.num = 2
    PULSE_SUM.num = 3

    def __init__(self, run_dir, parent):
        """Create a btn for run-dir select and 2 spin boxes for train, pulse.

        Parameters:
            run_dir (str) : The default run directory
        """
        super(RunDirSelecter, self).__init__()
        self.parent = parent
        self.rundir = None
        self.tid = None
        self._img = None
        self.min_tid = None
        self.max_tid = None

        # Creat an hbox with a title, a field to add a filename and a button
        hbox = QtWidgets.QHBoxLayout()
        self.run_sel = QtGui.QPushButton("Run-dir")
        self.run_sel.setToolTip('Select a Run directory')
        self.run_sel.clicked.connect(self._sel_run)
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
        self.PULSE_SEL.button = pulse
        pulse.clicked.connect(lambda: self._set_sel_method(self.PULSE_SEL))
        hbox.addWidget(pulse)

        sum_fun = QtGui.QRadioButton('Sum')
        sum_fun.setChecked(False)
        sum_fun.setEnabled(False)
        self.PULSE_SUM.button = sum_fun
        sum_fun.clicked.connect(lambda: self._set_sel_method(self.PULSE_SUM))
        hbox.addWidget(sum_fun)

        mean_fun = QtGui.QRadioButton('Mean.')
        mean_fun.setChecked(False)
        mean_fun.setEnabled(False)
        self.PULSE_MEAN.button = mean_fun
        mean_fun.clicked.connect(lambda: self._set_sel_method(self.PULSE_MEAN))
        hbox.addWidget(mean_fun)

        self.setLayout(hbox)
        self._sel = (pulse, sum_fun, mean_fun)
        # If a run directory was already given read it
        if run_dir:
            self._read_rundir(run_dir)
        # Apply no selection method (sum, mean) to select pulses by default
        self._sel_method = None
        self._read_train = True

    def activate_spin_boxes(self):
        """Set min/max sizes of the spinbox according to trainId's and imgs."""
        self.tid_sel.setMinimum(self.min_tid)
        self.tid_sel.setMaximum(self.max_tid)
        self.tid_sel.setValue(self.min_tid)
        self.tid_sel.setEnabled(True)
        self.pulse_sel.setEnabled(True)
        for sel in (self.PULSE_SEL, self.PULSE_MEAN, self.PULSE_SUM):
            sel.button.setEnabled(True)
        self.PULSE_SEL.button.setChecked(True)
        self._update()

    def _set_sel_method(self, btn_prop):
        """Set the pulse selection method (pulse #, mean, sum)."""
        for sel in (self.PULSE_SEL, self.PULSE_MEAN, self.PULSE_SUM):
            sel.button.setChecked(False)
        btn_prop.button.setChecked(True)
        if btn_prop.num == 1:
            self.pulse_sel.setEnabled(True)
        else:
            self.pulse_sel.setEnabled(False)
        # Get the pulse selection method
        self._sel_method = btn_prop.method

    def _update(self):
        """Update train_id and img."""
        self.tid = self.tid_sel.value()
        self.det_info = self.rundir.detector_info(
            tuple(self.rundir.detector_sources)[0])
        self.pulse_sel.setMaximum(self.det_info['frames_per_train'])
        self._read_train = True

    @Slot(bool)
    def _sel_run(self):
        """Select a run directory."""
        rfolder = QtGui.QFileDialog.getExistingDirectory(self,
                                                         'Select run directory')
        if rfolder:
            self._read_rundir(rfolder)

    def _read_rundir(self, rfolder):
        """Read a selected run directory."""
        self.line.setText(rfolder)
        log.info('Opening run directory {}'.format(rfolder))
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.rundir = kd.RunDirectory(rfolder)
        self.min_tid = self.rundir.train_ids[0]
        self.max_tid = self.rundir.train_ids[-1]
        self.activate_spin_boxes()
        QtGui.QApplication.restoreOverrideCursor()

    def get(self):
        """Get the image of selected train."""
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        if self._read_train:
            log.info('Reading train #: {}'.format(self.tid))
            _, data = self.rundir.train_from_id(self.tid)
            img = kd.stack_detector_data(data, 'image.data')
            self._img = np.clip(img, 0, None)
            self._read_train = False
        if self._sel_method is None:
            # Read the selected train number
            pulse_num = self.pulse_sel.value()
            raw_data = self._img[pulse_num]
        else:
            raw_data = self._sel_method(self._img, axis=0)
        QtGui.QApplication.restoreOverrideCursor()
        return np.nan_to_num(raw_data)


class GeometryFileSelecter(QtWidgets.QFrame):
    """Define a Hbox containing a QLineEdit with a Label."""

    def __init__(self, width, txt, parent, content=''):
        """Create nested widgets to select and save geometry files.

        Parameters:
             width (int) : width of the QLineEdit element
             txt (str) : label of the QLineEdit element

        Keywords:
            content (str) : pre filled content of the QLineEdit element
                            (dfault empty)
        """
        super(GeometryFileSelecter, self).__init__()
        # Creat an hbox with a title, a field to add a filename and a button
        hbox = QtWidgets.QHBoxLayout()
        self.label = QtGui.QLabel(txt)
        self.parent = parent
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        hbox.addWidget(self.label)
        self.line = QtGui.QLineEdit(content)
        self.line.setMaximumHeight(22)
        hbox.addWidget(self.line)

        self.file_sel = QtGui.QPushButton("Load")
        self.file_sel.clicked.connect(self._get_files)
        hbox.addWidget(self.file_sel)
        self.apply_btn = QtGui.QPushButton('Apply')
        self.apply_btn.setToolTip('Assemble Data')
        self.save_btn = QtGui.QPushButton('Save')
        self.save_btn.setToolTip('Save geometry')
        self.save_btn.setEnabled(False)
        hbox.addWidget(self.apply_btn)
        hbox.addWidget(self.save_btn)
        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.addLayout(hbox)
        info = QtGui.QLabel(
            'Click on Quadrant to select; '
            'CTRL+arrow-keys to move them; '
            'Click "Assemble" to apply set changes')
        info.setToolTip('Click into the Image to select a Quadrant')
        vlayout.addWidget(info)

    def _get_files(self):
        """Open a dialog box to select a file."""
        if self.parent.detector_sel.currentText() == 'AGIPD':
            fname, _ = QtGui.QFileDialog.getOpenFileName(self,
                                                        'Load geometry file',
                                                        '.',
                                                        'CFEL file format (*.geom)')
            self.parent.quad_pos = None
            if fname:
                self.line.setText(fname)
            else:
                self.line.setText(None)

        else:
            self.win = GeomWindow(self, self.parent.detector_sel.currentText())

    @property
    def value(self):
        """Return the text of the QLinEdit element."""
        return self.line.text()

    def activate(self):
        """Change the content of buttons and QLineEdit elements."""
        self.save_btn.setEnabled(True)


class GeomWindow(QtGui.QMainWindow):
    """Pop-up window to select quad. positions and xfel format geometry file."""

    def __init__(self, parent, det='LPD'):
        """Create a new window and add widgets quad. and geometry file
           selection.

           Parameters:
               parent (GeometryFileSelecter): main widget dealing with geometry
                                              selection
           Keywords:
               det (str): Name of the detector (default LPD)
        """
        super(GeomWindow, self).__init__(parent)
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()

        self.setWindowTitle('{} Geometry'.format(det))
        self.setFixedSize(240, 220)
        sel = QuadSelector(self, parent, det)
        self.setCentralWidget(sel)
        #Move pop-up window to centre
        qtRectangle = self.frameGeometry()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        self.show()


class QuadSelector(QtWidgets.QFrame):
    """Setup widgets for quad. positions and geometry file selection."""

    def __init__(self, window, parent, det='LPD'):
        """Create a table element for quadrant selection and file selection
           dialogue for geometry file selection (in hdf5 format).

           Parameters:
               window (QtGui.QMainWindow) : window object where widgets are
                                            going to be displayed
               parent (GeometryFileSelecter): main widget dealing with geometry
                                              selection
          Keywords:
              det (str) : Name to the detector (default LPD)
        """
        super(QuadSelector, self).__init__(window)
        self.parent = parent
        self.window = window
        self.det = det
        self.quad_table = QtGui.QTableWidget(4, 2)
        self.quad_table.setToolTip('Set the Quad-Pos in mm')
        self.quad_table.setHorizontalHeaderLabels(['Quad X-Pos', 'Quad Y-Pos'])
        self.quad_table.setVerticalHeaderLabels(['1', '2', '3', '4'])
        for n, quad_pos in enumerate(FALLBACK_QUAD_POS[det]):
            self.quad_table.setItem(n, 0, QtGui.QTableWidgetItem(str(quad_pos[0])))
            self.quad_table.setItem(n, 1, QtGui.QTableWidgetItem(str(quad_pos[1])))
        self.quad_table.move(0,0)

        self.file_sel = QtGui.QPushButton('Select Geometry File')
        self.file_sel.setToolTip('Select a Geometry File in xfel (hdf5) format.')
        self.file_sel.clicked.connect(self._get_files)

        self.ok_btn = QtGui.QPushButton('Ok')
        self.ok_btn.clicked.connect(self._apply)
        self.cancel_btn = QtGui.QPushButton('Cancel')
        self.cancel_btn.clicked.connect(self._cancel)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.ok_btn)
        hbox.addWidget(self.cancel_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.quad_table)
        layout.addWidget(self.file_sel)
        layout.addLayout(hbox)
        self.setLayout(layout)

    def _get_files(self):
        """File-selection dialogue to get hdf5 geometry file."""
        fname, _ = QtGui.QFileDialog.getOpenFileName(self,
                                                    'Load geometry file',
                                                    '.',
                                                    'XFEL file format (*.h5)')
        # Put the filename into the geometry file field of the main gui
        self.parent.line.setText(fname)

    def _apply(self):
        """Read quad. pos and update the detectors fallback positions."""
        quad_pos = [[None, None] for i in range(self.quad_table.rowCount())]
        for i, j in product(
                            range(self.quad_table.rowCount()),
                            range(self.quad_table.columnCount())):
            table_element = self.quad_table.item(i, j)
            try:
                quad_pos[i][j] = float(table_element.text())
            except ValueError:
                _warning('Table Elements must be Float')
                return
        FALLBACK_QUAD_POS[self.det] = quad_pos
        if not self.parent.value:
            _warning('You must Select a Geometry File')
            return
        self.window.destroy()

    def _cancel(self):
        """Close the window."""
        self.window.destroy()


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
        self.levels = levels or [None, None]
        self.raw_data = None
        self.header = header or ''
        self.show_info = True # Show info pop-up after saving geometry
                              # not used for ci-testing

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        # Create new image view
        self.imv = pg.ImageView()

        self.quad = 0  # The selected quadrants
        self.selected_circle = None  # Default fit-method to create the rings
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
        self.window.showMaximized()
        self.window.setWindowTitle('GeoAssembler Gui')
        self.layout = QtGui.QGridLayout()

        # circle manipulation other input dialogs go to the top
        self.radius_setter = RadiusSetter('', None, self)
        self.detector_sel = QtGui.QComboBox()
        self.detector_sel.addItem('AGIPD')
        self.detector_sel.addItem('LPD')
        self.layout.addWidget(self.detector_sel, 0, 1, 1, 1)
        self.layout.addWidget(self.radius_setter, 0, 2, 1, 1)
        self.geom_selector = GeometryFileSelecter(GEOM_SEL_WIDTH,
                                                  'Geometry File:',
                                                  self,
                                                  geofile)
        self.layout.addWidget(self.geom_selector, 0, 9, 1, 1)

        # plot goes into the centre on right side, spanning 10 rows
        self.layout.addWidget(self.imv,  1, 0, 10, 10)

        # These buttons are on the top
        self.apply_btn = self.geom_selector.apply_btn
        self.apply_btn.clicked.connect(self._apply)
        self.save_btn = self.geom_selector.save_btn
        self.save_btn.clicked.connect(self._save_geom)
        self.load_geom_btn = self.geom_selector.file_sel
        # buttons go to the bottom
        self.clear_btn = QtGui.QPushButton('Clear Helpers')
        self.clear_btn.setToolTip('Remove All Buttons')
        self.clear_btn.clicked.connect(self._clear)
        self.layout.addWidget(self.clear_btn, 11, 0, 1, 1)
        self.add_circ_btn = QtGui.QPushButton('Draw Helper Objects')
        self.add_circ_btn.setToolTip('Add Circles to the Image')
        self.add_circ_btn.clicked.connect(self._drawCircle)
        self.layout.addWidget(self.add_circ_btn, 11, 1, 1, 1)
        self.cancel_btn = QtGui.QPushButton('Quit')
        self.cancel_btn.clicked.connect(self._destroy)
        self.layout.addWidget(self.cancel_btn, 11, 2, 1, 1)
        self.run_selector = RunDirSelecter(run_dir, self)
        self.run_selector_btn = self.run_selector.run_sel
        self.layout.addWidget(self.run_selector, 11, 3, 1, 8)
        self.info = QtGui.QLabel(
            'Click on Quadrant to select; CTRL+arrow-keys to move')
        self.info.setToolTip('Click into the Image to select a Quadrant')
        pg.LabelItem(justify='right')
        self.window.setLayout(self.layout)
        self.is_displayed = False

    def _apply(self):
        """Read the geometry file and position all modules."""
        self.det = self.detector_sel.currentText()
        if self.run_selector.rundir is None:
            return
        if self.det != 'AGIPD' and not self.geom_selector.value:
            _warning('Click the load button to load a geometry file')
            return
        log.info(' Starting to assemble ... ')
        quad_pos = FALLBACK_QUAD_POS[self.det]
        GeometryModule = GEOM_MODULES[self.det]
        self.geom_file = self.geom_selector.value
        self.geom = GeometryModule.load(self.geom_selector.value, quad_pos)
        self.raw_data = self.run_selector.get()
        data, self.centre = self.geom.position(self.raw_data)
        self.canvas = np.full(np.array(data.shape) + CANVAS_MARGIN, np.nan)

        self.data, self.centre =\
            self.geom.position(self.raw_data,
                                           canvas=self.canvas.shape)
        # Display the data and assign each frame a time value from 1.0 to 3.0
        if not self.is_displayed:
            xvals = np.linspace(1., 3., self.canvas.shape[0])
            try:
                self.imv.setImage(np.clip(self.data, *self.levels),
                                  levels=self.levels, xvals=xvals)
            except ValueError:
                self.imv.setImage(self.data,
                                  levels=None, xvals=xvals)
            self.is_displayed = True

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
        """Save the adapted geometry to a file in cfel output format."""
        if self.det == 'AGIPD':
            file_type = ('CFEL', 'geom')
        else:
            file_type = ('XFEL', 'csv')
        fname, _ = QtGui.QFileDialog.getSaveFileName(self.geom_selector,
                                                     'Save geometry file',
                                                     'geo_assembled.{}'.format(file_type[-1]),
                                                     '{} file format (*.{})'.format(*file_type))
        if fname:
            log.info(' Saving output to {}'.format(fname))
            try:
                os.remove(fname)
            except (FileNotFoundError, PermissionError):
                pass
            self.data, self.centre = self.geom.position(
                self.raw_data)
            self.geom.write_geom(fname, self.geom_file, header=self.header)
            if self.show_info:
                _warning('Geometry information saved to {}'.format(fname),
                         title='Info')

    def _move(self, d):
        """Move the quadrant."""
        quad = self.quad
        if quad <= 0:
            return
        self.geom.move_quad(quad, np.array(DIRECTION[d]))
        self.data, self.centre =\
            self.geom.position(self.raw_data,
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
        self.radius_setter = RadiusSetter('Radius', fit_helper, self)
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
        """Remove handles from all rois."""
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
        self.radius_setter = RadiusSetter(
            'Radius:', self.selected_circle, self)
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
        self.radius_setter = RadiusSetter('', None, self)
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
        """Draw rectangle around quadrant."""
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

