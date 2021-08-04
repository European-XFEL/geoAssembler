"""Methods and Classes that handle different detectors and their defaults."""
from numpy import s_

INC = 1

class DefaultGeometryConfig:
    """Define global default configuration parameters."""

    # Define all implemented detectors
    detectors = ('AGIPD', 'LPD', 'DSSC') 
    # Fallback quad positions if no geometry file is given as a starting point:
    fallback_quad_pos = {
                        'AGIPD': [(-540, 610),
                                  (-540, -15),
                                  (540, -143),
                                  (540, 482)],

                        'LPD': [(11.4, 299),
                                (-11.5, 8),
                                (254.5, -16),
                                (278.5, 275)],

                        # FIXME: these are made up; replace with measurements?
                        'DSSC': [(-130, 5),
                                 (-130, -125),
                                 (5, -125),
                                 (5, 5),],
                        }

    quad_pos_units = {
        'AGIPD': 'pixels',
        'LPD': 'mm',
        'DSSC': 'mm',
    }

    # Definition of increments (INC) the quadrants should move
    # (u = up, d = down, r = right, l = left is given:
    direction = {'u': (0, INC),
                 'd': (0, -INC),
                 'r': (INC, 0),
                 'l': (-INC, 0)}
    # Translate quad's into module indices
    quad2slice = {
        'AGIPD': {1: s_[0:4], 2: s_[4:8], 3: s_[8:12], 4: s_[12:16]},
        'LPD':   {1: s_[0:4], 2: s_[4:8], 3: s_[8:12], 4: s_[12:16]},
        'DSSC':  {1: s_[0:4], 2: s_[4:8], 3: s_[8:12], 4: s_[12:16]},
    }

    canvas_margin = 300  # pixel, used as margin on each side of detector quadrants
    geom_sel_width = 114

    # Default colormaps
    cmaps = ['binary_r',
             'viridis',
             'coolwarm',
             'winter',
             'summer',
             'hot',
             'OrRd']

    # Default file formats for certain detectors
    file_formats = { #Det     file_type, input, output
                    'AGIPD':  ('CFEL',  'geom', 'geom'),
                    'LPD':    ('XFEL',  'h5',    'csv'),
                    'DSSC':    ('XFEL',  'h5',    'csv')
                   }

    @classmethod
    def check_detector(cls, det):
        """Raise and Error if a given detector is not implemented."""
        if det not in cls.detectors:
            raise NotImplementedError('Detector is currently not Implemented')

