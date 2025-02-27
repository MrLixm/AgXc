# .dev/OCIO

Contains the build script for the OCIO config.

The OCIO config is defined in python using the official API which then generates
the final yaml config.

Because of the complexity of the OCIO implementations in DCCs we had to generates
multiple variants that all share the same "use-interface" but differs in backend
implementation.

## prerequisites

- You have a python virtual environment as specified by the repository root
  `pyproject.toml`.
- The `./python` directory is registred in the `PYTHONPATH`
    - note it is automatically appended to `sys.path` by the scripts

for tesing you also need:

- Foundry's Nuke installed on your machine (15+ version).
- Maxon's Redshift installed (for no particular DCC).
- Git Bash if you are on Windows, to execute shell scripts.

## build instructions

Once prerequisites are satisfied:

- run the [ocio-agxc-build.py](scripts/ocio-agxc-build.py) script with a python
  interpreter

With no argument the script will build the ocio config using relative paths to
its location.

The build script has a small CLI, use `--help` argument to check its options.

## testing

Tests allow to verify the config is working as expected and are stored in
`./tests`.

You usually need to manually check the output of the execution for
warnings or errors.
