"""Define the Widget tabs that are using in CalibrateNb."""

import os
import logging

from ipywidgets import widgets, Layout
from matplotlib import cm
import numpy as np
import pyFAI
import pyFAI.calibrant
from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
from scipy import constants

from ..calibrants import calibrants, celldir
log = logging.getLogger(__name__)


class ShapeTab(widgets.VBox):
    """Tab for geometry calibration with Shapes."""
    def __init__(self, parent):
        """Add tab to calibrate geometry to the main widget.

        Parameters:
           parent : CalibrateNb object
        """
        self.parent = parent
        self.title = 'Fit Objects'
        self.counts = 0

        self.selection = widgets.Dropdown(options=['None', '1', '2', '3', '4'],
                                          value='None',
                                          description='Quadrant',
                                          disabled=False)
        self.shape_btn = widgets.Button(description='Add ',
                                       disabled=False,
                                       button_style='',
                                       icon='',
                                       tooltip='Add Helper',
                                       layout=Layout(width='50px',
                                                     height='30px'))
        self.clr_btn = widgets.Button(description='Clear',
                                      tooltip='Remove All Shapes',
                                      disabled=False,
                                      button_style='',
                                      icon='',
                                      layout=Layout(width='50px',
                                                    height='30px'))
        self.shape_type_dn = widgets.Dropdown(options=['Circle', 'Square'],
                                            value='Circle',
                                            description='Type:',
                                            disabled=False,
                                            layout=Layout(width='170px',
                                                          height='30px'))

        self.shape_btn.on_click(self._add_shape)
        self.clr_btn.on_click(self._clear_shapes)
        self.buttons = [self.selection]
        self.current_shape = None
        self.shape_type = 'circle'
        self.row1 = widgets.HBox([self.selection])
        self.row2 = widgets.HBox([self.shape_type_dn, self.shape_btn, self.clr_btn])
        self.shape_type_dn.observe(self._set_shape_type, names='value')
        self.selection.observe(self._set_quad, names='value')
        super().__init__([self.row1, self.row2])

    def _set_shape_type(self, prop):
        """Set the shape type."""
        self.shape_type = prop['new'].lower()

    def _clear_shapes(self, *args):
        """Delete all shapes from the image."""
        for n, shape in self.parent.shapes.items():
            shape.remove()
        self.parent.shapes = {}
        self.row2 = widgets.HBox([self.shape_type_dn, self.shape_btn, self.clr_btn])
        self.children = [self.row1, self.row2]

    def _create_spin_boxes(self, size, angle):
        """Create  spin boxes for shape size and angle."""
        if self.parent.shapes[self.current_shape].type == 'circle':
            disabled = True
        else:
            disabled = False
        sb_size = widgets.BoundedFloatText(value=size,
                                           min=0,
                                           max=10000,
                                           step=1,
                                          disabled=False,
                                           description='Size',
                                           layout=Layout(width='200px',
                                                         height='30px'))
        sb_size.observe(self._set_size, names='value')

        sb_angle = widgets.BoundedFloatText(value=angle,
                                        min=0,
                                        max=360,
                                        step=0.01,
                                        disabled=disabled,
                                        description='Angle',
                                        layout=Layout(width='200px',
                                                      height='30px'))
        sb_angle.observe(self._set_angle, names='value')
        return [sb_size, sb_angle]

    @property
    def _shape_rpr(self):
        """Get the str of all shapes."""
        return ['{}:{}'.format(num, str(shape)) for (num, shape)
                in self.parent.shapes.items()]

    def _add_shape(self, *args):
        """Add a shape to the image."""
        num = len(self.parent.shapes)
        if num >= 10:  # Draw only 10 circles at max
            return
        size = 350
        for shape in self.parent.shapes.values():
            shape.set_edgecolor('gray')
        self.parent.draw_shape(self.shape_type, size, num)
        self.current_shape = num
        shapes = self._shape_rpr
        self.shape_drn = widgets.Dropdown(options=shapes,
                                        value=shapes[num],
                                        disabled=False,
                                        description='Sel.:',
                                        layout=Layout(width='220px',
                                                      height='30px'))
        self.shape_drn.observe(self._sel_shape, names='value')
        self.row2 = widgets.HBox([self.shape_type_dn, self.shape_btn, self.clr_btn,
                                  self.shape_drn] + self._create_spin_boxes(350, 0))
        self.children = [self.row1, self.row2]


    def _set_angle(self, prop):
        """Set the angle of the shape."""
        angle = prop['new']
        shape = self.parent.shapes[self.current_shape]
        shape.set_angle(angle)
        size = shape.get_size()
        shapes = self._shape_rpr
        self.shape_drn = widgets.Dropdown(options=shapes,
                                        value=shapes[self.current_shape],
                                        disabled=False,
                                        description='Sel.:',
                                        layout=Layout(width='220px',
                                                      height='30px'))

        self.shape_drn.observe(self._sel_shape, names='value')
        self.row2 = widgets.HBox([self.shape_type_dn, self.shape_btn, self.clr_btn,
                                  self.shape_drn] + self._create_spin_boxes(size, angle))
        self.children = [self.row1, self.row2]


    def _set_size(self, selection):
        """Set the shape size."""
        try:
            size = int(selection['new'])
        except TypeError:
            return

        shape = self.parent.shapes[self.current_shape]
        shape.set_size(size)
        angle = shape.get_angle()
        shapes = self._shape_rpr
        self.shape_drn = widgets.Dropdown(options=shapes,
                                        value=shapes[self.current_shape],
                                        disabled=False,
                                        description='Sel.:',
                                        layout=Layout(width='220px',
                                                      height='30px'))
        self.shape_drn.observe(self._sel_shape, names='value')
        self.row2 = widgets.HBox([self.shape_type_dn, self.shape_btn, self.clr_btn,
                                  self.shape_drn] + self._create_spin_boxes(size, angle))
        self.children = [self.row1, self.row2]



    def _sel_shape(self, selection):
        """Select-helper circles."""
        self.current_shape = int(selection['new'].split(':')[0])
        size = int(self.parent.shapes[self.current_shape].get_size())
        angle = int(self.parent.shapes[self.current_shape].get_angle())
        for num, shape in self.parent.shapes.items():
            if num != self.current_shape:
                shape.set_edgecolor('gray')
            else:
                shape.set_edgecolor('r')
        self.row2 = widgets.HBox([self.shape_type_dn, self.shape_btn, self.clr_btn,
                                  self.shape_drn]+self._create_spin_boxes(size, angle))
        self.children = [self.row1, self.row2]

    def _move_quadrants(self, pos):
        """Shift a quadrant."""
        d = pos['owner'].description.lower()[0]
        pn = int(pos['new'])
        po = int(pos['old'])
        delta = pn - po
        if d == 'h':
            pos = np.array((delta, 0))
            if self.parent.frontview:
                pos = -pos
        else:
            pos = np.array((0, delta))
        self.parent.geom.move_quad(self.parent.quad, pos)
        self.parent.draw_quad_bound(self.parent.quad)
        self.parent.update_plot(None)

    def _update_navi(self, pos):
        """Add navigation buttons."""
        posy_sel = widgets.BoundedIntText(value=0,
                                          min=-1000,
                                          max=1000,
                                          step=1,
                                          disabled=False,
                                          continuous_update=True,
                                          description='Horz.')
        posx_sel = widgets.BoundedIntText(value=0,
                                          min=-1000,
                                          max=1000,
                                          step=1,
                                          disabled=False,
                                          continuous_update=True,
                                          description='Vert.')
        posx_sel.observe(self._move_quadrants, names='value')
        posy_sel.observe(self._move_quadrants, names='value')

        if pos is None:
            self.buttons = [self.buttons[0]]

        elif len(self.buttons) == 1:
            self.buttons += [posx_sel, posy_sel]
        else:
            self.buttons[1] = posx_sel
            self.buttons[2] = posy_sel
        self.row1 = widgets.HBox(self.buttons)
        self.children = [self.row1, self.row2]

    def _set_quad(self, prop):
        """Select a quadrant."""
        try:
            pos = int(prop['new'])
        except ValueError:
            pos = 0
        try:
            self.parent.rect.remove()
        except (AttributeError, ValueError):
            pass

        if pos == 0:
            self._update_navi(None)
            self.parent.quad = None
            return
        self.parent.draw_quad_bound(pos)
        if pos != self.parent.quad:
            self._update_navi(pos)
        self.parent.quad = pos


class MaterialTab(widgets.VBox):
    """Calibrant Material Tab."""

    def __init__(self, parent):
        """Set all widgets for the tab.

        Parameters:
            parent (ipywidget) : The parent widget object embeding this tab
        """
        self.parent = parent
        self.title = 'Set Calibrant'
        self.alpha = 0.5  # The transparency value of the overlay
        self.clim = (0.5, 0.9)  # Standard clim (max alwys 1)
        self.img = None  # Image to be overlayed
        energy = 10e3  # [eV] Photon energy, default value can be overwirtten
        # Convert the energy to wave-length
        self.wave_length = self._energy2lambda(energy)
        self.calibrant = 'None'  # Calibrant material
        self.pxsize = 0.2 / 1000  # [mm] Standard detector pixel size
        self.cdist = 0.2  # [m] Standard probe distance
        # Get all calibrants defined in pyFAI
        self.calibrants = [self.calibrant] + calibrants
        # Calibrant selection
        self.calib_btn = widgets.Dropdown(options=self.calibrants,
                                          value='None',
                                          description='Calibrant', disabled=False,
                                          layout=Layout(width='250px', height='30px'))
        # Probe distance selection
        self.dist_btn = widgets.BoundedFloatText(value=self.cdist, min=0, max=10000,
                                                 layout=Layout(
                                                     width='150px', height='30px'),
                                                 step=0.01, disabled=False, description='Distance [m]')
        # Photon energy selection
        self.energy_btn = widgets.BoundedFloatText(value=energy, min=3000, max=100000,
                                                   layout=Layout(
                                                       width='200px', height='30px'),
                                                   step=1, disabled=False, description='Energy [eV]')
        # Pixel size selection
        self.pxsize_btn = widgets.BoundedFloatText(value=self.cdist, min=0, max=20,
                                                   layout=Layout(
                                                       width='150px', height='30px'),
                                                   step=0.01, disabled=False, description='Pixel Size [mm]')
        # Apply button to display the ring structure
        self.aply_btn = widgets.Button(description='Apply',
                                       disabled=False, button_style='', icon='',
                                       tooltip='Apply Material',
                                       layout=Layout(width='100px', height='30px'))
        # Clear button to delete overlay
        self.clr_btn = widgets.Button(description='Clear',
                                      tooltip='Do not show overlay',
                                      disabled=False, button_style='', icon='',
                                      layout=Layout(width='100px', height='30px'))
        # Set transparency value
        self.alpha_slider = widgets.FloatSlider(
            value=self.alpha,
            min=0,
            max=1,
            step=0.01,
            description='Transparancy:',
            orientation='horizontal',
            readout=True,
            readout_format='.2f',
            layout=Layout(width='40%'))
        # Set clim
        self.val_slider = widgets.FloatRangeSlider(
            value=self.clim,
            min=0,
            max=1,
            step=0.01,
            description='Range:',
            disabled=False,
            continuous_update=False,
            orientation='horizontal',
            readout=True,
            readout_format='.2f',
            layout=Layout(width='40%'))
        # Arange the buttons
        self.row1 = widgets.HBox(
            [self.calib_btn, self.dist_btn, self.energy_btn, self.pxsize_btn])
        self.row2 = widgets.HBox(
            [self.val_slider, self.alpha_slider, self.aply_btn, self.clr_btn])
        # Connect all methods to the buttons
        self.val_slider.observe(self._set_clim, names='value')
        self.alpha_slider.observe(self._set_alpha, names='value')
        self.clr_btn.on_click(self._clear_overlay)
        self.aply_btn.on_click(self._draw_overlay)
        self.calib_btn.observe(self._set_calibrant, names='value')
        self.pxsize_btn.observe(self._set_pxsize, names='value')
        self.energy_btn.observe(self._set_wavelength, names='value')
        self.dist_btn.observe(self._set_cdist, names='value')
        super(widgets.VBox, self).__init__([self.row1, self.row2])

    @staticmethod
    def _energy2lambda(energy):
        """Calc. wavelength from beam energy."""
        return constants.h * constants.c / (energy * constants.eV)

    def _set_cdist(self, prop):
        """Set the detector probe distance."""
        try:
            self.cdist = float(prop['new'])
        except TypeError:
            return

    def _set_pxsize(self, prop):
        """Set the detector pixel size."""
        try:
            self.pxsize = float(prop['new'])/1000.
        except TypeError:
            return

    def _set_wavelength(self, prop):
        """Set the wavelength (photon energy)."""
        try:
            energy = float(prop['new'])
        except TypeError:
            return
        # Convert energy to wavelength
        self.wave_length = self._energy2lambda(energy)

    def _set_calibrant(self, prop):
        """Set the calibrant material."""
        calib = prop['new']
        if isinstance(calib, str):
            self.calibrant = calib

    def _draw_overlay(self, *args):
        """Draw the ring structure with pyFAI."""
        if self.calibrant is 'None':
            return
        try:
            cal = pyFAI.calibrant.get_calibrant(self.calibrant)
            cal.set_wavelength(self.wave_length)
        except KeyError:
            cal_file = os.path.join(celldir, self.calibrant+'.D')
            cal = pyFAI.calibrant.Calibrant(cal_file,
                                            wavelength=self.wave_length)
        data, centre = self.parent.geom.position_all_modules(self.parent.raw_data,
                                                             canvas=self.parent.canvas.shape)
        det = pyFAI.detectors.Detector(self.pxsize * self.parent.aspect,
                                       self.pxsize)
        det.shape = data.shape
        det.max_shape = det.shape
        cx, cy = centre
        ai = AzimuthalIntegrator(dist=self.cdist,
                                 poni1=cx*self.pxsize*self.parent.aspect,
                                 poni2=cy*self.pxsize,
                                 wavelength=self.wave_length,
                                 detector=det)
        img = cal.fake_calibration_image(ai)
        cmp = cm.Reds
        cmp.set_bad('w', alpha=0)
        cmp.set_under('w', alpha=0)
        if self.img is None:
            self.img = self.parent.ax.imshow(img, cmap=cmp,
                                             alpha=1-self.alpha,
                                             vmin=self.clim[0],
                                             vmax=self.clim[1],
                                             origin='lower')
            self.parent.ax.set_aspect(self.parent.aspect)
        else:
            self.img.set_array(img)
            self.img.set_alpha(1-self.alpha)
            self.img.set_clim(*self.clim)
            self.img.set_visible(True)

    def _clear_overlay(self, *args):
        """Do not display the ring structure."""
        if self.img is None:
            return
        cmp = cm.Reds
        cmp.set_bad('w', alpha=0)
        cmp.set_under('w', alpha=0)
        self.img.set_visible(False)

    def _set_alpha(self, prop):
        """Set the transparency value of the ring overlay."""
        try:
            self.alpha = float(prop['new'])
        except TypeError:
            return
        try:
            self.img.set_alpha(1-self.alpha)
            self.img.set_clim(*self.clim)
        except AttributeError:
            pass

    def _set_clim(self, prop):
        """The the clims of the ring overlay."""
        try:
            if isinstance(prop['new'], tuple):
                self.clim = prop['new']
            else:
                return
        except TypeError:
            return
        try:
            self.img.set_alpha(self.alpha)
            self.img.set_clim(*self.clim)
        except AttributeError:
            pass
