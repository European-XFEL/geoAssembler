"""Define the Widget tabs that are using in CalibrateNb."""


import os
import logging

import numpy as np


from ipywidgets import widgets, Layout
#from IPython.display import display
from matplotlib import cm
#import matplotlib.patches as patches
import pyFAI
import pyFAI.calibrant
from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
from scipy import constants

from . import calibrants
from .defaults import params

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(os.path.basename(__file__))



class CalibTab(widgets.VBox):
    """Calibration-tab of type ipython widget vbox."""

    def __init__(self, parent):
        """Add tab to calibrate geometry to the main widget.

        Parameters:
           parent : CalibrateNb object
        """
        self.parent = parent
        self.title = 'Calibration'
        self.counts = 0

        self.selection = widgets.Dropdown(options=['None', '1', '2', '3', '4'],
                                          value='None',
                                          description='Quadrant',
                                          disabled=False)
        self.circ_btn = widgets.Button(description='Add circle',
                                       disabled=False,
                                       button_style='',
                                       icon='',
                                       tooltip='Add Helper Circle',
                                       layout=Layout(width='100px',
                                                     height='30px'))
        self.clr_btn = widgets.Button(description='Clear Circle',
                                      tooltip='Remove All Circles',
                                      disabled=False,
                                      button_style='',
                                      icon='',
                                      layout=Layout(width='100px',
                                                    height='30px'))

        self.circ_btn.on_click(self._add_circle)
        self.clr_btn.on_click(self._clear_circles)
        self.buttons = [self.selection]
        self.circle = None
        self.row1 = widgets.HBox([self.selection])
        self.row2 = widgets.HBox([self.circ_btn, self.clr_btn])
        self.selection.observe(self._set_quad)
        super(CalibTab, self).__init__([self.row1, self.row2])

    def _clear_circles(self, *args):
        """Delete all circles from the image."""
        for n, circle in self.parent.circles.items():
            circle.remove()
        self.parent.circles = {}
        self.row2 = widgets.HBox([self.circ_btn, self.clr_btn])
        self.children = [self.row1, self.row2]

    def _add_circle(self, *args):
        """Add a circel to the image."""
        num = len(self.parent.circles)
        if num >= 10:  # Draw only 10 circles at max
            return
        r = 350
        for circ in self.parent.circles.values():
            circ.set_edgecolor('gray')
        self.parent._draw_circle(r, num)
        self.circle = num
        self.circ_drn = widgets.Dropdown(options=list(self.parent.circles.keys()),
                                         value=num,
                                         disabled=False,
                                         description='Sel.:',
                                         layout=Layout(width='150px',
                                                       height='30px'))

        self.set_r = widgets.BoundedFloatText(value=350,
                                              min=0,
                                              max=10000,
                                              step=1,
                                              disabled=False,
                                              description='Radius')
        self.circ_drn.observe(self._sel_circle)
        self.set_r.observe(self._set_radius)
        self.row2 = widgets.HBox([self.circ_btn, self.clr_btn,
                                  self.circ_drn, self.set_r])
        self.children = [self.row1, self.row2]

    def _set_radius(self, selection):
        """Set the circle radius."""
        if selection['new'] and selection['old']:
            try:
                r = int(selection['new'])
            except TypeError:
                return
        else:
            return
        circle = self.parent.circles[self.circle]
        circle.set_radius(r)

    def _sel_circle(self, selection):
        """Select-helper circles."""
        if not isinstance(selection['new'], int):
            return
        self.circle = int(selection['new'])
        r = int(self.parent.circles[self.circle].get_radius())
        for num, circ in self.parent.circles.items():
            if num != self.circle:
                circ.set_edgecolor('gray')
            else:
                circ.set_edgecolor('r')
        self.set_r = widgets.BoundedFloatText(value=r,
                                              min=0,
                                              max=10000,
                                              step=1,
                                              disabled=False,
                                              continuous_update=True,
                                              description='Radius')
        self.set_r.observe(self._set_radius)
        self.row2 = widgets.HBox([self.circ_btn, self.clr_btn,
                                  self.circ_drn, self.set_r])
        self.children = [self.row1, self.row2]

    def _move_quadrants(self, pos):
        """Shift a quadrant."""
        if pos['new'] and pos['old']:
            d = pos['owner'].description.lower()[0]
            if isinstance(pos['new'], dict):
                pn = int(pos['new']['value'])
            else:
                pn = int(pos['new'])
            if isinstance(pos['old'], dict):
                po = int(pos['old']['value'])
            else:
                try:
                    po = int(pos['old'])
                except TypeError:
                    po = 0
        else:
            return

        sign = np.sign(po - pn)
        if d == 'h':
            pos = np.array((sign, 0))
        else:
            pos = np.array((0, sign))
        self.parent.geom.move_quad(self.parent.quad, pos)
        self.parent._draw_rect(
            {0: None, 1: 2, 2: 1, 3: 4, 4: 3}[self.parent.quad])
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
        posx_sel.observe(self._move_quadrants)
        posy_sel.observe(self._move_quadrants)

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
        self.counts += 1
        if (self.counts % 5 != 1):
            return
        pos = {0: None, 1: 2, 2: 1, 3: 4, 4: 3}[prop['new']['index']]
        try:
            self.parent.rect.remove()
        except (AttributeError, ValueError):
            pass
        if pos is None:
            self._update_navi(pos)
            self.parent.quad = None
            return
        self.parent._draw_rect(prop['new']['index'])
        if pos != self.parent.quad:
            self._update_navi(pos)
        self.parent.quad = pos


class MaterialTab(widgets.VBox):
    """Calibrant Material Tab."""

    def __init__(self, parent):
        """Set all widgets for the tab.

        Arguments:
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
        self.calibrants = [self.calibrant] + calibrants.calibrants
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
        self.val_slider.observe(self._set_clim)
        self.alpha_slider.observe(self._set_alpha)
        self.clr_btn.on_click(self._clear_overlay)
        self.aply_btn.on_click(self._draw_overlay)
        self.calib_btn.observe(self._set_calibrant)
        self.pxsize_btn.observe(self._set_pxsize)
        self.energy_btn.observe(self._set_wavelength)
        self.dist_btn.observe(self._set_cdist)
        super(widgets.VBox, self).__init__([self.row1, self.row2])

    @staticmethod
    def _energy2lambda(energy):
        """Calc. wavelength from beam energy"""
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
            cal_file = os.path.join(calibrants.celldir, self.calibrant+'.D')
            cal = pyFAI.calibrant.Calibrant(cal_file,
                                            wavelength=self.wave_length)
        data, centre = self.parent.geom.position_all_modules(self.parent.raw_data,
                                                             canvas=self.parent.canvas.shape)
        det = pyFAI.detectors.Detector(self.pxsize, self.pxsize)
        det.shape = data.shape
        det.max_shape = det.shape
        cy, cx = centre
        ai = AzimuthalIntegrator(dist=self.cdist,
                                 poni1=cy*self.pxsize,
                                 poni2=cx*self.pxsize,
                                 wavelength=self.wave_length,
                                 detector=det)
        img = cal.fake_calibration_image(ai)
        cmp = cm.Reds
        cmp.set_bad('w', alpha=0)
        cmp.set_under('w', alpha=0)
        if self.img is None:
            self.img = self.parent.ax.imshow(
                img, cmap=cmp, alpha=1-self.alpha, vmin=self.clim[0], vmax=self.clim[1])
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
