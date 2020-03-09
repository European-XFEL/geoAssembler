import os.path as osp
from pyqtgraph.Qt import (QtCore, QtGui)

def get_icon(file_name):
    """Load icon from file."""
    pkg_dir = osp.dirname(osp.dirname(__file__))
    icon_path = osp.join(pkg_dir, 'icons')
    icon = QtGui.QIcon(osp.join(icon_path, file_name))
    return icon


def create_button(label, icon_type):
    """Create a button and set an icon to it."""
    icon_types = {
                   'circle': ('circle.png', 16),
                   'cancel': ('gtk-cancel.png', 16),
                   'clear': ('clear-all.png', 16),
                   'detector': ('main_icon_64x64.png', 16),
                   'draw': ('system-run.png', 16),
                   'load': ('file.png', 16),
                   'log': ('log.png', 16),
                   'main': ('main_icon_64x64.png', 64),
                   'ok': ('gtk-ok.png', 16),
                   'quads': ('quads.png', 16),
                   'shapes': ('shapes.png', 16),
                   'rundir': ('open.png', 16),
                   'save': ('save.png', 16),
                   'square': ('square.png', 16)
                   }

    icon_name, size = icon_types[icon_type]

    button = QtGui.QPushButton(label)
    button.setIcon(get_icon(icon_name))
    button.setIconSize(QtCore.QSize(size, size))

    return button