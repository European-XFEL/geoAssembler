"""Definitions of all widgets that go into the geoAssembler."""

import os
from os import path as op

from extra_data import RunDirectory, stack_detector_data
from extra_data.components import AGIPD1M, LPD1M, DSSC1M
import numpy as np
from PyQt5 import uic
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

from .objects import (CircleShape, DetectorHelper, SquareShape, warning)
from .utils import get_icon

from ..defaults import DefaultGeometryConfig as Defaults
from ..io_utils import read_geometry, write_geometry


Slot = QtCore.pyqtSlot
Signal = QtCore.pyqtSignal

# Map the names in the detector dropdown to data access classes
det_data_classes = {
    'AGIPD': AGIPD1M,
    'LPD': LPD1M,
    'DSSC': DSSC1M
}


class FitObjectWidget(QtWidgets.QFrame):
    """Define a Hbox containing a Spinbox with a Label."""

    draw_shape_signal = Signal()
    delete_shape_signal = Signal()
    show_log_signal = Signal()

    def __init__(self, main_widget, parent=None):
        """Add a spin box with a label to set radii.

        Parameters:
           main_widget : Parent widget
        """
        super().__init__(parent)
        ui_file = op.join(op.dirname(__file__), 'editor/fit_object.ui')
        uic.loadUi(ui_file, self)

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
        self.bt_show_log.clicked.connect(self.show_log_signal.emit)
        self.bt_show_log.setIcon(get_icon('log.png'))
        self.cb_front_view.stateChanged.connect(main_widget.front_view_changed)

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
        self._update_combo_box()
        self._set_colors()
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
        self.cb_shape_number.addItem(repr(self.shapes[self.current_shape]))
        for i in range(self.cb_shape_number.count()):
            # TODO: this seems to be a bug in QT. If only the last item is
            # activated all the others will get the same label.
            # Activate all to avoid that behavior
            self.cb_shape_number.setCurrentIndex(i)
        self.cb_shape_number.setEnabled(True)
        self.bt_clear_shape.setEnabled(True)

    def _get_shape(self):
        """Get the current shape form the shape combobox."""
        num = self.cb_shape_number.currentIndex()
        if num == -1:
            # Shape is empty, do nothing
            return
        self.current_shape = num + 1
        self._update_spin_box(self.shapes[self.current_shape])
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
        idx = self.cb_shape_number.currentIndex()
        txt = self.cb_shape_number.itemText(idx)
        if txt != repr(shape):
            self.cb_shape_number.setItemText(idx, repr(shape))
            #self.cb_shape_number.update()

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

    run_changed = Signal()
    selection_changed = Signal()

    def __init__(self, main_widget):
        """Create a btn for run-dir select and 2 spin boxes for train, self.rb_pulse.

        Parameters:
            main_widget : Parent widget
        """
        super().__init__(main_widget)

        ui_file = op.join(op.dirname(__file__), 'editor/run_data.ui')
        uic.loadUi(ui_file, self)

        self.main_widget = main_widget
        self.rundir = None
        self._cached_train_stack = (None, None)  # (tid, data)

        self.bt_select_run_dir.clicked.connect(self._sel_run)
        self.bt_select_run_dir.setIcon(get_icon('open.png'))

        for radio_btn in (self.rb_pulse, self.rb_mean):
            radio_btn.clicked.connect(self._set_sel_method)

        # Apply no selection method (sum, mean) to select self.rb_pulses by default
        self._sel_method = None
        self._read_train = True

        self.sb_train_id.valueChanged.connect(self.selection_changed.emit)
        self.sb_pulse_id.valueChanged.connect(self.selection_changed.emit)

    def get_train_id(self):
        return self.sb_train_id.value()

    def run_loaded(self):
        """Update the UI after a run is successfully loaded"""
        det = det_data_classes[self.main_widget.det](self.rundir, min_modules=9)
        self.sb_train_id.setMinimum(det.data.train_ids[0])
        self.sb_train_id.setMaximum(det.data.train_ids[-1])
        self.sb_train_id.setValue(det.data.train_ids[0])

        self.sb_pulse_id.setMaximum(det.frames_per_train - 1)

        # Enable spin boxes and radio buttons
        self.sb_train_id.setEnabled(True)
        self.sb_pulse_id.setEnabled(True)
        for radio_btn in (self.rb_pulse, self.rb_mean):
            radio_btn.setEnabled(True)

        self.run_changed.emit()

    @QtCore.pyqtSlot()
    def _set_sel_method(self):
        select_pulse = False
        if self.rb_mean.isChecked():
            self._sel_method = np.nanmean
        else:
            # Single Pulse
            self._sel_method = None
            select_pulse = True

        self.sb_pulse_id.setEnabled(select_pulse)
        self.selection_changed.emit()

    @QtCore.pyqtSlot()
    def _sel_run(self):
        """Select a run directory."""
        rfolder = QtGui.QFileDialog.getExistingDirectory(self,
                                                         'Select run directory')
        if rfolder:
            self.read_rundir(rfolder)

    def read_rundir(self, rfolder):
        """Read a selected run directory."""
        self.main_widget.log.info('Opening run directory {}'.format(rfolder))
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self.rundir = RunDirectory(rfolder)
        except Exception:
            QtGui.QApplication.restoreOverrideCursor()
            self.main_widget.log.info('Could not find HDF5-Files')
            warning('No HDF5-Files found', title='Info')
            return

        self.le_run_directory.setText(rfolder)
        self.run_loaded()
        QtGui.QApplication.restoreOverrideCursor()

    def get_train_stack(self):
        """Get a 4D array representing detector data in a train

        (pulses, modules, slow_scan, fast_scan)
        """
        tid = self.sb_train_id.value()
        if tid == self._cached_train_stack[0]:
            return self._cached_train_stack[1]

        self.main_widget.log.info('Reading train #: %s', tid)
        _, data = self.rundir.select('*/DET/*', 'image.data').train_from_id(tid)
        img = stack_detector_data(data, 'image.data')

        # Probaply raw data with gain dimension - take the data dim
        if len(img.shape) == 5:
            img = img[:, 0]  # TODO: confirm if first gain dim is data
        arr = np.clip(img, 0, None)

        self._cached_train_stack = (tid, arr)
        return arr


    def get(self):
        """Get the image of selected train & pulse (or mean/sum).

        Returns 3D array (modules, slow_scan, fast_scan)
        """
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            train_stack = self.get_train_stack()
            if self._sel_method is None:
                # Read the selected train number
                pulse_num = self.sb_pulse_id.value()
                raw_data = train_stack[pulse_num]
            else:
                raw_data = self._sel_method(train_stack, axis=0)

            return np.nan_to_num(raw_data)
        finally:
            QtGui.QApplication.restoreOverrideCursor()


class GeometryWidget(QtWidgets.QFrame):
    """Define a Hbox containing a QLineEdit with a Label."""

    new_geometry = Signal()

    def __init__(self, main_widget, filename):
        """Create nested widgets to select and save geometry files."""
        super().__init__(main_widget)
        ui_file = op.join(op.dirname(__file__), 'editor/geometry_editor.ui')
        uic.loadUi(ui_file, self)

        self.main_widget = main_widget
        self.geom = None

        for det in Defaults.detectors:
            self.cb_detectors.addItem(det)

        self.cb_detectors.currentIndexChanged.connect(
            self._update_quadpos)
        self.cb_detectors.setCurrentIndex(0)
        self.le_geometry_file.setText(filename)
        self._geom_window = DetectorHelper(self.det, filename, self)
        self._geom_window.filename_set_signal.connect(self._set_geom)

        self.bt_load.clicked.connect(self._load)
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
            write_geometry(self.geom, fname, self.main_widget.log)
            txt = ' Geometry information saved to {}'.format(fname)
            self.main_widget.log.info(txt)
            warning(txt, title='Info')

    @Slot()
    def _set_geom(self):
        """Put the geometry file name into the text box."""
        self.le_geometry_file.setText(self._geom_window.filename)
        self.geom = None
        self.new_geometry.emit()

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
        """Create the extra_geom geometry object."""
        if self.det != 'AGIPD' and not self.geom_file:
            warning('Click the load button to load a geometry file')
            return
        if self.geom is None:
            quad_pos = self._geom_window.quad_pos
            self.geom = read_geometry(self.det, self.geom_file, quad_pos)

    def get_geom(self):
        if self.geom is None:
            self._create_gemetry_obj()
        return self.geom
