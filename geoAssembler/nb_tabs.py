"""Define the Widget tabs that are using in CalibrateNb"""


import os
import logging

import numpy as np


from ipywidgets import widgets, Layout
from IPython.display import display
from matplotlib import pyplot as plt, cm
import matplotlib.patches as patches

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
        if num >= 10: #Draw only 10 circles at max
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
            pos = np.array((0, sign))
        else:
            pos = np.array((sign, 0))
        self.parent.geom.move_quad(self.parent.quad, pos)
        self.parent._draw_rect(
                {0: None, 1: 2, 2: 1, 3: 4, 4: 3}[self.parent.quad])
        self.parent.update_plot(None)

    def _update_navi(self, pos):
        """Add navigation buttons."""
        posx_sel = widgets.BoundedIntText(value=0,
                                          min=-1000,
                                          max=1000,
                                          step=1,
                                          disabled=False,
                                          continuous_update=True,
                                          description='Horizontal')
        posy_sel = widgets.BoundedIntText(value=0,
                                          min=-1000,
                                          max=1000,
                                          step=1,
                                          disabled=False,
                                          continuous_update=True,
                                          description='Vertical')
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


