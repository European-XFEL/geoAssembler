"""Definition of additional qt helper objects."""
from collections import deque
import logging
from os import path as op

import pyqtgraph as pg
from PyQt5 import uic
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

from .utils import create_button


def warning(txt, title="Warning"):
    """Inform user about missing information."""
    msg_box = QtWidgets.QMessageBox()
    msg_box.setIcon(QtWidgets.QMessageBox.Information)
    msg_box.setText(txt)
    msg_box.setWindowTitle(title)
    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg_box.exec_()


class CircleShape(pg.EllipseROI):
    """Define a Elliptic Shape with a fixed aspect ratio (aka circle)."""

    def __init__(self, pos, size):
        """Create a circular region of interest.

        Parameters:
           pos (tuple) : centre of the circle (x, y)
           size (int) : diameter of the circle
        """
        pen = QtGui.QPen(QtCore.Qt.red, 0.002)
        pg.ROI.__init__(self,
                        pos=pos,
                        size=size,
                        removable=True,
                        movable=False,
                        invertible=False,
                        pen=pen)
        self.aspectLocked = True
        self.handleSize = 0
        _ = [self.removeHandle(handle) for handle in self.getHandles()]

    def __repr__(self):
        size = self.size()[0]
        return 'Circle(d:{})'.format(size)


class SquareShape(pg.RectROI):
    """Define a rectangular Shape with a fixed aspect ratio (aka square)."""

    def __init__(self, pos, size):
        """Create a squared region of interest.

        Parameters:
           pos (tuple) : centre of the circle (x, y)
           size (int) : diameter of the circle
        """
        pen = QtGui.QPen(QtCore.Qt.red, 0.002)
        pg.ROI.__init__(self,
                        pos=pos,
                        size=size,
                        removable=True,
                        movable=False,
                        invertible=False,
                        pen=pen)
        self.aspectLocked = True
        self.handleSize = 0
        _ = [self.removeHandle(handle) for handle in self.getHandles()]

    def __repr__(self):
        size = self.size()[0]
        return 'Square(a:{})'.format(size)


class DetectorHelper(QtGui.QDialog):
    """Show quadrant positions in a table"""

    filename_set_signal = QtCore.pyqtSignal()

    def __init__(self, quad_pos, det_type='AGIPD', parent=None):
        """Create a table element for quad selection and file selection.

        Parameters:
            det (str): the detector (AGIPD or LPD)

        Keywords
            fname (str) :  file name of the geometry file (Default '')
        """
        super().__init__(parent)

        ui_file = op.join(op.dirname(__file__), 'editor/load_detector.ui')
        uic.loadUi(ui_file, self)

        self.setWindowTitle('{} Geometry'.format(det_type))

        self.quad_pos = list(quad_pos.itertuples(index=False))

        self.populate_table()
        self.bt_copy_csv.clicked.connect(self._copy_csv)

    def populate_table(self):
        """Update the Qudrant table."""
        for n, quad_pos in enumerate(self.quad_pos):
            self.tb_quadrants.setItem(
                n, 0, QtGui.QTableWidgetItem(str(quad_pos[0])))
            self.tb_quadrants.setItem(
                n, 1, QtGui.QTableWidgetItem(str(quad_pos[1])))
        self.tb_quadrants.move(0, 0)

    def _copy_csv(self):
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText("\n".join(f"{x},{y}" for (x, y) in self.quad_pos))


class LogCapturer(logging.Handler, QtCore.QObject):
    """Emit Qt signal for Python logging, and store recent messages.
    """
    new_msg = QtCore.Signal(str)

    def __init__(self, parent, level=logging.NOTSET):
        QtCore.QObject.__init__(self, parent)
        logging.Handler.__init__(self, level)
        self.msg_buffer = deque(maxlen=500)

    def emit(self, record):
        msg = self.format(record)
        self.msg_buffer.append(msg)
        self.new_msg.emit(msg)


class LogDialog(QtGui.QDialog):
    """A Dialog that displays the log connected to logging.

    Parameters:
        main_widget : Parent creating this dialog
    """
    def __init__(self, main_window):
        super().__init__(parent=main_window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('GeoAssembler Logs')
        self.log_capturer = main_window.log_capturer

        self.text_area = QtGui.QPlainTextEdit(self)
        self.text_area.setReadOnly(True)
        self.ok_btn = create_button('Ok', 'ok')
        self.ok_btn.clicked.connect(self.close)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.text_area, 0, 0, 10, 10)
        layout.addWidget(self.ok_btn, 11, 0, 1, 1)
        self.setLayout(layout)

        for msg in self.log_capturer.msg_buffer:
            self.text_area.appendPlainText(msg)

        self.log_capturer.new_msg.connect(self.text_area.appendPlainText)
