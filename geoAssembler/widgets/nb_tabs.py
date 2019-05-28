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

from traitlets import HasTraits, Integer, observe
from .. import calibrants


log = logging.getLogger(__name__)


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
        self.roi_btn = widgets.Button(description='Add ',
                                       disabled=False,
                                       button_style='',
                                       icon='',
                                       tooltip='Add Helper',
                                       layout=Layout(width='100px',
                                                     height='30px'))
        self.clr_btn = widgets.Button(description='Clear Helper',
                                      tooltip='Remove All Circles',
                                      disabled=False,
                                      button_style='',
                                      icon='',
                                      layout=Layout(width='100px',
                                                    height='30px'))
        self.roi_type = widgets.Dropdown(options=['Circle', 'Square'],
                                         value='Circle',
                                         description='Type:',
                                         disabled=False,
                                         layout=Layout(width='170px',
                                                       height='30px'))

        self.roi_btn.on_click(self._add_roi)
        self.clr_btn.on_click(self._clear_rois)
        self.buttons = [self.selection]
        self.current_roi = None
        self.roi_func = self.parent.draw_circle
        self.row1 = widgets.HBox([self.selection])
        self.row2 = widgets.HBox([self.roi_type, self.roi_btn, self.clr_btn])
        self.roi_type.observe(self._set_roi_type, names='value')
        self.selection.observe(self._set_quad)
        super().__init__([self.row1, self.row2])

    @observe('num')
    def _set_roi_type(self, prop):
        """Set the roi type."""
        roi_funcs = {'square': self.parent.draw_square,
                     'circle': self.parent.draw_circle}
        self.roi_func = roi_funcs[prop['new'].lower()]

    def _clear_rois(self, *args):
        """Delete all circles from the image."""
        for n, roi in self.parent.rois.items():
            roi.remove()
        self.parent.rois = {}
        self.row2 = widgets.HBox([self.roi_type, self.roi_btn, self.clr_btn])
        self.children = [self.row1, self.row2]

    def _add_roi(self, *args):
        """Add a circel to the image."""
        num = len(self.parent.rois)
        if num >= 10:  # Draw only 10 circles at max
            return
        size = 350
        for roi in self.parent.rois.values():
            roi.set_edgecolor('gray')
        self.roi_func(size, num)
        self.current_roi = num
        self.roi_drn = widgets.Dropdown(options=list(self.parent.rois.keys()),
                                         value=num,
                                         disabled=False,
                                         description='Sel.:',
                                         layout=Layout(width='150px',
                                                       height='30px'))

        self.sp_size = widgets.BoundedFloatText(value=350,
                                              min=0,
                                              max=10000,
                                              step=1,
                                              disabled=False,
                                              description='Size',
                                              layout=Layout(width='200px',
                                                            height='30px'))
        self.sp_angle = widgets.BoundedFloatText(value=0,
                                                 min=0,
                                                 max=360,
                                                 step=0.01,
                                                 disabled=False,
                                                 description='Angle',
                                                 layout=Layout(width='200px',
                                                               height='30px'))

        self.roi_btn.observe(self._sel_roi)
        self.sp_size.observe(self._set_size)
        self.sp_angle.observe(self._set_angle, names='value')
        self.row2 = widgets.HBox([self.roi_type, self.roi_btn, self.clr_btn,
                                  self.roi_drn, self.sp_size, self.sp_angle])
        self.children = [self.row1, self.row2]


    def _set_angle(self, prop):
        """Set the angle of the roi."""
        angle = prop['new']
        roi = self.parent.rois[self.current_roi]
        roi.remove()
        self.roi_func(roi.size, self.current_roi, angle=angle)

    def _set_size(self, selection):
        """Set the roi size."""
        if selection['new'] and selection['old']:
            try:
                size = int(selection['new'])
            except TypeError:
                return
        else:
            return
        roi = self.parent.rois[self.current_roi]
        roi.set_size(size)

    def _sel_roi(self, selection):
        """Select-helper circles."""
        if not isinstance(selection['new'], int):
            return
        self.current_roi = int(selection['new'])
        size = int(self.parent.rois[self.current_roi].get_size())
        for num, roi in self.parent.rois.items():
            if num != self.current_roi:
                roi.set_edgecolor('gray')
            else:
                roi.set_edgecolor('r')
        self.set_size = widgets.BoundedFloatText(value=size,
                                              min=0,
                                              max=10000,
                                              step=1,
                                              disabled=False,
                                              continuous_update=True,
                                              description='Size')
        self.set_size.observe(self._set_size)
        self.row2 = widgets.HBox([self.roi_type, self.roi_btn, self.clr_btn,
                                  self.roi_drn, self.set_size])
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
        self.parent.draw_quad_bound(
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
        self.parent.draw_quad_bound(prop['new']['index'])
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
        try:
           calibs = calibrants.calibrants
        except AttributeError:
           calibs = calibrants        
        self.calibrants = [self.calibrant] + calibs #.calibrants
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
