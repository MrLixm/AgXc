# .dev/OCIO

Contains the build script for the OCIO config.

## prerequisites

- You have a python environment as specified by the repository root `pyproject.toml`.
- The `AgXLib` package is registred in the `PYTHONPATH`
- The `./modules` dir is optionally in your `PYTHONPATH` (if not it is added via 
`sys.path` mechanism).

for tesing you also need:

- Foundry's Nuke installed on your machine (15+ version)
- Git Bash if you are on Windows, to execute shell scripts

## build instructions

Once prerequisites are satisfied:
- run the [build.py](build.py) script with a python interpreter

With no argument the script will build the ocio config using relative paths to
its location.

The build script has a small CLI, use `python build.py --help` to check for 
options.

## testing

To run a basic test the config is working you can execute the 
[launch-tests.sh](tests/nuke/launch-tests.sh) script in the `tests/` folder.

You need to manually check the output of the execution for warnings or errors.
