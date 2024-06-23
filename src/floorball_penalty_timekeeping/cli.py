import os
import subprocess

import click


@click.command()
@click.option('--debug', default=False, help='Run app in debug mode.')
def program_run(debug):
    """Start the GUI"""
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app.py'))
    subprocess.run(["streamlit", "run", path])
