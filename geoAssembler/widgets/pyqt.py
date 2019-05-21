"""Qt Version of the detector geometry calibration."""

import logging
from os import path as op

import numpy as np
import pyqtgraph as pg
from PyQt5 import uic
from PyQt5.QtWidgets import QHBoxLayout
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
from pyqtgraph.Qt import QtCore, QtGui

from .qt_subwidgets import GeometryWidget, RunDataWidget, FitObjectWidget
from .qt_objects import QLogger, warning

from ..defaults import DefaultGeometryConfig as Defaults
from ..gui_utils import create_button, get_icon


Slot = QtCore.pyqtSlot


class QtMainWidget(QtGui.QMainWindow):
    """Qt-Version of the Calibration Class."""

    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

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
        super().__init__()

        self.setWindowTitle('GeoAssembler')
        self.setWindowIcon(get_icon('main_icon_64x64.png'))

        # pyqtgraph config
        pg.setConfigOptions(imageAxisOrder='row-major')
        pg.LabelItem(justify='right')

        self.geofile = geofile
        self.levels = levels or [None, None]
        self.header = header or ''

        self.raw_data = None
        self.rect = None
        self.quad = -1  # The selected quadrants (-1 none selected)
        self.is_displayed = False
        q_logger = QLogger(self)
        self.log.addHandler(q_logger)

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
        self.geom_selector.draw_img_signal.connect(self._draw)

        self.run_selector = RunDataWidget(run_dir, self)

        self.fit_widget.draw_roi_signal.connect(self._draw_roi)
        self.fit_widget.delete_roi_signal.connect(self._clear_roi)

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

    # Some properties coming up
    @property
    def rois(self):
        """Get all rois from fit widget."""
        return self.fit_widget.rois

    @property
    def current_roi(self):
        """Get currently selected roi from fit widget."""
        return self.fit_widget.rois[self.fit_widget.current_roi]

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
        return self.geom_selector.geom

    def _draw(self):
        """Read the geometry file and position all modules."""
        if self.run_dir is None:
            warning('Click the Run-dir button to select a run directory')
            self.log.error(' No data to assemble loaded ... ')
            return
        self.log.info(' Starting to assemble ... ')
        self.raw_data = self.run_selector.get()
        data, self.centre = self.geom_obj.position_all_modules(self.raw_data)
        self.canvas = np.full(np.array(data.shape) + Defaults.canvas_margin,
                              np.nan)

        self.data, _ = self.geom_obj.position_all_modules(self.raw_data,
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
        self.fit_widget._add_roi_btn.setEnabled(True)

    def _move(self, d):
        """Move the quadrant."""
        quad = self.quad
        if quad <= 0:
            return
        self.geom_obj.move_quad(quad, np.array(Defaults.direction[d]))
        self.data, self.centre =\
            self.geom_obj.position_all_modules(self.raw_data,
                                               canvas=self.canvas.shape)
        self._draw_rect(quad)
        self.imv.getImageItem().updateImage(self.data)

    def _draw_roi(self):
        """Add a fit object to the image."""
        self.image.addItem(self.current_roi)

    def _clear_roi(self):
        """Delete all helper objects."""
        for num in self.rois:
            self.image.removeItem(self.rois[num])

    def _get_quadrant(self, y, x):
        """Return the quadrant for a given set of coordinates."""
        y1, y2, y3 = 0, self.data.shape[-1]/2, self.data.shape[-1]
        x1, x2, x3 = 0, self.data.shape[-2]/2, self.data.shape[-2]
        self.bounding_boxes = {1: (x2, x3, y2, y3),
                               2: (x1, x2, y2, y3),
                               3: (x1, x2, y1, y2),
                               4: (x2, x3, y1, y2)}
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
            self.geom_obj.get_quad_corners(quad,
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
        _ = [self.rect.removeHandle(handle)
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
