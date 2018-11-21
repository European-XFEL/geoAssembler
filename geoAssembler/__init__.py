"""Call the calibration routine for ringbased calibration

Copyright (c) 2017, European X-Ray Free-Electron Laser Facility GmbH
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

You should have received a copy of the 3-Clause BSD License along with this
program. If not, see <https://opensource.org/licenses/BSD-3-Clause>


Author: bergeman
"""


__version__ = "0.0.1"

import os

from PyQt5 import QtGui

from .PanelView import Calibrate_Qt, Calibrate_Nb


def Calibrate(*args, **kwargs):
    """Parameters:
            raw_data (3d-array) : Data stored in panels, fs, ss (3d-array)

            Keywords:
             geofile (str/AGIPD_1MGeometry) :  The geometry file can either be
                                               an AGIPD_1MGeometry object or
                                               the filename to the geometry file
                                                in CFEL fromat. If None is given
                                                (default) the modules are
                                                positioned with 29px gaps.
             vmin (int) : minimal value in the data array (default: -1000)
                          anything below this value will be clipped
             vmax (int) : maximum value in the data array (default: 5000)
                          anything above this value will be clipped
        """
    if 'notebook' in os.environ['_'].lower() or 'jupyter' in os.environ['_'].lower():
        return Calibrate_Nb(*args, **kwargs)
    else:
        app = QtGui.QApplication([])
        Calib = Calibrate_Qt(*args, **kwargs)
        Calib.w.show()
        app.exec_()
        app.closeAllWindows()
        return Calib

