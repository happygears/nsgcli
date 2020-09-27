# NetSpyGlass Command Line Tools

this package installs Python module `nsgcli` and three command-line
entry points: `nsgcli`, `nsgql` and `silence`.

You should set up a virtualenv to work with this code: In IntelliJ:
under Project Settings -> Project, create a new SDK of type 
virtualenv, and base it on a Python3 (>= 3.8) installation on your
machine. IntelliJ will then offer to download the dependencies into 
the `venv` directory. You can also install the dependencies manually
if you enter the environment.

Enter the virtual environment by running `. venv/bin/activate` in the 
project directory.

If necessary install dependencies with 
`python3 -m pip install -r requirements.txt`.

To create entry points for testing during development, run 
`python3 -m pip install --editable .`

Use script `tools/build.sh` to build and `tools/upload.sh` to push to pypi.

