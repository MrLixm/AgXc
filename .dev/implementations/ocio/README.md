# .dev/OCIO

Contains the build script for the OCIO config.

## prerequisites

- You have a python environment as specified by the repository root `pyproject.toml`.
- The `AgXLib` package is in the `PYTHONPATH`

## build instructions

Once prerequisites are satisfied:
- run the [build.py](build.py) script with a python interpreter

With no argument the script will build the ocio config using relative paths to
its location.

The build script has a small CLI, use `python build.py --help` to check for 
options.
