import logging

import colour
import numpy

import AgXLib
from ._types import Ndarray

LOGGER = logging.getLogger(__name__)


def convert_imagery_to_AgX_closeddomain(
    src_array: Ndarray,
    src_colorspace: colour.RGB_Colourspace,
    inset: tuple[float, float, float],
    rotate: tuple[float, float, float],
    tonescale_min_EV: float = -10.0,
    tonescale_max_EV: float = +6.5,
    tonescale_contrast: float = 2.0,
    tonescale_limits: tuple[float, float] = (3.0, 3.25),
) -> Ndarray:
    """
    Apply the AgX DRT on the given array and return a new array  encoded in
    the provided workspace colorspace.

    The inset and rotate values are bounds to the workspace colorspace selected.

    Args:
        src_array: R-G-B imagery data in any state
        src_colorspace:
            colorspace the src_array is encoded in, INCLUDING transfer-function.
            Used as the workspace colorspace for inset.
        inset: amount of inset to apply per primary as [R, G, B], [-0,1] range.
        rotate: amount of rotation in degree to apply per primary as [R, G, B], [-0,360+] range.
        tonescale_min_EV:
        tonescale_max_EV:
        tonescale_contrast:
        tonescale_limits:

    Returns:
        new R-G-B image data array encoded in the provided workspace_colorspace
    """
    # anything outside the gamut of the working space is discarded as not valid
    wip_array = src_array.clip(min=0.0)

    inset_matrix = AgXLib.get_reshaped_colorspace_matrix(
        src_gamut=src_colorspace.primaries,
        src_whitepoint=src_colorspace.whitepoint,
        inset_r=inset[0],
        inset_g=inset[1],
        inset_b=inset[2],
        rotate_r=rotate[0],
        rotate_g=rotate[1],
        rotate_b=rotate[2],
    )
    # XXX: the inset created is a SMALLER variant of the gamut but the operation we want
    #   to apply is actually a conversion to a BIGGER gamut, which will compress the value.
    #   Where [1,0,0] could be converted to something like [0.85, 0.03, 0.02], leaving
    #   room for the per-channel of the tonescale operation.
    #   Which is why we invert the matrix.
    inset_matrix = numpy.linalg.inv(inset_matrix)

    # apply "inset"
    wip_array = colour.algebra.vector_dot(inset_matrix, wip_array)

    # convert to the log shaper space for the tonescale
    wip_array = AgXLib.convert_open_domain_to_normalized_log2(
        wip_array,
        minimum_ev=tonescale_min_EV,
        maximum_ev=tonescale_max_EV,
    )
    wip_array = wip_array.clip(0.0, 1.0)

    # apply tonescale (1D curve)
    wip_array = AgXLib.apply_AgX_tonescale(
        wip_array,
        min_EV=tonescale_min_EV,
        max_EV=tonescale_max_EV,
        general_contrast=tonescale_contrast,
        limits_contrast=tonescale_limits,
    )
    # linearize as the tonescale is display-referred as ~= 2.4 power function
    # TODO verify if 2.4 or 2.2 needed
    wip_array = colour.algebra.spow(wip_array, 2.4)

    # we let the use handle the workspace colorspace -> display colorspace conversion
    return wip_array
