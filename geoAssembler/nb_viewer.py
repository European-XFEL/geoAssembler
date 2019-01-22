"""Jupyter Version of the detector geometry calibration
   for powder ring based calibration."""


import os
import logging

import numpy as np


from ipywidgets import widgets, Layout
from IPython.display import display
from matplotlib import pyplot as plt, cm
import matplotlib.patches as patches


from .geometry import AGIPD_1MGeometry
from .nb_tabs import CalibTab


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(os.path.basename(__file__))

#Fallback quad positions if no geometry file is given as a starting point:
FALLBACK_QUAD_POS = [(-540, 610), (-540, -15), (540, -143), (540, 482)]

#Definition of increments (INC) the quadrants should move to once a direction
#(u = up, d = down, r = right, l = left is given:
INC = 1
DIRECTION = {'u' : (-INC,    0),
             'd' : ( INC,    0),
             'r' : (   0,  INC),
             'l' : (   0, -INC)}

CANVAS_MARGIN = 300 #pixel, used as margin on each side of detector quadrants


class CalibrateNb:
    """Ipython Widget version of the Calibration Class."""

    def __init__(self, raw_data, geometry=None, vmin=None, vmax=None,
                 figsize=None, bg=None, **kwargs):
        """Display detector data and arrange panels.

        Parameters:
            raw_data (3d-array)  : Data array, containing detector image
                                   (nmodules, y, x)
        Keywords:
            geometry (str/AGIPD_1MGeometry)  : The geometry file can either be
                                               an AGIPD_1MGeometry object or
                                               the filename to the geometry
                                               file in CFEL fromat
            vmin (int) : minimal value in the data array (default: -1000)
                          anything below this value will be clipped
            vmax (int) : maximum value in the data array (default: 5000)
                          anything above this value will be clipped
            kwargs : additional keyword arguments that are parsed to matplotlib
        """
        self.data = raw_data
        self.im = None
        self.vmin = vmin or -1000
        self.vmax = vmax or 5000
        self.raw_data = np.clip(raw_data, self.vmin, self.vmax)
        self.figsize = figsize or (8, 8)
        self.bg = bg or 'w'
        self.circles = {}
        self.quad = None
        self.cmap = cm.get_cmap('gist_earth')
        try:
            self.cmap.set_bad(self.bg)
        except (ValueError, KeyError):
            self.bg = 'w'
        
        # Try to assemble the data (if geom is a AGIPD_Geometry class)
        if geometry is None:
            self.geom = AGIPD_1MGeometry.from_quad_positions(quad_pos=FALLBACK_QUAD_POS)
        elif isinstance(geometry, str):
            self.geom = AGIPD_1MGeometry.from_crystfel_geom(geometry)
        else:
            self.geom = geometry

        data, _ = self.geom.position_all_modules(self.raw_data)
        # Create a canvas
        self.canvas = np.full(np.array(data.shape) + CANVAS_MARGIN, np.nan)
        self._add_widgets()
        self.update_plot(plot_range=(self.vmin, self.vmax), **kwargs)
        self.rect = None
        self.sl = widgets.HBox([self.val_slider, self.cmap_sel])
        for wdg in (self.sl, self.tabs):
            display(wdg)

    @property
    def centre(self):
        """Return the centre of the image (beam)."""
        return self.geom.position_all_modules(self.raw_data)[1]

    def _draw_circle(self, r, num):
        """Draw circel of radius r and add it to the circle collection."""
        centre = self.geom.position_all_modules(self.raw_data,
                                                canvas=self.canvas.shape)[1]
        self.circles[num] = plt.Circle(centre[::-1], r,
                                       facecolor='none', edgecolor='r', lw=1)
        self.ax.add_artist(self.circles[num])

    def _draw_rect(self, pos):
        """Draw a rectangle around around a given quadrant."""
        try:
            # Remove the old one first if there is any
            self.rect.remove()
        except (AttributeError, ValueError):
            pass
        if pos is None:
            # If none then no new rectangle should be drawn
            return
        P, dx, dy =\
        self.geom.get_quad_corners(
                {1: 2, 2: 1, 3: 4, 4: 3}[pos],
                np.array(self.data.shape,dtype='i')//2)

        self.rect = patches.Rectangle(P,
                                      dx,
                                      dy,
                                      linewidth=1.5,
                                      edgecolor='r',
                                      facecolor='none')
        self.ax.add_patch(self.rect)
        self.update_plot(plot_range=None)

    def _add_tabs(self):
        """Add panel tabs."""
        self.tabs = widgets.Tab()
        self.tabs.children = (CalibTab(self),)
        for i, tab in enumerate(self.tabs.children):
            self.tabs.set_title(i, tab.title)

        self.tabs.children[0].selection.observe(self.tabs.children[0]._set_quad)

    def _add_widgets(self):
        """Add widgets to the layour."""
        # Slider for the max, vmin view
        self.val_slider = widgets.FloatRangeSlider(
            value=[self.vmin, self.vmax],
            min=self.vmin-np.fabs(self.vmax-self.vmin),
            max=self.vmax+np.fabs(self.vmax-self.vmin),
            step=0.1,
            description='Boost:',
            disabled=False,
            continuous_update=False,
            orientation='horizontal',
            readout=True,
            readout_format='d',
            layout=Layout(width='70%'))
        self.cmap_sel = widgets.Dropdown(options=['gist_earth',
                                                  'gist_ncar',
                                                  'bone',
                                                  'winter',
                                                  'summer',
                                                  'hot',
                                                  'copper',
                                                  'OrRd',
                                                  'coolwarm',
                                                  'CMRmap',
                                                  'jet'],
                                         value='gist_earth',
                                         description='Color Map:',
                                         disabled=False,
                                         layout=Layout(width='200px'))
        self.cmap_sel.observe(self._set_cmap)
        self.val_slider.observe(self._set_clim)
        self._add_tabs()

    def _set_clim(self, plot_range):
        """Update the color limits."""
        try:
            vmin, vmax= plot_range['new'][0], plot_range['new'][-1]
        except KeyError:
            return
        self.im.set_clim(vmin, vmax)
        self.cbar.update_bruteforce(self.im)
        cbar_ticks = np.linspace(vmin, vmax, 6)
        self.cbar.set_ticks(cbar_ticks)

    def _set_cmap(self, sel):
        """Update the colormap."""
        try:
            cmap_val = str(sel['new'])
        except KeyError:
            return

        try:
            cmap = cm.get_cmap(cmap_val)
            cmap.set_bad(self.bg)
            self.im.set_cmap(cmap)
        except ValueError:
            return

    def update_plot(self, plot_range=(100, 1500), cmap='gist_earth', **kwargs):
        """Update the plotted image."""
        # Update the image first
        self.data, centre =\
        self.geom.position_all_modules(self.raw_data, canvas=self.canvas.shape)
        cy, cx = centre
        if self.im is not None:
            if plot_range is not None:
                self.im.set_clim(*plot_range)
            else:
                self.im.set_array(self.data)
            h1, h2 = self.cent_cross
            h1.remove()
            h2.remove()
            h1 = self.ax.hlines(cy, cx-20, cx+20, colors='r', linewidths=1)
            h2 = self.ax.vlines(cx, cy-20, cy+20, colors='r', linewidths=1)
            self.cent_cross = (h1, h2)
        else:
            self.fig = plt.figure(figsize=self.figsize,
                                  clear=True, facecolor=self.bg)
            self.ax = self.fig.add_subplot(111)
            self.im = self.ax.imshow(
                self.data, vmin=plot_range[0], vmax=plot_range[-1],
                cmap=self.cmap, **kwargs)
            self.ax.set_xticks([]), self.ax.set_yticks([])
            h1 = self.ax.hlines(cy, cx-20, cx+20, colors='r', linewidths=1)
            h2 = self.ax.vlines(cx, cy-20, cy+20, colors='r', linewidths=1)
            self.cent_cross = (h1, h2)
            self.fig.subplots_adjust(bottom=0,
                                     top=1,
                                     hspace=0,
                                     wspace=0,
                                     right=1,
                                     left=0)

            self.cbar = self.fig.colorbar(self.im,
                                          shrink=0.8,
                                          anchor=(0.01, 0),
                                          pad=0.01,
                                          aspect=50)

            cbar_ticks = np.linspace(plot_range[0], plot_range[-1], 6)
            self.cbar.set_ticks(cbar_ticks)
