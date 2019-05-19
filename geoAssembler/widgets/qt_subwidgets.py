from collections import namedtuple
import os

import karabo_data as kd
import numpy as np
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

from .qt_objects import (CircleROI, DetectorHelper, SquareROI, warning)

from ..defaults import DefaultGeometryConfig as Defaults
from ..gui_utils import (create_button, get_icon, read_geometry, write_geometry)


Slot = QtCore.pyqtSlot
Signal = QtCore.pyqtSignal

class FitObjectWidget(QtWidgets.QFrame):
    """Define a Hbox containing a Spinbox with a Label."""

    draw_roi_signal = Signal()
    delete_roi_signal = Signal()
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
        self._add_roi_btn = create_button('Draw Helper Object', 'rois')
        self._add_roi_btn.setToolTip('Add Circles to the Image')
        self._add_roi_btn.setEnabled(False)
        self._add_roi_btn.clicked.connect(self._draw)

        # Add button to clear all fit helpers
        self._clr_roi_btn = create_button('Clear Helpers', 'clear')
        self._clr_roi_btn.setToolTip('Remove all fit Helpers')
        self._clr_roi_btn.setEnabled(False)
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
        self.draw_roi_signal.emit()

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
        self._clr_roi_btn.setEnabled(True)
        self._roi_combobox.update()

    def _get_roi(self):
        try:
            num = int(self._roi_combobox.currentText())
        except ValueError:
            # Roi is empty, do nothing
            return
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
        self.delete_roi_signal.emit()
        self._roi_combobox.clear()
        self._roi_combobox.setEnabled(False)
        self._clr_roi_btn.setEnabled(False)
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
        self.run_sel = create_button("Run-dir", "rundir")
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
        self.pulse_sel.setMaximum(self.det_info['frames_per_train'] - 1)
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
        self.main_widget.log.info('Opening run directory {}'.format(rfolder))
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
            self.main_widget.log.info('Reading train #: {}'.format(self.tid))
            _, data = self.rundir.train_from_id(self.tid, 
                                                devices=[('*DET*',
                                                          'image.data')])
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

    draw_img_signal = Signal()
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
        for det in Defaults.detectors:
            self.detector_combobox.addItem(det)
        self.detector_combobox.currentIndexChanged.connect(self._update_quadpos)
        self.detector_combobox.setCurrentIndex(0)
        label1 = QtGui.QLabel('Geometry File:')
        label1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.file_sel = create_button('Load', 'load')
        self.file_sel.setToolTip('Load/Set Detector Geometry')
        self.file_sel.clicked.connect(self._load)
        self.apply_btn = create_button('Apply', 'draw')
        self.apply_btn.setToolTip('Assemble Data')
        self.apply_btn.clicked.connect(self._create_gemetry_obj)
        self.save_btn = create_button('Save', 'save')
        self.save_btn.setToolTip('Save geometry')
        self.save_btn.clicked.connect(self._save_geometry_obj)
        self.save_btn.setEnabled(False)
        hbox.addWidget(self.file_sel)
        hbox.addWidget(self.apply_btn)
        hbox.addWidget(self.save_btn)
        label2 = QtGui.QLabel('Detector:')
        label2.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hbox.addWidget(label2)
        hbox.addWidget(self.detector_combobox)
        hbox.addWidget(label1)
        self._geom_file_sel = QtGui.QLineEdit(content)
        self._geom_file_sel.setMaximumHeight(22)
        self._geom_file_sel.setAlignment(QtCore.Qt.AlignLeft |
                                         QtCore.Qt.AlignVCenter)
        hbox.addWidget(self._geom_file_sel,5)
        self.header = main_widget.header

        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.addLayout(hbox)
        info = QtGui.QLabel(
            'Click "Apply Button" to draw image; '
            'Click on Quadrant to select then '
            'CTRL+arrow-keys to move them; ')
        info.setToolTip('Click into the Image to select a Quadrant')
        vlayout.addWidget(info)
        # Window for selecting geometry file and quad_pos
        self._geom_window = DetectorHelper(self, self.header, content)
        self._geom_window.filename_set_signal.connect(self._set_text)
        self._geom_window.header_set_signal.connect(self._set_header)

    def _update_quadpos(self):
        """Update the quad posistions"""
        self._geom_window.quad_pos = None
        self._geom_window.update_quad_table()
        self._geom_window.setWindowTitle('{} Geometry'.format(self.det))

    def _load(self):
        """Open a dialog box to select a file."""
        self._geom_window.show()

    def _save_geometry_obj(self):
        """Save the loaded geometry to file."""
        file_format = Defaults.file_formats[self.det][0]
        out_format = Defaults.file_formats[self.det][-1]
        file_type = '{} file format (*.{})'.format(file_format, out_format)
        fname, _ = QtGui.QFileDialog.getSaveFileName(self,
                                                     'Save geometry file',
                                                     'geo_assembled.{}'.format(
                                                         out_format),
                                                     file_type)
        if fname:
            self.main_widget.log.info(' Saving output to {}'.format(fname))
            try:
                os.remove(fname)
            except (FileNotFoundError, PermissionError):
                pass
            write_geometry(self.geom, fname, self.header)
            txt  = ' Geometry information saved to {}'.format(fname)
            self.main_widget.log.info(txt)
            warning(txt, title='Info')

    def _set_header(self):
        self.header = self._geom_window.header

    @property
    def geom_file(self):
        """Return the text of the QLinEdit element."""
        return self._geom_file_sel.text()

    def activate(self):
        """Change the content of buttons and QLineEdit elements."""
        self.save_btn.setEnabled(True)

    @property
    def det(self):
        """Set Detector from combobox."""
        return self.detector_combobox.currentText()

    def _set_text(self):
        self._geom_file_sel.setText(self._geom_window.fname)

    def _create_gemetry_obj(self):
        """Create the karabo_data geometry object."""
        if self.det != 'AGIPD' and not self.geom_file:
            warning('Click the load button to load a geometry file')
            return
        quad_pos = self._geom_window.quad_pos
        self.geom = read_geometry(self.det, self.geom_file, quad_pos)
        self.draw_img_signal.emit()
