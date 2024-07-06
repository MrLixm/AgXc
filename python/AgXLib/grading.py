import logging
import math
from typing import Union

import numpy

from ._types import Ndarray

LOGGER = logging.getLogger(__name__)

RGBt = Union[tuple[float, float, float], numpy.ndarray]
"""
Type for an RGB array
"""

RGBable = Union[float, RGBt]
"""
Types that can be converted to a RGB array
"""


def sigmoid_parabolic(array: Ndarray, pivot: RGBable, t0: RGBable):
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


def tonemap_piecewise_power(
    array: Ndarray,
    pivot_x: RGBable = 0.5,
    pivot_y: RGBable = 0.5,
    slope: RGBable = 3.0,
    shoulder_length: RGBable = 0.1,
    toe_length: RGBable = 0.0,
    white: tuple[RGBable, RGBable] = (1.0, 1.0),
    black: tuple[RGBable, RGBable] = (0.0, 0.0),
):
    """
    Apply the John Hable picewise power tonemap curve as modified by Jed Smith.

    This is an S-curve on a [0-1 range].

    References:
        - [1] https://github.com/jedypod/nuke-colortools/blob/master/toolsets/transfer_function/Tonemap_PiecewisePower.nk
    """
    pv_x = numpy.array(pivot_x)
    pv_y = numpy.array(pivot_y)
    m = numpy.array(slope)
    ls = numpy.array(shoulder_length)
    lt = numpy.array(toe_length)
    pw = (numpy.array(white[0]), numpy.array(white[1]))
    pb = (numpy.array(black[0]), numpy.array(black[1]))

    pt = (
        -lt / (numpy.sqrt(m * m + 1)) + pv_x,
        -(m * lt) / (numpy.sqrt(m * m + 1)) + pv_y,
    )
    ps = (
        ls / (numpy.sqrt(m * m + 1)) + pv_x,
        (m * ls) / (numpy.sqrt(m * m + 1)) + pv_y,
    )

    cb = pt[1] - pt[0] * m
    bt = (m * (pt[0] - pb[0])) / (pt[1] - pb[1])
    at = numpy.log(pt[1] - pb[1]) - bt * numpy.log(pt[0] - pb[0])
    bs = (m * (pw[0] - ps[0])) / (pw[1] - ps[1])
    as_ = numpy.log(pw[1] - ps[1]) - bs * numpy.log(pw[0] - ps[0])

    return numpy.where(
        array <= 0,
        0.0,
        numpy.where(
            array <= pt[0],
            numpy.exp(at + bt * numpy.log(array - pb[0])) + pb[1],
            numpy.where(
                array < ps[0],
                m * array + cb,
                -numpy.exp(as_ + bs * numpy.log(-(array - pw[0]))) + pw[1],
            ),
        ),
    )


def spow(
    array: Ndarray,
    power: RGBable,
) -> Ndarray:
    """
    Power function safe for negatives.

    SRC: /src/OpenColorIO/ops/cdl/CDLOpCPU.cpp#L252
    SRC: /src/OpenColorIO/ops/gradingprimary/GradingPrimary.cpp#L194
    """
    out = abs(array) ** power
    out = out * numpy.copysign(1, array)
    return out


def saturation(
    array: Ndarray,
    amount: RGBable,
    coefs: RGBt = (0.2126, 0.7152, 0.0722),
) -> Ndarray:
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
