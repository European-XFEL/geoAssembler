# Ring Based Detector Geometry Calibration Tool

This repository provides a tool to calibrate AGIPD detector geometry information

The tool can be seen as an alternative to the calibration mode of CrysFEL's
hdfsee. The calibration can either be based on a starting geometry that needs
to be refined or a completly new geometry. In this case the initial conditions
for the geometry are defined so that all modules are 29px apart from each other.

## Dependencies
The following python packages should be available:
 - numpy
 - cfelpyutils
 - pyqtgraph
 - matplotlib
 - ipywidgets

All packages should be available via the desy's anaconda3 module

## Usage (with real data):
### With existing geometry file
First lets suppose you already have a geometry file in CFEL format (*.geom*)
and the file is located in your home directory. You can now refine this
starting geometry:

```python
>>> import karabo_data as kd
>>> from geoAssembler import Calibrate
>>> runDir = '/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0273'
>>> crystFelGeo = '~/starter.geom'
>>> Run = kd.RunDirectory(run_dir)
>>> tId, train_data = Run.train_from_index(0)
>>> data = []
>>> for i in range(16):
      data.append(train_data[SPB_DET_AGIPD1M-1/DET/{}CH0:xtdf'.format(i)]['image.data'])
>>> vmin, vmax = 100, 1000
>>> Cal = Calibrate(data[0], crystFelGeo, vmin, vmax)
>>> Cal.centre

```
The qudrants are activated by clicking on them in the Image. They can be shifted
with the key combination CTRL+arrow-keys (i.e CTRL+up for moving the quadrant up)

You can save the geometry file by clicking on the save button.

## Testing:
Testing the implementation is done py pytest. To apply the test suite run 

```bash
$: pytest -v geoAssembler/tests
```
