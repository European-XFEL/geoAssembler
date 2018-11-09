# Geometry Calibration tool

This repository provides a tool to calibrate AGIPD detector geometry information

The tool can be seen as an alternative to the calibration mode of CrysFEL's
hdfsee. The calibration can either be based on a starting geometry that needs
to be refined or a completly new geometry. In this case the initial conditions
for the geometry are defined so that all modules are 29px apart from each other.



## Usage (with real data):
### With existing geometry file
First lets suppose you already have a geometry file in CFEL format (*.geom*)
and the file is located in your home directory. You can now refine this
starting geometry:

```python
>>> import karabo_data as kd
>>> from geoAssembler import PanelView as pv
>>> runDir = '/gpfs/exfel/exp/SPB/201830/p900022/proc/r0025/'
>>> crystFelGeo = '~/starter.geom'
>>> Run = kd.RunDirectory(run_dir)
>>> tId, train_data = Run.train_from_index(0)
>>> data = []
>>> for i in range(16):
      data.append(train_data[SPB_DET_AGIPD1M-1/DET/{}CH0:xtdf'.format(i)]['image.data'])
>>> vmin, vmax = 100, 1000
>>> view = pv(data[0], crystFelGeo, vmin, vmax)

```
The qudrants are activated by clicking on them 

You can save the geometry file 

If no geometry information is given a standard (crude) geometry arrangement from
the Karabo online preview device is applied:
```python
>>> from Assembler import Assemble
>>> A = Assemble()
>>> A.df
                              Source  Xoffset  Yoffset  FlipX  FlipY  rotate
0    SPB_DET_AGIPD1M-1/DET/0CH0:xtdf        0      612   True   True       0
1    SPB_DET_AGIPD1M-1/DET/1CH0:xtdf      158      612   True   True       0
2    SPB_DET_AGIPD1M-1/DET/2CH0:xtdf      316      612   True   True       0
3    SPB_DET_AGIPD1M-1/DET/3CH0:xtdf      474      612   True   True       0
4    SPB_DET_AGIPD1M-1/DET/4CH0:xtdf      662      612   True   True       0
5    SPB_DET_AGIPD1M-1/DET/5CH0:xtdf      820      612   True   True       0
6    SPB_DET_AGIPD1M-1/DET/6CH0:xtdf      978      612   True   True       0
7    SPB_DET_AGIPD1M-1/DET/7CH0:xtdf     1136      612   True   True       0
8    SPB_DET_AGIPD1M-1/DET/8CH0:xtdf      712        0  False   True       0
9    SPB_DET_AGIPD1M-1/DET/9CH0:xtdf      870        0  False   True       0
10  SPB_DET_AGIPD1M-1/DET/10CH0:xtdf     1028        0  False   True       0
11  SPB_DET_AGIPD1M-1/DET/11CH0:xtdf     1186        0  False   True       0
12  SPB_DET_AGIPD1M-1/DET/12CH0:xtdf       50        0  False   True       0
13  SPB_DET_AGIPD1M-1/DET/13CH0:xtdf      208        0  False   True       0
14  SPB_DET_AGIPD1M-1/DET/14CH0:xtdf      366        0  False   True       0
15  SPB_DET_AGIPD1M-1/DET/15CH0:xtdf      524        0  False   True       0
```

