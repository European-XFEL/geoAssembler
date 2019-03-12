import pytest
from tempfile import TemporaryDirectory

from .utils import create_test_directory

@pytest.fixture(scope='module')
def mock_run():
     with TemporaryDirectory() as td:
         create_test_directory(td)
         yield td


