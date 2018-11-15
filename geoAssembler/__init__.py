'''Call the calibration routine for ringbased calibration

   Author: bergeman'''

import os

from PyQt5 import QtGui

from .PanelView import Calibrate_Qt, Calibrate_Nb


def Calibrate(*args, **kwargs):
    '''Parameters:
            data (2d-array)  : File name of the geometry file, if none is given
                               (default) the image will be assembled with 29 Px
                               gaps between all modules.

            Keywords:
             geom (str/AGIPD_1MGeometry) :  The geometry file can either be
                                            an AGIPD_1MGeometry object or
                                            the filename to the geometry file
                                            in CFEL fromat
             vmin (int) : minimal value in the data array (default: -1000)
                          anything below this value will be clipped
             vmax (int) : maximum value in the data array (default: 5000)
                          anything above this value will be clipped
        '''

    if 'notebook' in os.environ['_'].lower() or 'jupyter' in os.environ['_'].lower():
        return Calibrate_Nb(*args, **kwargs)
    else:
        app = QtGui.QApplication([])
        Calib = Calibrate_Qt(*args, **kwargs)
        Calib.w.show()
        app.exec_()
        app.closeAllWindows()
        return Calib
