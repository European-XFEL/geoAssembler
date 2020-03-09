
"""Jupyter Version of the detector geometry calibration."""

import logging

import numpy as np

from ipywidgets import widgets, Layout
from IPython.display import display
from matplotlib import pyplot as plt, cm
from matplotlib import transforms
from matplotlib.patches import Ellipse, Rectangle


from ..defaults import DefaultGeometryConfig as Defaults
from .tabs import ShapeTab, MaterialTab
from ..io_utils import read_geometry

log = logging.getLogger(__name__)

class CircleShape(Ellipse):
    """Circular Shape that supporting different aspect ratios."""
    type = 'circle'

    def __str__(self):
        return "Circle(%i)"%self.width

    def __init__(self, centre, diameter, ax, aspect, **kwargs):
        """Create an circle on top of an image with a given aspect ratio.

        Parameters
        -----------
        centre : float
        Centre of the circle (y, x)

        diameter : float
        Diameter of the circle

        ax : ax object
        Axes object that holding the plotting information

        aspect: float
        Aspect ratio (width / height)
        """

        a = diameter * aspect
        b = diameter
        self.aspect = aspect
        super().__init__(centre[::-1], a, b,
                         facecolor='none', edgecolor='r', lw=1)

    def set_size(self, diameter):
        """Increase/Decrease the diameter of the circle."""
        self.width = diameter * self.aspect
        self.height = diameter
        self.stale = True

    def set_angle(self, angle):
        """This is just a fake method don't do anything."""
        return

    def get_angle(self):
        """This has no effect, and always returns 0"""
        return 0

    def get_size(self):
        return self.width

class SquareShape(Rectangle):
    """Circular Shape that supporting different aspect ratios."""
    type = 'square'

    def __str__(self):
        return "Square(%i)"%self.get_width()

    def __init__(self, centre, size, ax, aspect, angle=0):
        """Create an square on top of an image with a given aspect ratio.

        Parameters
        -----------
        centre : float
        Centre point of the square (y, x)

        size : float
        size of the square

        ax : ax object
        Axes object that holding the plotting information

        aspect: float
        Aspect ratio (width / height)

        angle : float
        Rotation of the object
        """

        ts = ax.transData
        self.size = size
        self.centre = centre[::-1]
        self.aspect = aspect
        coords = ts.transform(self.centre)
        tr = transforms.Affine2D().rotate_deg_around(coords[0], coords[1], angle)
        t= ts + tr
        self.ax = ax
        self._angle = angle
        #Rotated rectangle patch
        super().__init__(self.centre, size*self.aspect, size,
                         facecolor='none', edgecolor='r', lw=1, transform=t)
        y = self.get_y() - size/2
        x = self.get_x() - size/2 * aspect
        self.set_y(y)
        self.set_x(x)

    def set_size(self, size):
        """Increase/Decrease the size of the squre."""
        w = self.get_width()
        h = self.get_height()
        self.set_width(size * self.aspect)
        self.set_height(size)
        dw = self.get_width() - w
        dh = self.get_height() - h

        self.set_y(self.get_y() - dh/2)
        self.set_x(self.get_x() - dw/2)
        self.stale = True

    def get_size(self):
        return self.get_width()

    def set_angle(self, angle):
        """Rotate the square by a given angle."""
        ts = self.ax.transData
        coords = ts.transform(self.centre)
        tr = transforms.Affine2D().rotate_deg_around(coords[0], coords[1], angle)
        t = ts + tr
        self.set_transform(t)
        self._angle = angle

    def get_angle(self):
        return self._angle

class MainWidget:
    """Ipython Widget version of the Calibration Class."""

    def __init__(self, raw_data, geometry=None, det='AGIPD', vmin=None,
                 vmax=None, figsize=None, bg=None, aspect=1, frontview=False, 
                 **kwargs):
        """Display detector data and arrange panels.

        Parameters:
            raw_data (3d-array)  : Data array, containing detector image
                                   (nmodules, y, x)
        Keywords:
            geometry : None/extra_geom geometry object
            The geometry file can either be an AGIPD_1MGeometry object or
            the filename to the geometry file in CFEL fromat

            det : str
            detector to be used (if geometry is None)

            vmin : int
            minimal value in the data array (default: -1000) anything below
            this value will be clipped

            vmax : int
            maximum value in the data array (default: 5000) anything above this
            value will be clipped

            figsize : tuple
            size of the figure

            bg : str
            background color of the image

            aspect (str, int) :
            aspect ratio width/height of the plot

            frontview (bool) :
            if false (default) then view is plotted as if you were looking into
            the beam

            kwargs :
            additional keyword arguments that are parsed to matplotlibs imshow
            function
        """
        self.data = raw_data
        Defaults.check_detector(det)
        self.im = None
        self.aspect = aspect
        self.vmin = vmin or np.nanmin(self.data)
        self.vmax = vmax or np.nanmax(self.data)
        self.raw_data = np.clip(raw_data, self.vmin, self.vmax)
        self.figsize = figsize or (8, 8)
        self.bg = bg or 'w'
        self.shapes = {}
        self.quad = None
        self.frontview = frontview
        self.cmap = cm.get_cmap(Defaults.cmaps[0])
        try:
            self.cmap.set_bad(self.bg)
        except (ValueError, KeyError):
            self.bg = 'w'

        # Try to assemble the data (if geom is None)
        if geometry is None:
            self.geom = read_geometry(det, None, None)
        else:
            self.geom = geometry

        data, _ = self.geom.position_all_modules(self.raw_data)
        # Create a canvas
        self.canvas = np.full(np.array(data.shape) + Defaults.canvas_margin,
                              np.nan)
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

    def draw_shape(self, shape_type, size, num, angle=0):
        """Draw helper object and add it to the shapess collection."""
        _, centre = self.geom.position_all_modules(self.raw_data,
                                                canvas=self.canvas.shape)
        if shape_type.lower() == 'circle':
            self.shapes[num] = CircleShape(centre, size,
                                       self.ax, self.aspect,
                                       angle=angle)
        else:
            self.shapes[num] = SquareShape(centre, size,
                                       self.ax, self.aspect,
                                       angle=angle)

        self.ax.add_patch(self.shapes[num])

    def draw_quad_bound(self, pos):
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
            self.geom.get_quad_corners(pos,
                np.array(self.data.shape, dtype='i')//2)

        self.rect = Rectangle(P, dx, dy, linewidth=1.5, edgecolor='r',
                              facecolor='none')
        self.ax.add_patch(self.rect)
        self.update_plot(plot_range=None)

    def _add_tabs(self):
        """Add panel tabs."""
        self.tabs = widgets.Tab()
        self.tabs.children = (ShapeTab(self), MaterialTab(self))
        for i, tab in enumerate(self.tabs.children):
            self.tabs.set_title(i, tab.title)

    def _add_widgets(self):
        """Add widgets to the layout."""
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
        self.cmap_sel = widgets.Dropdown(options=Defaults.cmaps,
                                         value=Defaults.cmaps[0],
                                         description='Color Map:',
                                         disabled=False,
                                         layout=Layout(width='200px'))
        self.cmap_sel.observe(self._set_cmap)
        self.val_slider.observe(self._set_clim)
        self._add_tabs()

    def _set_clim(self, plot_range):
        """Update the color limits."""
        try:
            vmin, vmax = plot_range['new'][0], plot_range['new'][-1]
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

    @property
    def quad_pos(self):
        return self.geom.quad_pos

    def update_plot(self, plot_range=(None, None),
                    cmap=Defaults.cmaps[0], **kwargs):
        """Update the plotted image."""
        self.data, cnt = self.geom.position_all_modules(self.raw_data,
                                                        self.canvas.shape)
        cy, cx = cnt
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
            self.ax = self.fig.add_subplot(111, aspect=self.aspect)
            self.im = self.ax.imshow(
                self.data, vmin=plot_range[0], vmax=plot_range[1],
                cmap=self.cmap, origin='lower', **kwargs)
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
            self.ax.set_aspect(self.aspect)
            if self.frontview:
                self.ax.invert_xaxis()
