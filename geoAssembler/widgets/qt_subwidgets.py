from collections import namedtuple
import logging

import karabo_data as kd
import numpy as np
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

from .qt_objects import (CircleROI, SquareROI)

from ..defaults import DefaultGeometryConfig as Defaults
from ..gui_utils import (read_geometry, write_geometry)


log = logging.getLogger(__name__)
Slot = QtCore.pyqtSlot

class FitObjectWidget(QtWidgets.QFrame):
    """Define a Hbox containing a Spinbox with a Label."""
    draw_signal = QtCore.pyqtSignal()
    delete_signal = QtCore.pyqtSignal()


    def __init__(self, main_widget):
        """Add a spin box with a label to set radii.

        Parameters:
           label (str) : label for the spin box

        Keywords:
           roi : selected region of interest
        """
        super().__init__()
        # Create a hbox with a title and a spin-box to select the circ. radius
        self.main_widget = main_widget
        hbox = QtWidgets.QHBoxLayout()

        # Add a spinbox with title 'Size'
        self._spin_box = QtGui.QSpinBox()
        self._spin_box.setMinimum(0)
        self._spin_box.setMaximum(10000)
        self._spin_box.setEnabled(False)
        self._spin_box.valueChanged.connect(self._update_roi)

        # Set selection of fit helper types
        self._fit_type_combobox = QtWidgets.QComboBox()
        self._fit_type_combobox.setToolTip('Select the type of object that '
                                           'helps aligning the quadrants')
        self._fit_type_combobox.addItem('Circle')
        self._fit_type_combobox.addItem('Rectangle')

        # Add selection of fit helpers (roi)
        self._roi_combobox = QtWidgets.QComboBox()
        self._roi_combobox.setEnabled(False)
        self._roi_combobox.currentIndexChanged.connect(self._get_roi)

        # Add button to create fit helpers
        self._add_roi_btn = QtGui.QPushButton('Draw Helper Object')
        self._add_roi_btn.setToolTip('Add Circles to the Image')
        self._add_roi_btn.clicked.connect(self._draw)

        # Add button to clear all fit helpers
        self._clr_roi_btn = QtGui.QPushButton('Clear Helpers')
        self._clr_roi_btn.setToolTip('Remove all fit Helpers')
        self._clr_roi_btn.clicked.connect(self._clear)

        self.rois = {}
        self.current_roi = None

        hbox.addWidget(QtGui.QLabel('Size:'))
        hbox.addWidget(self._spin_box)
        hbox.addWidget(QtGui.QLabel('Helper Type:'))
        hbox.addWidget(self._fit_type_combobox)
        hbox.addWidget(QtGui.QLabel('Num.:'))
        hbox.addWidget(self._roi_combobox)
        hbox.addWidget(self._add_roi_btn)
        hbox.addWidget(self._clr_roi_btn)

        self.setLayout(hbox)

    def _draw(self):
        """Draw helper Objects (roi)."""
        if self.main_widget.quad == 0 or len(self.rois) > 9:
            return
        roi = self._get_roi_type()
        roi.sigRegionChangeFinished.connect(self._set_size)
        self.current_roi = len(self.rois) + 1
        self.rois[self.current_roi] = roi
        self._update_spin_box(roi)
        self._set_colors()
        self._update_combo_box()
        self.draw_signal.emit()

    def _set_colors(self):
        """Set the colors of all roi"""
        for n, roi in self.rois.items():
            roi.setPen(QtGui.QPen(QtCore.Qt.gray, 0.002))
        roi = self.rois[self.current_roi]
        roi.setPen(QtGui.QPen(QtCore.Qt.red, 0.002))


    def _get_roi_type(self):
        """Return the correct roi type."""
        roi_txt = self._fit_type_combobox.currentText().lower()
        shape = self.main_widget.canvas.shape
        y, x = int(round(shape[0]/2, 0)), int(round(shape[1]/2, 0))
        if roi_txt == 'circle':
            return CircleROI(pos=(x-x//2, y-x//2), size=x//1)
        elif roi_txt == 'rectangle':
            return SquareROI(pos=(x-x//2, y-x//2), size=x//1)

    def _update_combo_box(self):
        """Add a new roi selection to the combo-box."""
        self._roi_combobox.addItem(str(self.current_roi))
        self._roi_combobox.setCurrentIndex(len(self.rois)-1)
        self._roi_combobox.setEnabled(True)
        self._roi_combobox.update()

    def _get_roi(self):
        num = int(self._roi_combobox.currentText())
        self.current_roi = num
        self._update_spin_box(self.rois[num])
        self._set_colors()

    def _update_spin_box(self, roi):
        """Add properties for a new circle."""
        self._spin_box.setEnabled(True)
        size = int(roi.size()[0])
        self._spin_box.setValue(size)

    def _update_roi(self):
        """Update the size and centre of circ. form button-click."""
        # Circles have only radii and
        roi = self.rois[self.current_roi]
        size = max(self._spin_box.value(), 0.0001)
        pos = roi.pos()
        centre = (pos[0] + round(roi.size()[0], 0)//2,
                  pos[1] + round(roi.size()[1], 0)//2)
        new_pos = (centre[0] - size//2,
                   centre[1] - size//2)
        roi.setPos(new_pos)
        roi.setSize((size, size))

    def _set_size(self):
        """Update spin_box if ROI is changed by hand."""
        roi = self.rois[self.current_roi]
        self._spin_box.setValue(int(roi.size()[0]))

    def _clear(self):
        """Delete all helper objects."""
        self.delete_signal.emit()
        self._roi_combobox.clear()
        self._roi_combobox.setEnabled(False)
        self._spin_box.setEnabled(False)
        self.current_roi = None
        self.rois = {}


class RunDataWidget(QtWidgets.QFrame):
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

    def __init__(self, run_dir, main_widget):
        """Create a btn for run-dir select and 2 spin boxes for train, pulse.

        Parameters:
            run_dir (str) : The default run directory
        """
        super().__init__()
        self.main_widget = main_widget
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


class GeometryWidget(QtWidgets.QFrame):
    """Define a Hbox containing a QLineEdit with a Label."""

    def __init__(self, main_widget, content):
        """Create nested widgets to select and save geometry files.

        Parameters:
            main_widget   : parent widget that creates this widget
            content (str) : pre filled content of the QLineEdit element
                            (dfault empty)
        """
        super().__init__()
        # Creat an hbox with a title, a field to add a filename and a button
        hbox = QtWidgets.QHBoxLayout()
        self.main_widget = main_widget

        self.detector_combobox = QtGui.QComboBox()
        self.detector_combobox.addItem('AGIPD')
        self.detector_combobox.addItem('LPD')
        self.detector_combobox.setCurrentIndex(0)
        label1 = QtGui.QLabel('Geometry File:')
        label1.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.file_sel = QtGui.QPushButton("Load")
        self.file_sel.clicked.connect(self._load)
        self.apply_btn = QtGui.QPushButton('Apply')
        self.apply_btn.setToolTip('Assemble Data')
        self.save_btn = QtGui.QPushButton('Save')
        self.save_btn.setToolTip('Save geometry')
        self.save_btn.setEnabled(False)
        hbox.addWidget(self.apply_btn)
        hbox.addWidget(self.save_btn)
        label2 = QtGui.QLabel('Detector:')
        label2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        hbox.addWidget(label2)
        hbox.addWidget(self.detector_combobox)
        hbox.addWidget(label1)
        self._geom_file_sel = QtGui.QLineEdit(content)
        self._geom_file_sel.setMaximumHeight(22)
        self._geom_file_sel.setAlignment(QtCore.Qt.AlignRight |
                                         QtCore.Qt.AlignVCenter)
        hbox.addWidget(self._geom_file_sel,5)


        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.addLayout(hbox)
        info = QtGui.QLabel(
            'Click on Quadrant to select; '
            'CTRL+arrow-keys to move them; '
            'Click "Assemble" to apply set changes')
        info.setToolTip('Click into the Image to select a Quadrant')
        vlayout.addWidget(info)

    def _load(self):
        """Open a dialog box to select a file."""
        DetectorHelper.load(self, self.det)

    @property
    def value(self):
        """Return the text of the QLinEdit element."""
        return self._geom_file_sel.text()

    def activate(self):
        """Change the content of buttons and QLineEdit elements."""
        self.save_btn.setEnabled(True)
    @property
    def det(self):
        """Set Detector from combobox."""
        return self.detector_combobox.currentText()


class DetectorHelper(QtGui.QDialog):
    """Setup widgets for quad. positions and geometry file selection."""

    def __init__(self, parent, det='LPD'):
        """Create a table element for quad selection and file selection.

        Parameters:
            window (QtGui.QMainWindow) : window object where widgets are
                                        going to be displayed
            parent (GeometryFileSelecter): main widget dealing with geometry
                                            selection
        Keywords:
            det (str) : Name to the detector (default LPD)
        """
        super().__init__()
        self.setWindowTitle('{} Geometry'.format(det))
        self.setFixedSize(240, 220)
        self.parent = parent
        self.det = det
        self.quad_table = QtGui.QTableWidget(4, 2)
        self.quad_table.setToolTip('Set the Quad-Pos in mm')
        self.quad_table.setHorizontalHeaderLabels(['Quad X-Pos', 'Quad Y-Pos'])
        self.quad_table.setVerticalHeaderLabels(['1', '2', '3', '4'])
        for n, quad_pos in enumerate(Defaults.fallback_quad_pos[det]):
            self.quad_table.setItem(
                n, 0, QtGui.QTableWidgetItem(str(quad_pos[0])))
            self.quad_table.setItem(
                n, 1, QtGui.QTableWidgetItem(str(quad_pos[1])))
        self.quad_table.move(0, 0)

        file_sel = QtGui.QPushButton('Select Geometry File')
        file_sel.setToolTip(
            'Select a Geometry File in xfel (hdf5) format.')
        file_sel.clicked.connect(self._get_files)

        ok_btn = QtGui.QPushButton('Ok')
        ok_btn.clicked.connect(self._apply)
        cancel_btn = QtGui.QPushButton('Cancel')
        cancel_btn.clicked.connect(self.cancel)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(ok_btn)
        hbox.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.quad_table)
        layout.addWidget(file_sel)
        layout.addLayout(hbox)
        self.setLayout(layout)
        self.show()

    @classmethod
    def load(cls, parent, det):
        """Handels loading the right configuration for a given detector."""
        if det == 'AGIPD':
            parent.quad_pos = None
            fname = cls.file_dialog(parent, Defaults.file_formats[det])
            parent.line.setText(fname)
        else:
            return cls(parent, det)

    def _get_files(self):
        fname = self.file_dialog(self.parent, Defaults.file_formats[det])
        self.parent.line.setText(fname)

    @staticmethod
    def file_dialog(parent, file_format):
        """File-selection dialogue to get the geometry file."""
        f_type = '{} file format ({})'.format(*file_format)
        fname, _ = QtGui.QFileDialog.getOpenFileName(parent,
                                                     'Load geometry file',
                                                     '.',
                                                     f_type)
        # Put the filename into the geometry file field of the main gui
        return fname

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
        Defaults.fallback_quad_pos[self.det] = quad_pos
        if not self.parent.value:
            _warning('You must Select a Geometry File')
            return
        self.destroy()

