"""Qt Version of the detector geometry calibration."""
import logging

import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
from pyqtgraph.Qt import QtCore, QtGui

from .subwidgets import GeometryWidget, RunDataWidget, FitObjectWidget
from .objects import LogCapturer, LogDialog, warning

from ..defaults import DefaultGeometryConfig as Defaults
from .utils import get_icon


def run_gui(*args, **kwargs):
    """Run the Qt calibration windows in a QtGui application"""
    app = QtGui.QApplication([])
    calib = QtMainWidget(app, *args, **kwargs)
    logging.getLogger().addHandler(calib.log_capturer)
    app.exec_()
    app.closeAllWindows()


class QtMainWidget(QtGui.QMainWindow):
    """Qt-Version of the Calibration Class."""

    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    def __init__(self, app, run_dir=None, geofile=None, levels=None):
        """Display detector data and arrange panels.

        Parameters:
            run_dir : (str)
              Directory that contains the run data

            geofile : (str)
              The detector geometry file (CrystFEL or XFEL format)

            levels : (tuple)
              min/max values to be displayed (default: -1000)
        """
        super().__init__()

        self.setWindowTitle('GeoAssembler')
        self.setWindowIcon(get_icon('main_icon_64x64.png'))

        # pyqtgraph config
        pg.setConfigOptions(imageAxisOrder='row-major')
        pg.LabelItem(justify='right')

        self.geofile = geofile
        self.initial_levels = levels or [0, 10000]

        self.raw_data = None
        self.canvas = None
        self.rect = None
        self.quad = -1  # The selected quadrants (-1 none selected)
        self.is_displayed = False

        # This is hooked up to the Python logging system outside the class
        self.log_capturer = LogCapturer(self)

        # Create new image view
        self.imv = pg.ImageView()
        self.log.info('Creating main window')
        # Circle Points by Quadrant
        for action, keys in ((self._move_left, ('left', 'H')),
                             (self._move_up, ('up', 'K')),
                             (self._move_down, ('down', 'J')),
                             (self._move_right, ('right', 'L'))):
            for key in keys:
                shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+%s" % key),
                                           self.imv)
                shortcut.activated.connect(action)

        # circle manipulation other input dialogs go to the top
        self.fit_widget = FitObjectWidget(self, None)

        self.geom_selector = GeometryWidget(self, self.geofile)
        self.geom_selector.new_geometry.connect(self.assemble_draw)

        self.run_selector = RunDataWidget(self)
        self.run_selector.run_changed.connect(self.draw_reset_levels)
        self.run_selector.selection_changed.connect(self.assemble_draw)

        self.fit_widget.draw_shape_signal.connect(self._draw_shape)
        self.fit_widget.delete_shape_signal.connect(self._clear_shape)
        self.fit_widget.show_log_signal.connect(self.show_log)
        main_widget = QtGui.QWidget(self)
        self.setCentralWidget(main_widget)

        layout = QtGui.QGridLayout(main_widget)
        layout.addWidget(self.geom_selector,  0, 0)
        layout.addWidget(self.imv,  1, 0)
        layout.addWidget(self.run_selector, 2, 0)
        layout.addWidget(self.fit_widget, 3, 0)

        # So the main plot stretches forever
        layout.setRowStretch(1, 30)

        main_widget.setLayout(layout)

        # Add widgets to the layout in their proper positions
        self.showMaximized()
        self.frontview = False

        # If a run directory was already given, read it
        if run_dir:
            self.run_selector.read_rundir(run_dir)

    # Some properties coming up
    @property
    def shapes(self):
        """Get all shapes from fit widget."""
        return self.fit_widget.shapes

    @property
    def current_shape(self):
        """Get currently selected shape from fit widget."""
        return self.fit_widget.shapes[self.fit_widget.current_shape]

    @property
    def image(self):
        """Get the image fomr the pyqtgraph image object."""
        return self.imv.getView()

    @property
    def det(self):
        """Get the currently selected detector from the geometry widget."""
        return self.geom_selector.det

    @property
    def run_dir(self):
        """Get the currently set run directory from the run dir widget."""
        return self.run_selector.rundir

    @property
    def geom_file(self):
        """Get the current geometry file from the geom selector widget."""
        return self.geom_selector.geom_file

    @property
    def geom_obj(self):
        """Get the karabo data geometry object."""
        return self.geom_selector.get_geom()

    @QtCore.pyqtSlot()
    def draw_reset_levels(self):
        """Reset the image low/high levels to their initial values"""
        level_low, level_high = self.initial_levels
        self.assemble_draw()
        self.imv.setLevels(level_low, level_high)
        self.imv.setHistogramRange(min(level_low, 0), level_high * 2)
        self.imv.autoRange()

    @QtCore.pyqtSlot()
    def assemble_draw(self):
        """Read the geometry file and position all modules."""
        if self.run_dir is None:
            warning('Click the Run-dir button to select a run directory')
            self.log.error(' No data to assemble loaded ... ')
            return
        self.log.info(' Starting to assemble ... ')
        try:
            self.raw_data = self.run_selector.get()
        except ValueError:
            warning('No data in trainId, select a different trainId')
            return

        try:
            data, self.centre = self.geom_obj.position_all_modules(self.raw_data)
        except ValueError:
            warning('Error while applying geometry, check Detector Settings')
            return
        self.canvas = np.full(np.array(data.shape) + Defaults.canvas_margin,
                              np.nan)
        try:
            self.data, _ = self.geom_obj.position_all_modules(self.raw_data,
                                                              canvas=self.canvas.shape)
        except ValueError:
            warning('Error while applying geometry, check Detector Settings')
            return

        # Display the data and assign each frame a time value from 1.0 to 3.0
        self._draw_rect(None)
        self.redraw_image()

        self.imv.getImageItem().mouseClickEvent = self._click
        # Set a custom color map
        self.imv.setColorMap(pg.ColorMap(*zip(*Gradients['grey']['ticks'])))
        self.geom_selector.activate()
        self.quad = -1
        self.fit_widget.bt_add_shape.setEnabled(True)

    def redraw_image(self):
        img = self.data[::-1, ::self._flip_lr]
        self.imv.setImage(
            img, autoLevels=False, autoHistogramRange=False, autoRange=False
        )

    @property
    def _flip_lr(self):
        return -1 if self.frontview else 1

    @QtCore.pyqtSlot(int)
    def front_view_changed(self, new_state):
        self.frontview = (new_state == QtCore.Qt.Checked)
        self.redraw_image()
        if self.quad > 0:
            self._draw_rect(self.quad)

    def _move(self, d):
        """Move the quadrant."""
        quad = self.quad
        if quad <= 0:
            return
        inc = np.array(Defaults.direction[d])*np.array([self._flip_lr, 1])
        self.geom_obj.move_quad(quad, inc)
        self.data, self.centre =\
            self.geom_obj.position_all_modules(self.raw_data,
                                               canvas=self.canvas.shape)
        self._draw_rect(quad)
        self.redraw_image()

    def _draw_shape(self):
        """Add a fit object to the image."""
        self.image.addItem(self.current_shape)

    def _clear_shape(self):
        """Delete all helper objects."""
        for num in self.shapes:
            self.image.removeItem(self.shapes[num])

    def _get_quadrant(self, x, y):
        """Return the quadrant for a given set of coordinates."""
        x1, x2, x3 = 0, self.data.shape[-2]/2, self.data.shape[-2]
        y1, y2, y3 = 0, self.data.shape[-1]/2, self.data.shape[-1]

        self.bounding_boxes = {1: (x2, x3, y1, y2),
                               2: (x1, x2, y1, y2),
                               3: (x1, x2, y2, y3),
                               4: (x2, x3, y2, y3)}

        for quadrant, bbox in self.bounding_boxes.items():
            if bbox[0] <= x < bbox[1] and bbox[2] <= y < bbox[3]:
                return quadrant

    def _draw_rect(self, quad):
        """Draw rectangle around quadrant."""
        if self.rect is not None:
            self.imv.getView().removeItem(self.rect)

        if quad is None:
            return
        self.quad = quad
        P, dx, dy =\
            self.geom_obj.get_quad_corners(quad,
                                           np.array(self.data.shape, dtype='i')//2)
        pen = QtGui.QPen(QtCore.Qt.red, 0.002)
        Y, X = self.data.shape
        if self.frontview:
            P = (X - P[0] - dx, Y-P[1] - dy)
        else:
            P = (P[0], Y - P[1] - dy)
        self.rect = pg.RectROI(pos=P,
                               size=(dx, dy),
                               movable=False,
                               removable=False,
                               pen=pen,
                               invertible=False)
        self.rect.handleSize = 0
        self.imv.getView().addItem(self.rect)
        _ = [self.rect.removeHandle(handle)
             for handle in self.rect.getHandles()]

    def _click(self, event):
        """Event for mouse-click into ImageRegion."""
        if self.quad == 0:
            return
        event.accept()
        # Get postion of mouse-click and display it
        Y, X = self.data.shape
        pos = event.pos()
        x = int(pos.x())
        if self.frontview:
            x = X - x
        y = int(Y - pos.y())
        quad = self._get_quadrant(y, x)
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

    @QtCore.pyqtSlot()
    def show_log(self):
        LogDialog(self).open()
