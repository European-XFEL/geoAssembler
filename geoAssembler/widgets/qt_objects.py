
"""Definition of additionla qt helper objects."""

from itertools import product
import logging

import pyqtgraph as pg
from pyqtgraph.Qt import (QtCore, QtGui, QtWidgets)

from ..defaults import DefaultGeometryConfig as Defaults
from ..gui_utils import create_button


def warning(txt, title="Warning"):
    """Inform user about missing information."""
    msg_box = QtWidgets.QMessageBox()
    msg_box.setIcon(QtWidgets.QMessageBox.Information)
    msg_box.setText(txt)
    msg_box.setWindowTitle(title)
    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg_box.exec_()


class CircleROI(pg.EllipseROI):
    """Define a Elliptic ROI with a fixed aspect ratio (aka circle)."""

    def __init__(self, pos, size):
        """Create a circular region of interest.

        Parameters:
           pos (int) : centre of the circle
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


class SquareROI(pg.RectROI):
    """Define a rectangular ROI with a fixed aspect ratio (aka square)."""

    def __init__(self, pos, size):
        """Create a squared region of interest.

        Parameters:
           pos (int) : centre of the circle
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


class DetectorHelper(QtGui.QDialog):
    """Setup widgets for quad. positions and geometry file selection."""

    filename_set_signal = QtCore.pyqtSignal()
    header_set_signal = QtCore.pyqtSignal()

    def __init__(self, parent, header='', fname=''):
        """Create a table element for quad selection and file selection.

        Parameters:
            parent (GeometryFileSelecter): main widget dealing with geometry
                                           selection
        Keywords
            header (str) :  Additional informations added to the geometry file
                            (affects CFEL format only, Default '')

            fname (str) :  file name of the geometry file (Default '')
        """
        super().__init__()
        self.setFixedSize(260, 240)
        self.parent = parent
        self.header = header
        self.quad_pos = None
        self.setWindowTitle('{} Geometry'.format(self.det))
        self.quad_table = QtGui.QTableWidget(4, 2)
        self.quad_table.setToolTip('Set the Quadrant Posistions')
        self.quad_table.setHorizontalHeaderLabels(['Quad X-Pos', 'Quad Y-Pos'])
        self.quad_table.setVerticalHeaderLabels(['1', '2', '3', '4'])
        self.update_quad_table()
        file_sel = create_button('Load Geometry', 'load')
        file_sel.setToolTip('Select a Geometry File.')
        file_sel.clicked.connect(self._get_files)

        header_btn = create_button('Set header', 'quads')
        header_btn.setToolTip(
            'Add additional infromation to the Geometry File')
        header_btn.clicked.connect(self._set_header)

        ok_btn = create_button('Ok', 'ok')
        ok_btn.clicked.connect(self._apply)
        cancel_btn = create_button('Cancel', 'cancel')
        cancel_btn.clicked.connect(self.close)
        hbox1 = QtWidgets.QHBoxLayout()
        hbox1.addWidget(file_sel)
        hbox1.addWidget(header_btn)
        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addWidget(ok_btn)
        hbox2.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.quad_table)
        layout.addLayout(hbox1)
        layout.addLayout(hbox2)
        self.setLayout(layout)
        self.fname = fname

    def _get_files(self):
        """Read the geometry filename of from the dialog."""
        self.fname = self.file_dialog()
        if len(self.fname):
            self.filename_set_signal.emit()

    def update_quad_table(self):
        """Update the Qudrant table."""
        quad_pos = self.quad_pos or Defaults.fallback_quad_pos[self.det]
        for n, quad_pos in enumerate(quad_pos):
            self.quad_table.setItem(
                n, 0, QtGui.QTableWidgetItem(str(quad_pos[0])))
            self.quad_table.setItem(
                n, 1, QtGui.QTableWidgetItem(str(quad_pos[1])))
        self.quad_table.move(0, 0)

    @property
    def det(self):
        """Get the selected detector from the parent widget."""
        return self.parent.det

    def file_dialog(self):
        """File-selection dialogue to get the geometry file."""
        file_format = Defaults.file_formats[self.det]
        f_type = '{} file format (*.{})'.format(*file_format)
        fname, _ = QtGui.QFileDialog.getOpenFileName(self,
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
                warning('Table Elements must be Float')
                return
        if not self.fname and self.det != 'AGIPD':
            warning('You must Select a Geometry File')
            return
        self.quad_pos = quad_pos
        self.close()

    def _set_header(self):
        """Set the header of a geometry file."""
        self.header_win = QtGui.QDialog(self)
        self.header_win.setFixedSize(260, 240)
        self.header_win.setWindowTitle('Set Header')

        self._header_textbox = QtGui.QPlainTextEdit()
        self._header_textbox.insertPlainText(self.header)
        self._header_textbox.move(20, 20)
        self._header_textbox.resize(280, 280)

        ok_btn = create_button('Ok', 'ok')
        ok_btn.clicked.connect(self._over_write_header)
        cancel_btn = create_button('Cancel', 'cancel')
        cancel_btn.clicked.connect(self.header_win.close)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(ok_btn)
        hbox.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._header_textbox)
        layout.addLayout(hbox)
        self.header_win.setLayout(layout)
        self.header_win.show()

    def _over_write_header(self):
        """Overwrite the default header."""
        self.header = self._header_textbox.toPlainText()
        self.header_set_signal.emit()
        self.header_win.close()


class QLogger(logging.Handler):
    """Logger object connected python logging."""

    def __init__(self, main_widget):
        """Create a Dialog that displays the log connected to logging.

        Parameters:
            main_widget : Parent creating this dialog
        """
        super().__init__()
        self.win = QtGui.QDialog(main_widget)
        layout = QtWidgets.QGridLayout()

        self.widget = QtGui.QPlainTextEdit()
        self.widget.setReadOnly(True)
        layout.addWidget(self.widget, 0, 0, 10, 10)
        ok_btn = create_button('Ok', 'ok')
        ok_btn.clicked.connect(lambda: self.win.close())
        layout.addWidget(ok_btn, 11, 0, 1, 1)
        self.win.setLayout(layout)

    def emit(self, record):
        """Overload emit signal to write into text widget."""
        msg = self.format(record)
        self.widget.appendPlainText(msg)

    def write(self, m):
        """Overload write and do nothing."""
        pass
