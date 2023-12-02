import logging
from typing import Union

import numpy

LOGGER = logging.getLogger(__name__)

RGBt = Union[tuple[float, float, float], numpy.ndarray]
"""
Type for an RGB array
"""

RGBable = Union[float, RGBt]
"""
Types that can be converted to a RGB array
"""


def sigmoid_parabolic(array: numpy.ndarray, pivot: RGBable, t0: RGBable):
    """
    Apply a sigmoid parabolic curve on the given array.

    This is an S-curve on a [0-1 range].

    References:
        - [1] Jed Smith: https://github.com/jedypod/nuke-colortools/blob/master/toolsets/transfer_function/SigmoidParabolic.nk

    Args:
        array: [0-1] range RGB or single channel data
        pivot: pivot of the curve
        t0: center of the pivot

    Returns:
        new array with the sigmoid curve applied
    """
    pivot = numpy.array(pivot)
    t0 = numpy.array(t0)
    return numpy.where(
        array < t0,
        t0 * (array / t0) ** pivot,
        1 + (t0 - 1) * ((array - 1) / (t0 - 1)) ** pivot,
    )


def spow(
    array: numpy.ndarray,
    power: RGBable,
) -> numpy.ndarray:
    """
    Power function safe for negatives.

    SRC: /src/OpenColorIO/ops/cdl/CDLOpCPU.cpp#L252
    SRC: /src/OpenColorIO/ops/gradingprimary/GradingPrimary.cpp#L194
    """
    out = abs(array) ** power
    out = out * numpy.copysign(1, array)
    return out


def saturation(
    array: numpy.ndarray,
    amount: RGBable,
    coefs: RGBt = (0.2126, 0.7152, 0.0722),
) -> numpy.ndarray:
    """
    Increase color saturation (not the similarly named clamp operation).

    SRC:
        - src/OpenColorIO/ops/gradingprimary/GradingPrimaryOpCPU.cpp#L214
        - https://video.stackexchange.com/q/9866

    Args:
        array:
        amount:
            saturation with different coeff per channel,
            or same value for all channels
        coefs:
            luma coefficient. Default if not specified are BT.709 ones.

    Returns:
        input array with the given saturation value applied
    """

    luma = array * coefs
    luma = numpy.sum(luma, axis=2)
    luma = numpy.stack((luma,) * 3, axis=-1)

    array -= luma
    array *= amount
    array += luma

    return array
