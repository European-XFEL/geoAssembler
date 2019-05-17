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

from .qt_subwidgets import GeometryWidget, RunDataWidget, FitObjectWidget

from ..defaults import DefaultGeometryConfig as Defaults
from ..gui_utils import (read_geometry, write_geometry)


log = logging.getLogger(__name__)
Slot = QtCore.pyqtSlot


def _warning(txt, title="Warning"):
    """Inform user about missing information."""
    msg_box = QtWidgets.QMessageBox()
    msg_box.setIcon(QtWidgets.QMessageBox.Information)
    msg_box.setText(txt)
    msg_box.setWindowTitle(title)
    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg_box.exec_()



class QtMainWidget:
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
        self.fit_widget = FitObjectWidget(self)
        self.geom_selector = GeometryWidget(self, geofile)
        self.run_selector = RunDataWidget(run_dir, self)
        self.layout.addWidget(self.geom_selector,  0, 0, 1, 9)
        # plot goes into the centre on right side, spanning 10 rows
        self.layout.addWidget(self.imv,  1, 0, 30, 10)
        # These buttons are on the top
        self.apply_btn = self.geom_selector.apply_btn
        self.apply_btn.clicked.connect(self._apply)
        self.save_btn = self.geom_selector.save_btn
        self.save_btn.clicked.connect(self._save_geom)
        self.load_geom_btn = self.geom_selector.file_sel
        # buttons go to the bottom
        gbox = QtGui.QGridLayout()
        self.quit_btn = QtGui.QPushButton('Quit')
        self.quit_btn.clicked.connect(self._destroy)
        gbox.addWidget(self.run_selector, 0, 0, 1, 15)
        gbox.addWidget(self.quit_btn, 1, 0, 1, 1)
        gbox.addWidget(self.fit_widget, 1, 1, 1, 1)
        self.layout.addLayout(gbox, 31, 0, 1, 10)
        self.fit_widget.draw_signal.connect(self._draw_roi)
        self.fit_widget.delete_signal.connect(self._clear_roi)

        pg.LabelItem(justify='right')
        self.window.setLayout(self.layout)
        self.is_displayed = False

    @property
    def run_selector_btn(self):
        return self.run_selector.run_sel

    @property
    def rois(self):
        return self.fit_widget.rois

    @property
    def current_roi(self):
        return self.fit_widget.rois[self.fit_widget.current_roi]

    @property
    def image(self):
        return self.imv.getView()

    @property
    def det(self):
        return self.geom_selector.det

    def _apply(self):
        """Read the geometry file and position all modules."""
        if self.run_selector.rundir is None:
            _warning('Click the Run-dir button to select a run directory')
            return
        if self.det != 'AGIPD' and not self.geom_selector.value:
            _warning('Click the load button to load a geometry file')
            return
        log.info(' Starting to assemble ... ')
        quad_pos = Defaults.fallback_quad_pos[self.det]
        self.geom_file = self.geom_selector.value
        self.geom = read_geometry(self.det, self.geom_selector.value, quad_pos)
        self.raw_data = self.run_selector.get()
        data, self.centre = self.geom.position_all_modules(self.raw_data)
        self.canvas = np.full(np.array(data.shape) + Defaults.canvas_margin,
                              np.nan)

        self.data, _ = self.geom.position_all_modules(self.raw_data,
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
        file_format = Defaults.file_formats[self.det]
        file_type = 'file format (*.{})'.format(*file_format)
        fname, _ = QtGui.QFileDialog.getSaveFileName(self.geom_selector,
                                                     'Save geometry file',
                                                     'geo_assembled.{}'.format(
                                                         file_format[-1]),
                                                     file_type)
        if fname:
            log.info(' Saving output to {}'.format(fname))
            try:
                os.remove(fname)
            except (FileNotFoundError, PermissionError):
                pass
            self.data, self.centre = self.geom.position_all_modules(
                self.raw_data)
            write_geometry(self.geom, fname, self.header)
            _warning('Geometry information saved to {}'.format(fname), 
                     title='Info')

    def _move(self, d):
        """Move the quadrant."""
        quad = self.quad
        if quad <= 0:
            return
        self.geom.move_quad(quad, np.array(Defaults.direction[d]))
        self.data, self.centre =\
            self.geom.position_all_modules(self.raw_data,
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

    def _destroy(self):
        """Destroy the window and exit."""
        QtCore.QCoreApplication.quit()

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
