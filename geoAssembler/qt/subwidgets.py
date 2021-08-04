"""Definitions of all widgets that go into the geoAssembler."""

import os
from os import path as op

from extra_data import RunDirectory, stack_detector_data
from extra_data.components import AGIPD1M, LPD1M, DSSC1M, identify_multimod_detectors
import numpy as np
from PyQt5 import uic
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

from .objects import (CircleShape, DetectorHelper, SquareShape, warning)
from .utils import get_icon

from ..defaults import DefaultGeometryConfig as Defaults
from ..geometry import GEOM_CLASSES
from ..io_utils import read_geometry, write_geometry


Slot = QtCore.pyqtSlot
Signal = QtCore.pyqtSignal

# Map the names in the detector dropdown to data access classes
det_data_classes = {
    'AGIPD': AGIPD1M,
    'LPD': LPD1M,
    'DSSC': DSSC1M
}
data_classes_to_names = {v: k for (k, v) in det_data_classes.items()}


class StartDialog(QtWidgets.QDialog):
    """Dialog to select run data, detector and initial geometry"""
    run_chosen = Signal(str)
    run_opened = Signal(str)
    xd_run = None  # An EXtra-data DataCollection object
    run_path = None
    _geom_from_geom_file = None

    def __init__(self, run_path=None):
        super().__init__()
        ui_file = op.join(op.dirname(__file__), 'editor/start.ui')
        uic.loadUi(ui_file, self)

        self.available_detectors = []

        self.button_open_run.clicked.connect(self._choose_run_path)
        self.combobox_detectors.currentIndexChanged.connect(self._select_detector)
        self.button_open_h5.clicked.connect(self._choose_h5_file)
        self.button_clear_h5.clicked.connect(self.edit_h5_path.clear)
        self.button_open_geom.clicked.connect(self._choose_geom_file)

        self.rb_geom_default.toggled.connect(self._geom_option_changed)
        self.rb_geom_quadpos.toggled.connect(self._geom_option_changed)
        self.rb_geom_cfel.toggled.connect(self._geom_option_changed)

        self.run_opened.connect(self.edit_run_path.setText)

        if run_path:
            self.load_run(run_path)

    @QtCore.pyqtSlot()
    def _choose_run_path(self):
        """Select a run directory."""
        rfolder = QtGui.QFileDialog.getExistingDirectory(
            self, 'Select run directory'
        )
        if rfolder:
            self.load_run(rfolder)

    def load_run(self, path):
        try:
            self.xd_run = RunDirectory(path)
        except Exception as e:
            self.label_status.setText(f"Error opening run: {e}")
            self.xd_run = None
            self.run_path = None
            self.group_geom_options.setEnabled(False)
            self.dialog_buttons.setEnabled(False)
            raise

        self.run_path = path
        self.run_opened.emit(path)

        self.available_detectors = sorted(identify_multimod_detectors(
            self.xd_run, clses=[AGIPD1M, LPD1M, DSSC1M]
        ))
        self.combobox_detectors.clear()
        self.combobox_detectors.addItems([
            f'{name} ({cls.__name__})' for (name, cls) in self.available_detectors
        ])
        self.combobox_detectors.setEnabled(True)
        self.combobox_detectors.setCurrentIndex(0)
        if not self.available_detectors:
            self.label_status.setText("No recognised detectors in run")
        else:
            self.label_status.setText(
                f"Loaded run with {len(self.available_detectors)} detectors"
            )

    def _have_detector(self, have=False, can_load_geom=True, can_load_h5=True):
        self.rb_geom_default.setEnabled(have)
        self.rb_geom_quadpos.setEnabled(have)
        self.rb_geom_cfel.setEnabled(have and can_load_geom)
        if have:
            self.rb_geom_default.setChecked(True)

            if can_load_geom:
                self.rb_geom_cfel.setText("&CrystFEL format geometry (.geom)")
            else:
                self.rb_geom_cfel.setText(
                    "CrystFEL format geometry (not supported for this detector)"
                )

            if can_load_h5:
                self.label_h5_geom.setText("With HDF5 geometry (optional):")
            else:
                self.label_h5_geom.setText(
                    "With HDF5 geometry (not supported for this detector):"
                )

        self._have_geometry(have)

    @QtCore.pyqtSlot()
    def _select_detector(self, index=-1):
        """Update widgets when detector dropdown changes"""
        # The signal seems to send index=-1 even when a real selection is made.
        # Retrieve currentIndex instead:
        index = self.combobox_detectors.currentIndex()
        if index == -1:
            self._have_detector(False)
            return

        cls = self.available_detectors[index][1]
        det_type = data_classes_to_names[cls]
        self._have_detector(True,
            can_load_geom=(det_type != 'DSSC'),
            can_load_h5=(det_type != 'AGIPD'),
        )
        unit = Defaults.quad_pos_units[det_type]
        self.rb_geom_quadpos.setText(f"Specified quadrant positions ({unit})")
        self.populate_quadpos_table(Defaults.fallback_quad_pos[det_type])
        self.edit_h5_path.clear()

    def populate_quadpos_table(self, quad_pos):
        """Fill the Quadrant positions table."""
        def numeric_table_item(val):
            # https://stackoverflow.com/a/37623147/434217
            item = QtGui.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, val)
            return item

        for n, (quad_x, quad_y) in enumerate(quad_pos):
            self.tb_quadrants.setItem(n, 0, numeric_table_item(quad_x))
            self.tb_quadrants.setItem(n, 1, numeric_table_item(quad_y))
        self.tb_quadrants.move(0, 0)

    def quadpos_from_table(self):
        return [(
            self.tb_quadrants.item(i, 0).data(QtCore.Qt.EditRole),
            self.tb_quadrants.item(i, 1).data(QtCore.Qt.EditRole),
        ) for i in range(4)]

    def _choose_h5_file(self):
        path, _ = QtGui.QFileDialog.getOpenFileName(
            self, filter="EuXFEL HDF5 geometry (*.h5)"
        )
        if path:
            det_type = self.selected_detector_type
            try:
                # Load the file to check it's valid for this detector
                geom_cls = GEOM_CLASSES[det_type]
                quadpos = Defaults.fallback_quad_pos[det_type]
                geom_cls.from_h5_file_and_quad_positions(path, quadpos)
            except Exception as e:
                self.label_status.setText(f"Error loading geometry from HDF5: {e}")
            else:
                self.edit_h5_path.setText(path)

    @property
    def selected_detector(self):
        index = self.combobox_detectors.currentIndex()
        return self.available_detectors[index]

    @property
    def selected_detector_type(self):
        _, data_cls = self.selected_detector
        return data_classes_to_names[data_cls]

    def _choose_geom_file(self):
        path, _ = QtGui.QFileDialog.getOpenFileName(
            self, filter="CrystFEL geometry (*.geom)"
        )
        try:
            geom_cls = GEOM_CLASSES[self.selected_detector_type]
            geom = geom_cls.from_crystfel_geom(path)
        except Exception as e:
            self.label_status.setText(f"Error loading geometry file: {e}")
            self._geom_from_geom_file = None
            self._have_geometry(False)
            raise

        self._geom_from_geom_file = geom
        self._have_geometry(True)

    def _have_geometry(self, have=False):
        self.dialog_buttons.setEnabled(have)

    def _geom_option_changed(self, _checked):
        if self.rb_geom_cfel.isChecked():
            self._have_geometry(self._geom_from_geom_file is not None)
        else:
            self._have_geometry(True)

        if (
                self.rb_geom_quadpos.isChecked()
                and self.selected_detector_type != 'AGIPD'
        ):
            self.button_open_h5.setEnabled(True)
            self.button_clear_h5.setEnabled(True)
        else:
            self.button_open_h5.setEnabled(False)
            self.button_clear_h5.setEnabled(False)

    def geometry(self):
        """Make a geometry object from the information in the dialog"""
        if self.rb_geom_cfel.isChecked():
            return self._geom_from_geom_file
        else:
            det_type = self.selected_detector_type
            geom_cls = GEOM_CLASSES[det_type]

            if self.rb_geom_quadpos.isChecked():
                quadpos = self.quadpos_from_table()
                h5_path = self.edit_h5_path.text()
                if h5_path:
                    return geom_cls.from_h5_file_and_quad_positions(h5_path, quadpos)
            else:  # rb_geom_default
                quadpos = Defaults.fallback_quad_pos[det_type]

            return geom_cls.from_quad_positions(quadpos)

class FitObjectWidget(QtWidgets.QFrame):
    """Define a Hbox containing a Spinbox with a Label."""

    draw_shape_signal = Signal()
    delete_shape_signal = Signal()
    show_log_signal = Signal()

    def __init__(self, main_widget):
        """Add a spin box with a label to set radii.

        Parameters:
           main_widget : Parent widget
        """
        super().__init__(parent=main_widget)
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
        y, x = self.main_widget.centre
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

    selection_changed = Signal()

    def __init__(self, main_widget, rundir, run_path):
        """Create a btn for run-dir select and 2 spin boxes for train, self.rb_pulse.

        Parameters:
            main_widget : Parent widget
        """
        super().__init__(main_widget)

        ui_file = op.join(op.dirname(__file__), 'editor/run_data.ui')
        uic.loadUi(ui_file, self)

        self.main_widget = main_widget
        self.rundir = rundir
        self._cached_train_stack = (None, None)  # (tid, data)

        # self.bt_select_run_dir.clicked.connect(self._sel_run)
        # self.bt_select_run_dir.setIcon(get_icon('open.png'))

        for radio_btn in (self.rb_pulse, self.rb_mean):
            radio_btn.clicked.connect(self._set_sel_method)

        # Apply no selection method (sum, mean) to select self.rb_pulses by default
        self._sel_method = None
        self._read_train = True

        self.sb_train_id.valueChanged.connect(self.selection_changed.emit)
        self.sb_pulse_id.valueChanged.connect(self.selection_changed.emit)

        if rundir is not None:
            self.run_loaded()
        if run_path is not None:
            self.le_run_directory.setText(run_path)

    def get_train_id(self):
        return self.sb_train_id.value()

    def run_loaded(self):
        """Update the UI after a run is successfully loaded"""
        det = det_data_classes[self.main_widget.det_type](self.rundir, min_modules=9)
        self.sb_train_id.setMinimum(det.data.train_ids[0])
        self.sb_train_id.setMaximum(det.data.train_ids[-1])
        self.sb_train_id.setValue(det.data.train_ids[0])

        self.sb_pulse_id.setMaximum(int(det.frames_per_train) - 1)

        # Enable spin boxes and radio buttons
        self.sb_train_id.setEnabled(True)
        self.sb_pulse_id.setEnabled(True)
        for radio_btn in (self.rb_pulse, self.rb_mean):
            radio_btn.setEnabled(True)


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

    def __init__(self, main_widget, det_type='AGIPD'):
        """Create nested widgets to select and save geometry files."""
        super().__init__(main_widget)
        ui_file = op.join(op.dirname(__file__), 'editor/geometry_editor.ui')
        uic.loadUi(ui_file, self)

        self.main_widget = main_widget
        self.det_type = det_type

        self.bt_quad_pos.clicked.connect(self._show_quadpos)
        self.bt_save.clicked.connect(self._save_geometry_obj)
        self.bt_save.setIcon(get_icon('save.png'))

        self.label_geom.setText(f"{det_type} geometry")

    @property
    def geom(self):
        return self.main_widget.geom_obj

    def _show_quadpos(self):
        """Show the quad posistions."""
        geom_window = DetectorHelper(self.geom.quad_pos, self.det_type, self)
        geom_window.setWindowTitle('{} Geometry'.format(self.det_type))
        geom_window.show()

    def _save_geometry_obj(self):
        """Save the loaded geometry to file."""
        file_type = 'CrystFEL geometry (*.geom)'
        fname, _ = QtGui.QFileDialog.getSaveFileName(
            self, 'Save geometry file', f'{self.det_type}.geom', filter=file_type
        )
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
