from geoAssembler.main import main
from testpath import assert_isfile

def test_template_notebook(tmp_path):
    main(['--notebook', '--nb_dir', str(tmp_path)])
    assert_isfile(tmp_path / 'GeoAssembler.ipynb')
