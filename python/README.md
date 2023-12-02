# AgXc/python

Python implementations of AgX.

# Content

- [AgX.numpy.py](AgX.numpy.py): single script with the original AgX implementation,
using only numpy as dependency. **Not updated anymore.**
- [AgXLib](AgXLib): python package with the various AgX component.

# Documentation

## `AgXLib`

Import the various component of AgX in other python modules/scripts.

The library might be updated with the most recent changes on AgX algorithms.

### require

Assume the dependency listed in the root `pyproject.toml` are installed.

### usage

```python
import numpy
import colour
import AgXLib

array = numpy.array([0.1, 0.2, 0.3])
colorspace_workspace = colour.RGB_COLOURSPACES["ITU-R BT.2020"]
# by default BT2020 as an OETF, we don't want to apply it.
colorspace_workspace.cctf_decoding = colour.linear_function
colorspace_workspace.cctf_encoding = colour.linear_function

converted = AgXLib.convert_imagery_to_AgX_closeddomain(
    array,
    colour.RGB_COLOURSPACES["ACEScg"],
    colorspace_workspace,
    inset=(0.15, 0.15, 0.15),
    rotate=(5, 0, -6),
)
# output of the function is in the workspace colorspace
display = colour.RGB_to_RGB(
    converted,
    colorspace_workspace,
    colour.RGB_COLOURSPACES["sRGB"],
    apply_cctf_encoding=True,
)
```


## `AgX.numpy.py`

Encode a linear - sRGB image with the AgX DRT. 

This is a copy of the original Troy implementation that will NOT be updated
with any change.

### require

- `numpy` as only dependency.
- `python~>=3.9`