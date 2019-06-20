
"""Definitions of all widgets that go into the geoAssembler."""

from collections import namedtuple
import os
from os import path as op

import karabo_data as kd
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

from .qt_objects import (CircleShape, DetectorHelper, SquareShape, warning)

from ..defaults import DefaultGeometryConfig as Defaults
from ..gui_utils import (create_button, get_icon,
                         read_geometry, write_geometry)


Slot = QtCore.pyqtSlot
Signal = QtCore.pyqtSignal


class FitObjectWidget(QtWidgets.QFrame):
    """Define a Hbox containing a Spinbox with a Label."""

    draw_shape_signal = Signal()
    delete_shape_signal = Signal()
    quit_signal = Signal()
    show_log_signal = Signal()

    def __init__(self, main_widget, parent=None):
        """Add a spin box with a label to set radii.

        Parameters:
           main_widget : Parent widget
        """
        super().__init__(parent)
        ui_file = op.join(op.dirname(__file__), 'editor/fit_object.ui')
        uic.loadUi(ui_file, self)
        print(ui_file)

        self.main_widget = main_widget

        # Add a spinbox with title 'Size'
        self.sb_shape_size.valueChanged.connect(self._update_shape)
        self.cb_shape_number.currentIndexChanged.connect(self._get_shape)
        self.bt_add_shape.clicked.connect(self._draw)
        self.bt_add_shape.setIcon(get_icon('shapes.png'))
        self.bt_add_shape.setEnabled(False)
        self.bt_clear_shape.clicked.connect(self._clear)
        self.bt_clear_shape.setIcon(get_icon('clear-all.png'))
        self.bt_clear_shape.setEnabled(False)
        self.bt_quit.clicked.connect(self.quit_signal.emit)
        self.bt_show_log.clicked.connect(self.show_log_signal.emit)
        self.bt_quit.setIcon(get_icon('exit.png'))
        self.bt_show_log.setIcon(get_icon('log.png'))

        self.shapes = {}
        self.current_shape = None
        self.size = 690
        self.pen_size = 0.002
    def _draw(self):
        """Draw helper Objects (shape)."""
        if self.main_widget.quad == 0 or len(self.shapes) > 9:
            return
        shape = self._get_shape_type()
        shape.sigRegionChangeFinished.connect(self._set_size)
        self.current_shape = len(self.shapes) + 1
        self.shapes[self.current_shape] = shape
        self._update_spin_box(shape)
        self._set_colors()
        self._update_combo_box()
        self.draw_shape_signal.emit()

    def _set_colors(self):
        """Set the colors of all shape."""
        for n, shape in self.shapes.items():
            pen = QtGui.QPen(QtCore.Qt.gray, 0.002)
            pen.setWidthF(0.002)
            shape.setPen(pen)
        shape = self.shapes[self.current_shape]
        pen = QtGui.QPen(QtCore.Qt.red, 0.002)
        pen.setWidthF(0.002)
        shape.setPen(pen)

    def _get_shape_type(self):
        """Return the correct shape type."""
        shape_txt = self.cb_shape_type.currentText().lower()
        shape = self.main_widget.canvas.shape
        y, x = int(round(shape[0]/2, 0)), int(round(shape[1]/2, 0))
        if shape_txt == 'circle':
            return CircleShape(pos=(x-x//2, y-x//2), size=self.size)
        elif shape_txt == 'rectangle':
            return SquareShape(pos=(x-x//2, y-x//2), size=self.size)

    def _update_combo_box(self):
        """Add a new shape selection to the combo-box."""
        self.cb_shape_number.addItem(str(self.current_shape))
        self.cb_shape_number.setCurrentIndex(len(self.shapes)-1)
        self.cb_shape_number.setEnabled(True)
        self.bt_clear_shape.setEnabled(True)
        self.cb_shape_number.update()

    def _get_shape(self):
        """Get the current shape form the shape combobox."""
        try:
            num = int(self.cb_shape_number.currentText())
        except ValueError:
            # Shape is empty, do nothing
            return
        self.current_shape = num
        self._update_spin_box(self.shapes[num])
        self._set_colors()

    def _update_spin_box(self, shapes):
        """Add properties for a new circle."""
        self.sb_shape_size.setEnabled(True)
        shape = self.shapes[self.current_shape]
        size = int(shape.size()[0])
        self.sb_shape_size.setValue(size)

    def _update_shape(self):
        """Update the size and centre of circ. form button-click."""
        # Circles have only radii and
        shape = self.shapes[self.current_shape]
        size = max(self.sb_shape_size.value(), 0.0001)
        pos = shape.pos()
        centre = (pos[0] + round(shape.size()[0], 0)//2,
                  pos[1] + round(shape.size()[1], 0)//2)
        new_pos = (centre[0] - size//2,
                   centre[1] - size//2)
        shape.setPos(new_pos)
        pen_size = 0.002 * self.size/size
        pen = QtGui.QPen(QtCore.Qt.red, pen_size)

        pen.setWidthF(pen_size)
        shape.setSize((size, size))
        shape.setPen(pen)

    def _set_size(self):
        """Update spin_box if Shape is changed by hand."""
        shape = self.shapes[self.current_shape]
        self.sb_shape_size.setValue(int(shape.size()[0]))

    def _clear(self):
        """Delete all helper objects."""
        self.delete_shape_signal.emit()
        self.cb_shape_number.clear()
        self.cb_shape_number.setEnabled(False)
        self.bt_clear_shape.setEnabled(False)
        self.sb_shape_size.setEnabled(False)
        self.current_shape = None
        self.shapes = {}


class RunDataWidget(QtWidgets.QFrame):
    """A widget that defines run-directory, trainId and self.rb_pulse selection."""

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
    
    draw_img_signal = Signal()
    def __init__(self, run_dir, main_widget, parent=None):
        """Create a btn for run-dir select and 2 spin boxes for train, self.rb_pulse.

        Parameters:
            run_dir (str) : The default run directory
            main_widget : Parent widget
        """
        super().__init__(parent)

        ui_file = op.join(op.dirname(__file__), 'editor/run_data.ui')
        uic.loadUi(ui_file, self)

        self.main_widget = main_widget
        self.rundir = None
        self.tid = None
        self._img = None
        self.min_tid = None
        self.max_tid = None

        # Creat an hbox with a title, a field to add a filename and a button
        self.bt_select_run_dir.clicked.connect(self._sel_run)
        self.bt_select_run_dir.setIcon(get_icon('open.png'))
        self.sb_train_id.valueChanged.connect(self._update)

        self.rb_pulse.setChecked(False)
        self.rb_pulse.setEnabled(False)
        self.PULSE_SEL.button = self.rb_pulse
        self.rb_pulse.clicked.connect(
            lambda: self._set_sel_method(self.PULSE_SEL))

        self.rb_sum.setChecked(False)
        self.rb_sum.setEnabled(False)
        self.PULSE_SUM.button = self.rb_sum
        self.rb_sum.clicked.connect(
            lambda: self._set_sel_method(self.PULSE_SUM))

        self.rb_mean.setChecked(False)
        self.rb_mean.setEnabled(False)
        self.PULSE_MEAN.button = self.rb_mean
        self.rb_mean.clicked.connect(
            lambda: self._set_sel_method(self.PULSE_MEAN))

        self._sel = self.rb_pulse, self.rb_sum, self.rb_mean
        # If a run directory was already given read it
        if run_dir:
            self._read_rundir(run_dir)
        # Apply no selection method (sum, mean) to select self.rb_pulses by default
        self._sel_method = None
        self._read_train = True

        self.sb_pulse_id.valueChanged.connect(self.draw_img_signal.emit)

    def activate_spin_boxes(self):
        """Set min/max sizes of the spinbox according to trainId's and imgs."""
        self.sb_train_id.setMinimum(self.min_tid)
        self.sb_train_id.setMaximum(self.max_tid)
        self.sb_train_id.setValue(self.min_tid)
        self.sb_train_id.setEnabled(True)
        self.sb_pulse_id.setEnabled(True)
        for sel in (self.PULSE_SEL, self.PULSE_MEAN, self.PULSE_SUM):
            sel.button.setEnabled(True)
        self.PULSE_SEL.button.setChecked(True)
        self._update()

    def _set_sel_method(self, btn_prop):
        """Set the self.rb_pulse selection method (self.rb_pulse #, mean, sum)."""
        for sel in (self.PULSE_SEL, self.PULSE_MEAN, self.PULSE_SUM):
            sel.button.setChecked(False)
        btn_prop.button.setChecked(True)
        if btn_prop.num == 1:
            self.sb_pulse_id.setEnabled(True)
        else:
            self.sb_pulse_id.setEnabled(False)
        # Get the self.rb_pulse selection method
        self._sel_method = btn_prop.method

    def _update(self):
        """Update train_id and img."""
        self.tid = self.sb_train_id.value()
        self.det_info = self.rundir.detector_info(
            tuple(self.rundir.detector_sources)[0])
        self.sb_pulse_id.setMaximum(self.det_info['frames_per_train'] - 1)
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
        self.le_run_directory.setText(rfolder)
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
            try:
                img = kd.stack_detector_data(data, 'image.data')
            except ValueError:
                QtGui.QApplication.restoreOverrideCursor()
                self.main_widget.log.error('Bad train, skipping')
                raise ValueError('Bad train')
            # Probaply raw data with gain dimension - take the data dim
            if len(img.shape) == 5:
                img = img[:, 0] # TODO: confirm if first gain dim is data
            self._img = np.clip(img, 0, None)
            self._read_train = False
        if self._sel_method is None:
            # Read the selected train number
            self.rb_pulse_num = self.sb_pulse_id.value()
            raw_data = self._img[self.rb_pulse_num]
        else:
            raw_data = self._sel_method(self._img, axis=0)
        QtGui.QApplication.restoreOverrideCursor()
        return np.nan_to_num(raw_data)


class GeometryWidget(QtWidgets.QFrame):
    """Define a Hbox containing a QLineEdit with a Label."""

    draw_img_signal = Signal()

    def __init__(self, main_widget, content, parent=None):
        """Create nested widgets to select and save geometry files."""
        super().__init__(parent)
        ui_file = op.join(op.dirname(__file__), 'editor/geometry_editor.ui')
        uic.loadUi(ui_file, self)

        self.main_widget = main_widget
        self.header = main_widget.header

        for det in Defaults.detectors:
            self.cb_detectors.addItem(det)

        self.cb_detectors.currentIndexChanged.connect(
            self._update_quadpos)
        self.cb_detectors.setCurrentIndex(0)
        self.le_geometry_file.setText(content)
        self._geom_window = DetectorHelper(
            self.det, content, self.header)
        self._geom_window.filename_set_signal.connect(self._set_geom)
        self._geom_window.header_set_signal.connect(self._set_header)

        self.bt_load.clicked.connect(self._load)
        self.bt_apply.clicked.connect(self._create_gemetry_obj)
        self.bt_apply.setIcon(get_icon('system-run.png'))
        self.bt_load.setIcon(get_icon('file.png'))
        self.bt_save.clicked.connect(self._save_geometry_obj)
        self.bt_save.setIcon(get_icon('save.png'))

    def _update_quadpos(self):
        """Update the quad posistions."""
        self._geom_window.set_detector(self.det)
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
            write_geometry(self.geom, fname, self.header, self.main_widget.log)
            txt = ' Geometry information saved to {}'.format(fname)
            self.main_widget.log.info(txt)
            warning(txt, title='Info')

    @pyqtSlot()
    def _set_header(self):
        self.header = self._geom_window.header_text

    @pyqtSlot()
    def _set_geom(self):
        """Put the geometry file name into the text box."""
        self.le_geometry_file.setText(self._geom_window.filename)

    @property
    def geom_file(self):
        """Return the text of the QLinEdit element."""
        return self.le_geometry_file.text()

    def activate(self):
        """Change the content of buttons and QLineEdit elements."""
        self.bt_save.setEnabled(True)

    @property
    def det(self):
        """Set Detector from combobox."""
        return self.cb_detectors.currentText()

    def _create_gemetry_obj(self):
        """Create the karabo_data geometry object."""
        if self.det != 'AGIPD' and not self.geom_file:
            warning('Click the load button to load a geometry file')
            return
        quad_pos = self._geom_window.quad_pos
        self.geom = read_geometry(self.det, self.geom_file, quad_pos)
        self.draw_img_signal.emit()
