import os

NB_MESSAGE = """Notebook has been created. You can use it by loading the file
{nb_path} either by using JupyterHub on desy:
 https://max-jhub.desy.de
or by starting a jupyter server:
 jupyter-notebook --port PORT_NUMBER* --no-browser &
and follow the displayed instructions. For more information see:

https://in.xfel.eu/readthedocs/docs/data-analysis-user-documentation/en/latest/computing.html#can-i-execute-a-jupyter-notebook-on-the-maxwell-cluster-and-connect-it-to-the-webbrowser-of-my-desktop-laptop


Note 1: the PORT_NUMBER should be a number of >= 1024 like 8432
"""

NB_DIR = os.path.join(os.environ['HOME'], 'notebooks')
NB_FILE = 'GeoAssembler.ipynb'
CLEN = 0.119  # Default sample distance
ENERGY = 10235  # Default beam energy
# Default run directory
RUNDIR = '/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0005'


def copy_notebook(defaults):
    """Create a new notebook and copy it into the user-space."""
    parent = os.path.dirname(__file__)
    tmpl = os.path.join(parent, 'templates', 'geoAssembler.tmpl')
    try:
        os.makedirs(defaults['folder'])
    except FileExistsError:
        pass
    with open(tmpl) as f:
        jb_tmpl = f.read()

    for key in ('rundir', 'geofile', 'levels', 'clen', 'energy'):
        jb_tmpl = jb_tmpl.replace('{%s}' % key, str(defaults[key]))

    with open(os.path.join(defaults['folder'], defaults['name']), 'w') as f:
        f.write(jb_tmpl)

    print(NB_MESSAGE.format(nb_path=os.path.join(defaults['folder'],
                                                 defaults['name'])))


def create_nb(rundir=None, geofile=None, clen=None, energy=None, levels=None,
              nb_dir=None, nb_file=None):
    """Creat a notebook and copy it into the user space."""
    # Get the default varaibles for the notebook, if user has already given them
    # take them if not ask for them and provide default options
    nb_defaults = {}
    nb_defaults['rundir'] = repr(rundir or RUNDIR)
    if geofile is not None:
        nb_defaults['geofile'] = repr(geofile)
    else:
        nb_defaults['geofile'] = None
    if levels is None:
        levels = [None, None]
    else:
        levels = levels
    nb_defaults['levels'] = levels
    nb_defaults['energy'] = energy
    nb_defaults['folder'] = nb_dir or NB_DIR
    name = nb_file or NB_FILE
    if not name.endswith('.ipynb'):
        name += '.ipynb'
    nb_defaults['name'] = os.path.basename(name)
    nb_defaults['clen'] = clen or CLEN
    copy_notebook(nb_defaults)