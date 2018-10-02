"""
Author: Bergemann
Creation date: September, 2018, 16:10 AM
Copyright (c) European XFEL GmbH Hamburg. All rights reserved.
"""

import numpy as np
import pandas as pd
import sys
import re
from itertools import product


def Test():
    '''
    Method that creates a simple data-set that fakes data from karabo-data

    Returns:
        dict-object : Karabo-data like image.data
    '''
    data_array = np.ones((64, 512, 128))
    return {source: {'image.data': i*data_array} for (i, source) in
            enumerate(Assemble._make_df()['Source'].values)}


class Assemble(object):
    ''' Class containing methods that apply a given detector geometry to
        manipulate detector images

        Methods
        -------
        apply_geo: Applies the detector geometry to the recorded image
        stack    : Applies no geometry modules are only stacked
    '''

    def __init__(self, df=None):
        '''The class has the following instances:

           df = pandas data frame holding geometry information

           The object object can be crated with or without a specified detector
           geometry information. Currently only CrystFel geometry file or pandas
           data frames (or cvs formats that can be read by pandas are supported).

           Default format (non-CrystFel is looks something like this:
                                         Source  Xoffset  Yoffset  FlipX  FlipY  rotate
           0    SPB_DET_AGIPD1M-1/DET/0CH0:xtdf        0      607   True   True       0
           1    SPB_DET_AGIPD1M-1/DET/1CH0:xtdf      157      607   True   True       0
           2    SPB_DET_AGIPD1M-1/DET/2CH0:xtdf      314      607   True   True       0
           3    SPB_DET_AGIPD1M-1/DET/3CH0:xtdf      471      608   True   True       0
           4    SPB_DET_AGIPD1M-1/DET/4CH0:xtdf      634      630   True   True       0
           5    SPB_DET_AGIPD1M-1/DET/5CH0:xtdf      792      630   True   True       0
           6    SPB_DET_AGIPD1M-1/DET/6CH0:xtdf      949      630   True   True       0
           7    SPB_DET_AGIPD1M-1/DET/7CH0:xtdf     1107      630   True   True       0
           8    SPB_DET_AGIPD1M-1/DET/8CH0:xtdf      634       21  False   True       0
           9    SPB_DET_AGIPD1M-1/DET/9CH0:xtdf      791       21  False   True       0
           10  SPB_DET_AGIPD1M-1/DET/10CH0:xtdf      948       22  False   True       0
           11  SPB_DET_AGIPD1M-1/DET/11CH0:xtdf     1106       22  False   True       0
           12  SPB_DET_AGIPD1M-1/DET/12CH0:xtdf        0        0  False   True       0
           13  SPB_DET_AGIPD1M-1/DET/13CH0:xtdf      157        1  False   True       0
           14  SPB_DET_AGIPD1M-1/DET/14CH0:xtdf      313        0  False   True       0
           15  SPB_DET_AGIPD1M-1/DET/15CH0:xtdf      470        1  False   True       0

           Keywords:
              df (str, or pandas.core.dataframe): geometry (file) information
                                                    [default : None]

           Example:
              >>> from Assembler import Assemble
              >>> import karabo_data as kd
              >>> run_dir = '/gpfs/exfel/exp/SPB/201830/p900022/proc/r0025'
              >>> geof = 'cyrstfel_geometry.geom'
              >>> Cryst= Assemble(geof)
              >>> for tId, data in kd.RunDirectory(run_dir).trains():
                      array = Crys.apply_geo(data)
                      print(array.shape)
                      break
             >>>
        '''
        # If no geometry is given use the standard one
        if df is None:
            self.__df = self._make_df()
            self.df = self.__set_df
        # If geometry is already a pandas data frame use that one an carry on
        elif type(df) == pd.core.frame.DataFrame:
            self.__df = df
            self.df = self.__set_df
        else:
            # Try reading the geometry file, if it's csv file read it with pandas
            try:
                self.__df = pd.read_csv(df)
                self.df = self.__set_df
            except Exception:
                # If it fails it's likely a CrystFel geometry file
                self.__df = self._make_df()  # Create a standard geometry that gets overwritten
                # as template
                self.df = self.__set_df
                # Read the CrystFel geometry information
                self.__from_crystfel(df)

    @staticmethod
    def _make_df():
        # This method creates a standard geometry, which can be overwritten later
        return pd.DataFrame({'Source': ['SPB_DET_AGIPD1M-1/DET/0CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/1CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/2CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/3CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/4CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/5CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/6CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/7CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/8CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/9CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/10CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/11CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/12CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/13CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/14CH0:xtdf',
                                        'SPB_DET_AGIPD1M-1/DET/15CH0:xtdf'],
                             'Xoffset': [0,  158,  316,  474,  662,
                                         820,  978, 1136,  712,  870, 1028,
                                         1186,   50,  208,  366,  524],
                             'Yoffset': [612, 612, 612, 612, 612, 612, 612,
                                         612,   0,   0,   0,   0,   0,
                                         0,   0,   0],
                             'FlipX': [True,  True,  True,  True,  True,
                                       True,  True,  True, False,  False,
                                       False, False, False, False, False,
                                       False],
                             'FlipY': [False, False, False, False, False,
                                       False, False, False, True,  True,
                                       True,  True,  True,  True,  True,
                                       True],
                             'rotate': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                        0, 0, 0, 0],
                             'Quadrant':[2, 2, 2, 2, 4, 4, 4, 4, 3, 3, 3, 3,
                                         1, 1, 1, 1]})


    @property
    def __set_df(self):
        # Update some useful information once the geometry data frame is set

        self.__offsetX = self.__df.Xoffset.values
        self.__offsetY = self.__df.Yoffset.values
        self.__flipX = self.__df.FlipX
        self.__flipY = self.__df.FlipY
        self.__rot = self.__df.rotate

        self.__minOffX = min(self.__offsetX)
        self.__maxOffX = max(self.__offsetX)
        self.__minOffY = min(self.__offsetY)
        self.__maxOffY = max(self.__offsetY)

        return self.__df

    def apply_geo(self, data, modules_only=False):
        ''' This method applies the geometry to the recorded detector image

        Parameters:
           data (dict) : karabo_data dict. Containing the detector information
                         of a given trainId.
        Keywords:
           modules_only (bool) : only for testing, assing each module image
                                 a unique number. This can be used to see where
                                 the modules are located
        Returns:
           Nd-array : numpy ND array for the image.data of the detector
        '''

        arr = None  # Output array
        self.__df = self.df
        self.df = self.__set_df
        for index, path in enumerate(self.df['Source'].values):
            d = np.squeeze(data[path]['image.data'])

            if arr is None:
                # Get data shapes and axis
                shape = list(d.shape)
                axis = list(range(len(shape)))
                s2 = axis[-1]
                s1 = axis[-2]
                axis[-1] = s1
                axis[-2] = s2
                dtype = d.dtype
                # Get the shapes of the Full Array
                shape[-1] -= int(self.__minOffX)
                shape[-1] += int(self.__maxOffX)
                shape[-2] -= int(self.__minOffY)
                shape[-2] += int(self.__maxOffY)
                # Create the output array
                arr = np.zeros(shape)*np.nan
            ox = int(self.__offsetY[index] - self.__minOffY)
            oy = int(self.__offsetX[index] - self.__minOffX)

            if self.__flipY[index]:
                d = np.flip(d, axis=-1)

            if self.__flipX[index]:
                d = np.flip(d, axis=-2)
            d = np.rot90(d, k=self.__rot[index]//90, axes=(-2, -1))

            if d.shape[-1] > arr.shape[-1]:
                arr = np.resize(arr, arr.shape[:-1]+[d.shape[-1]])

            if modules_only:
                arr[..., ox:ox+d.shape[-2], oy:oy+d.shape[-1]] = index
            else:
                arr[..., ox:ox+d.shape[-2], oy:oy+d.shape[-1]] = d

        # return arr
        arr = arr.astype(dtype)[..., ::-1]
        arr = np.transpose(arr, axis)
        return arr.astype(dtype)[..., ::-1]

    def stack(self, data, modules_only=False):
        ''' This method only stacks the detector modules into an array without
            applying any geometry

        Parameters:
           data (dict) : karabo_data dict. Containing the detector information
                         of a given trainId.
        Keywords:
           modules_only (bool) : only for testing, assing each module image
                                 a unique number. This can be used to see where
                                 the modules are located
        Returns:
           Nd-array : numpy ND array for the image.data of the detector
        '''

        Yoffset=[542, 542, 542, 542, 542, 542, 542, 542, 0, 0, 0, 0, 0, 0, 0, 0]
        Xoffset=[   0,  158,  316,  474,  632,  790,  948, 1106, 632,  790,  948,
             1106, 0, 158, 316, 474]
        self.__df = pd.DataFrame({'Source':self.df.Source, 'Xoffset':Xoffset, 
            'Yoffset':Yoffset, 'FlipX':self.df.FlipX, 'FlipY':self.df.FlipY,
            'rotate':self.df.rotate, 'Quadrant':self.df.Quadrant},
             index=self.df.index)

        self.df = self.__set_df
        return self.apply_geo(data, modules_only)#[...,80:,70:]
        arr = None  # Output array
        for index, path in enumerate(self.df['Source'].values):
            d = np.squeeze(data[path]['image.data'])
            M={0:(0,1), 1:(1,1), 2:(2,1), 3:(3,1), 4:(4,1), 5:(5,1), 6:(6,1),
               7:(7,1), 12:(0,0), 13:(1,0), 14:(2,0), 15:(3,0), 8:(4,0), 9:(5,0),
               10:(6,0), 11:(7,0)}

            if arr is None:
                shape = list(d.shape)
                # Check for 4D or 3D shapes
                shapey,shapex = shape[-1], shape[0]
                if len(shape) > 3:
                    shape = shape[:-2]+shape[-2:]
                    newshape = shape[:-2] + [2*shape[-2]] + [8*shape[-1]]
                elif len(shape) == 3:
                    newshape = [shape[0], 2*shape[-2], 8*shape[-1]]
                    shape = [shape[0]]+shape[-2:]
                else:
                    newshape = [2*shape[-2], 8*shape[-1]]
                    shape = [shape[0], shape[1]]

                arr = np.zeros(newshape)
            posy, posx = M[index]
            if self.__flipY[index]:
                d = np.flip(d, axis=-1)

            if self.__flipX[index]:
                d = np.flip(d, axis=-2)
            d = np.rot90(d, k=self.__rot[index]//90, axes=(-2, -1))
            ix=posx*shapex
            iy=posy*shapey
            if modules_only:
                arr[...,iy:iy+shapey, ix:ix+shapex] = index
            else:
                arr[...,iy:iy+shapey, ix:ix+shapex] = d.T

        return arr#.reshape(*newshape)

    def __from_crystfel(self, filename):
        '''
           This method read the detector geometry from a CrystFel geometry file
           and translates int into a format that it can be understood by the
           apply_geo method'''
        with open(filename, 'r') as f:
            geomfile = f.read()
            # Crystfel geometry defines 16 panels with 8 elements in each panel
            geometry = np.array(list(product(range(16), range(8))))
            # x,y corner for the 16x8 entries
            corners = np.empty([len(geometry), 2])
            # Search for the according geometry information
            for jj in range(len(geometry)):
                panel, chip = geometry[jj]
                corner = [None, None]
                for ii, co in enumerate(('y', 'x')):
                    regex = re.compile('p%ia%i/corner_%s(.*)' %
                                       (panel, chip, co))
                    try:
                        corner[ii] = float(regex.findall(geomfile)[
                                           0].split('=')[-1].strip())
                    except (IndexError, AttributeError, ValueError):
                        sys.stderr.write(
                            '%i of panel %i is missing in the file' % (chip, panel))
                        raise RuntimeError('File Might be corrupted')
                corners[jj] = corner
        c = corners.round(0).astype('i')

        df = pd.DataFrame({'y': c[:, 1], 'x': c[:, 0], 'panel': geometry[:, 0],
                           'asics': geometry[:, -1]})
        # The reference frame is in the center of the detector, move it to the
        # Upper left corner
        df = self.__rearange(df)
        df.Yoffset = df.Yoffset.astype('i')
        df.Xoffset = df.Xoffset.astype('i')
        # Set the geometric information to the data frame
        self.__df = self.df
        self.__df[['Yoffset', 'Xoffset']] = df[['Yoffset', 'Xoffset']]
        self.df = self.__set_df

    @staticmethod
    def __rearange(df):
        '''Method that moves the center of reference from the detector center
           to the upper left corner
        '''
        data = {'panel': [], 'Xoffset': [], 'Yoffset': []}
        df.y = df.y.max() - df.y
        df.x += abs(df.x.min())

        for p in df.panel.unique():
            p_data = df.loc[df.panel == p]
            data['panel'].append(p)
            data['Xoffset'].append(p_data.x.min())
            data['Yoffset'].append(p_data.y.min())

        new_data = pd.DataFrame(data)#.sort_values('Xoffset')
        for i in range(8, 16):
            new_data.at[i, 'Xoffset'] += 128
        return new_data
