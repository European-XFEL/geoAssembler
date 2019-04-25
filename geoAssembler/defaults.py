
"""Define global default configuration parameters."""


from .geometry import AGIPDGeometry, LPDGeometry


# Fallback quad positions if no geometry file is given as a starting point:
FALLBACK_QUAD_POS = {
                    'AGIPD': [(-540, 610), (-540, -15), (540, -143), (540, 482)],
                    'LPD': [(11.4, 299), (-11.5, 8), (254.5, -16), (278.5, 275)]
                    }

GEOM_MODULES = {'AGIPD': AGIPDGeometry,
                'LPD': LPDGeometry}
# Definition of increments (INC) the quadrants should move to once a direction
# (u = up, d = down, r = right, l = left is given:
INC = 1
DIRECTION = {'u': (0, -INC),
             'd': (0, INC),
             'r': (INC, 0),
             'l': (-INC, 0)}

CANVAS_MARGIN = 300  # pixel, used as margin on each side of detector quadrants
GEOM_SEL_WIDTH = 114

# Default colormaps
DEFAULT_CMAPS = ['binary_r',
                 'viridis',
                 'coolwarm',
                 'winter',
                 'summer',
                 'hot',
                 'OrRd']


