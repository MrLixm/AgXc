"""
Nearly all the content here is a direct copy of Troy Sobotka work :
https://github.com/sobotka/AgX-S2O3/blob/main/AgX.py
Which based himself on the work of Jed Smith.

Slight modifications in terms of code style but outcome is similar.
"""
import logging
import typing

import numpy

from ._types import Ndarray

LOGGER = logging.getLogger(__name__)


NdarrayT = typing.TypeVar("NdarrayT", bound=Ndarray)


def _equation_scale(
    x_pivot: NdarrayT,
    y_pivot: NdarrayT,
    slope_pivot: NdarrayT,
    power: NdarrayT,
) -> NdarrayT:
    """
    All argument expected to be of the same last dimension.
    """
    a = (slope_pivot * x_pivot) ** -power
    b = ((slope_pivot * (x_pivot / y_pivot)) ** power) - 1.0
    return (a * b) ** (-1.0 / power)


def _equation_hyperbolic(x: NdarrayT, power: NdarrayT) -> NdarrayT:
    """
    All argument expected to be of the same last dimension.
    """
    return x / ((1.0 + x**power) ** (1.0 / power))


def _equation_term(
    array: NdarrayT,
    x_pivot: NdarrayT,
    slope_pivot: NdarrayT,
    scale: NdarrayT,
) -> NdarrayT:
    """
    All argument expected to be of the same last dimension.
    """
    return (slope_pivot * (array - x_pivot)) / scale


def _equation_curve(
    array: Ndarray,
    x_pivot: Ndarray,
    y_pivot: Ndarray,
    slope_pivot: Ndarray,
    toe_power: Ndarray,
    shoulder_power: Ndarray,
    scale: Ndarray,
) -> Ndarray:
    """
    All argument expected to be of the same last dimension.
    """
    a = _equation_hyperbolic(
        _equation_term(array, x_pivot, slope_pivot, scale), toe_power
    )
    a *= scale
    a += y_pivot

    b = _equation_hyperbolic(
        _equation_term(array, x_pivot, slope_pivot, scale), shoulder_power
    )
    b *= scale
    b += y_pivot

    curve = numpy.where(scale < 0.0, a, b)
    return curve


def _equation_full_curve(
    array: Ndarray,
    x_pivot: Ndarray,
    y_pivot: Ndarray,
    slope_pivot: Ndarray,
    toe_power: Ndarray,
    shoulder_power: Ndarray,
) -> Ndarray:
    scale_x_pivot = numpy.where(array >= x_pivot, 1.0 - x_pivot, x_pivot)
    scale_y_pivot = numpy.where(array >= x_pivot, 1.0 - y_pivot, y_pivot)

    toe_scale = _equation_scale(
        scale_x_pivot,
        scale_y_pivot,
        slope_pivot,
        toe_power,
    )
    shoulder_scale = _equation_scale(
        scale_x_pivot,
        scale_y_pivot,
        slope_pivot,
        shoulder_power,
    )

    scale = numpy.where(array >= x_pivot, shoulder_scale, -toe_scale)

    return _equation_curve(
        array,
        x_pivot,
        y_pivot,
        slope_pivot,
        toe_power,
        shoulder_power,
        scale,
    )


def apply_AgX_tonescale(
    array: Ndarray,
    min_EV: float = -10.0,
    max_EV: float = +6.5,
    general_contrast: float = 2.0,
    limits_contrast: tuple[float, float] = (3.0, 3.25),
) -> Ndarray:
    """
    Apply the AgX 1D tonescale curve on the given R-G-B array.

    Args:
        array:
            imagery data as RGB or single channel,
            usually in a "shaper space" like log encoding.
        min_EV: minimal exposure being fitted in the curve [0,1] range.
        max_EV: maximum exposure being fitted in the curve [0,1] range.
        general_contrast: increase "s" shape
        limits_contrast: toe and shoulder contrast

    Returns:
        new array with the tonescale applied, same shape as input array.
    """
    AgX_x_pivot = numpy.abs(min_EV / (max_EV - min_EV))
    AgX_y_pivot = 0.50

    AgX_x_pivot = numpy.asarray(AgX_x_pivot)
    AgX_y_pivot = numpy.asarray(AgX_y_pivot)
    general_contrast = numpy.asarray(general_contrast)
    limits_contrast = numpy.asarray(limits_contrast)

    converted = _equation_full_curve(
        array,
        AgX_x_pivot,
        AgX_y_pivot,
        general_contrast,
        limits_contrast[0],
        limits_contrast[1],
    )
    return converted
