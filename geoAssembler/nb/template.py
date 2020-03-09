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


def fill_notebook_template(nb_vars, dest_path):
    """Fill the notebook template and write it to the destination path"""
    parent = os.path.dirname(__file__)
    tmpl = os.path.join(parent, 'templates', 'geoAssembler.tmpl')

    with open(tmpl) as f:
        jb_tmpl = f.read()

    for key, value in nb_vars.items():
        jb_tmpl = jb_tmpl.replace('{%s}' % key, repr(value))

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, 'w') as f:
        f.write(jb_tmpl)

    print(NB_MESSAGE.format(nb_path=dest_path))


def create_nb(rundir=None, geofile=None, clen=None, energy=None, levels=None,
              dest_path=None):
    """Create a notebook from a template and save it into the user space."""
    nb_vars = {
        'rundir': rundir or RUNDIR,
        'geofile': geofile,
        'levels': levels or [None, None],
        'energy': energy or ENERGY,
        'clen': clen or CLEN,
    }

    if dest_path is None:
        dest_path = os.path.join(NB_DIR, NB_FILE)
    elif not dest_path.endswith('.ipynb'):
        dest_path += '.ipynb'

    fill_notebook_template(nb_vars, dest_path)
