
"""Methods and Classes that handle different detectors and their defaults."""

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

                        'DSSC': [(-5, 140),
                                 (-5, -5),
                                 (130, -5),
                                 (130, 140)],
                        }

    # Definition of increments (INC) the quadrants should move
    # (u = up, d = down, r = right, l = left is given:
    direction = {'u': (0, INC),
                 'd': (0, -INC),
                 'r': (INC, 0),
                 'l': (-INC, 0)}
    # Translate quad's into module indices
    quad2index = {
                  'AGIPD' : {1: 0, 2: 4, 3: 8, 4: 12},
                  'LPD' : {1: 0, 2: 4, 3: 8, 4: 12},
                  'DSSC' : {1: 0, 2: 4, 3: 8, 4: 12},
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

