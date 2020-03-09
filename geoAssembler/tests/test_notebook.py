from extra_data import RunDirectory, stack_detector_data
import ipywidgets
import pytest

from geoAssembler import CalibrateNb
from geoAssembler.nb.notebook import CircleShape, SquareShape
from geoAssembler.nb.tabs import ShapeTab

@pytest.fixture(scope='session')
def agipd_frame(mock_run):
    run = RunDirectory(mock_run)
    print(run.instrument_sources)
    print(run.keys_for_source('SPB_DET_AGIPD1M-1/DET/10CH0:xtdf'))
    tid, train_data = run.select('*/DET/*', 'image.data').train_from_index(0)
    ary = stack_detector_data(train_data, 'image.data')
    return ary[0]

def test_create_widgets(agipd_frame):
    calib = CalibrateNb(agipd_frame, det='AGIPD')

    assert isinstance(calib.val_slider, ipywidgets.FloatRangeSlider)
    assert isinstance(calib.cmap_sel, ipywidgets.Dropdown)

def test_add_shapes(agipd_frame):
    calib = CalibrateNb(agipd_frame, det='AGIPD')
    assert len(calib.shapes) == 0

    shape_tab = calib.tabs.children[0]
    assert isinstance(shape_tab, ShapeTab)

    shape_tab.shape_type_dn.value = 'Circle'
    shape_tab.shape_btn.click()
    shape_tab.shape_type_dn.value = 'Square'
    shape_tab.shape_btn.click()

    assert len(calib.shapes) == 2
    assert isinstance(calib.shapes[0], CircleShape)
    assert isinstance(calib.shapes[1], SquareShape)

def test_move_quad(agipd_frame):
    calib = CalibrateNb(agipd_frame, det='AGIPD')

    shape_tab = calib.tabs.children[0]
    assert isinstance(shape_tab, ShapeTab)

    shape_tab.selection.value = '1'
    vert_widg, horz_widg = shape_tab.buttons[1:]
    assert isinstance(horz_widg, ipywidgets.BoundedIntText)
    assert isinstance(vert_widg, ipywidgets.BoundedIntText)

    q1_x_initial, q1_y_initial = calib.quad_pos.loc['q1']
    print("before:", calib.quad_pos.loc['q1'])

    horz_widg.value += 2
    vert_widg.value -= 3
    
    dh, dv = 2 * calib.geom.pixel_size, 3 * calib.geom.pixel_size
    print("after:", calib.quad_pos.loc['q1'])
    assert tuple(calib.quad_pos.loc['q1']) == (q1_x_initial + dh, q1_y_initial - dv)
