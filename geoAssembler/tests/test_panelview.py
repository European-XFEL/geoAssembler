import os

from pyqtgraph import QtCore
from PyQt5.QtTest import QTest

from ..geometry import AGIPDGeometry


def test_defaults(calib):
    """Test default settings."""
    # Click add circle btn when no image is selected, check for circles
    test_calib = calib
    # QTest.mouseClick(test_calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    # assert len(test_calib.shapes) == 0

    #Test if geometry was correctly applied
    assert isinstance(test_calib.geom_obj, AGIPDGeometry)
    #Test if the preset levels are correct
    levels = tuple(test_calib.imv.getImageItem().levels)
    assert levels == (0, 10000)
    test_calib.close()

def test_preset(calib):
    """Test pre defined settings."""
    assert calib.run_selector.get_train_id() == 10000
    assert calib.run_selector._sel_method == None
    assert calib.run_selector._read_train == True

def test_load_geo(mock_directory_dialog, mock_open, start_dialog, geomfile):
    """Test the correct loading of geometry."""
    with mock_directory_dialog:
        QTest.mouseClick(start_dialog.button_open_run, QtCore.Qt.LeftButton)
    # Push the geometry load button and load a geo file via mock dialog
    QTest.mouseClick(start_dialog.rb_geom_cfel, QtCore.Qt.LeftButton)
    assert start_dialog.button_open_geom.isEnabled()
    with mock_open:
        QTest.mouseClick(start_dialog.button_open_geom, QtCore.Qt.LeftButton)
    # Check that the geo file was loaded
    assert start_dialog.edit_geom_path.text() == os.path.abspath(geomfile)
    assert isinstance(start_dialog.geometry(), AGIPDGeometry)

def test_circles(calib):
    """Test adding circles."""
    # Draw image
    QTest.mouseClick(calib.fit_widget.bt_clear_shape, QtCore.Qt.LeftButton)
    # Press the add circle button twice, check for num of circles
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    assert len(calib.shapes) == 2

def test_circle_properties(calib):
    """Test changeing properties of the circles."""
    # Add a circle
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    # Set the size of the spinbox to 800 and check for circ. radius
    calib.fit_widget.sb_shape_size.setValue(800)
    assert calib.current_shape.size()[0] == 800
    # Add another circle, select the first one and check for size again
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    # calib.bottom_buttons[1].click()
    assert calib.current_shape.size()[0] == 690

def test_shapes_dropdown(calib):
    """Test the circle selection buttons on the bottom."""
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    QTest.mouseClick(calib.fit_widget.bt_add_shape, QtCore.Qt.LeftButton)
    assert calib.fit_widget.cb_shape_number.currentText().startswith('Circle')
    QTest.mouseClick(calib.fit_widget.bt_clear_shape, QtCore.Qt.LeftButton)
    assert calib.fit_widget.cb_shape_number.count() == 0

def test_save_geo(mock_save, mock_warning, save_geo, calib):
    """Test saving the geom file."""
    assert calib.geom_selector.bt_save.isEnabled()
    with mock_save, mock_warning:
        QTest.mouseClick(calib.geom_selector.bt_save, QtCore.Qt.LeftButton)
    geom = AGIPDGeometry.from_crystfel_geom(save_geo)
    assert isinstance(geom, AGIPDGeometry)
