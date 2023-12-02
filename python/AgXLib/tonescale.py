"""
Nearly all the content here is a direct copy of Troy Sobotka work :
https://github.com/sobotka/AgX-S2O3/blob/main/AgX.py
Slight modifications in terms of code style but outcome is similar.
"""
import logging

import numpy

LOGGER = logging.getLogger(__name__)

# shorter alias
Ndarray = numpy.ndarray


def _equation_scale(
    x_pivot: Ndarray,
    y_pivot: Ndarray,
    slope_pivot: Ndarray,
    power: Ndarray,
) -> Ndarray:
    """
    The following is a completely tunable sigmoid function compliments
    of the incredible hard work of Jed Smith. He's an incredible peep,
    but don't let anyone know that I said that -- (Troy.S)
    """
    a = (slope_pivot * x_pivot) ** -power
    b = ((slope_pivot * (x_pivot / y_pivot)) ** power) - 1.0
    return (a * b) ** (-1.0 / power)


def _equation_hyperbolic(x: Ndarray, power: Ndarray) -> Ndarray:
    return x / ((1.0 + x**power) ** (1.0 / power))


def _equation_term(
    x: Ndarray,
    x_pivot: Ndarray,
    slope_pivot: Ndarray,
    scale: Ndarray,
) -> Ndarray:
    return (slope_pivot * (x - x_pivot)) / scale


def _equation_curve(
    x: Ndarray,
    x_pivot: Ndarray,
    y_pivot: Ndarray,
    slope_pivot: Ndarray,
    power: Ndarray,
    scale: Ndarray,
) -> Ndarray:
    a = _equation_hyperbolic(
        _equation_term(x, x_pivot, slope_pivot, scale), power[..., 0]
    )
    a *= scale
    a += y_pivot

    b = _equation_hyperbolic(
        _equation_term(x, x_pivot, slope_pivot, scale), power[..., 1]
    )
    b *= scale
    b += y_pivot

    curve = numpy.where(scale < 0.0, a, b)
    return curve


def _equation_full_curve(
    lut_array: Ndarray,
    x_pivot: float,
    y_pivot: float,
    slope_pivot: float,
    power: tuple[float, float],
) -> Ndarray:
    x_pivot = numpy.asarray(x_pivot)
    y_pivot = numpy.asarray(y_pivot)
    slope_pivot = numpy.asarray(slope_pivot)
    power = numpy.asarray(power)

    scale_x_pivot = numpy.where(lut_array >= x_pivot, 1.0 - x_pivot, x_pivot)
    scale_y_pivot = numpy.where(lut_array >= x_pivot, 1.0 - y_pivot, y_pivot)

    toe_scale = _equation_scale(
        scale_x_pivot, scale_y_pivot, slope_pivot, power[..., 0]
    )
    shoulder_scale = _equation_scale(
        scale_x_pivot, scale_y_pivot, slope_pivot, power[..., 1]
    )

    scale = numpy.where(lut_array >= x_pivot, shoulder_scale, -toe_scale)

    return _equation_curve(lut_array, x_pivot, y_pivot, slope_pivot, power, scale)


def apply_AgX_tonescale(
    rgbarray: Ndarray,
    min_EV: float = -10.0,
    max_EV: float = +6.5,
    general_contrast: float = 2.0,
    limits_contrast: tuple[float, float] = (3.0, 3.25),
) -> Ndarray:
    """
    Apply the AgX 1D tonescale curve on the given R-G-B array.

    Args:
        rgbarray: R-G-B imagery data, usually in a "shaper space" like log encoding.
        min_EV: minimal exposure fitted in the [0,1] range.
        max_EV: maximum exposure fitted in the [0,1] range.
        general_contrast:
        limits_contrast:

    Returns:
        new array with the tonescale applied, same shape as input array.
    """
    AgX_x_pivot = numpy.abs(min_EV / (max_EV - min_EV))
    AgX_y_pivot = 0.50

    converted = _equation_full_curve(
        rgbarray,
        AgX_x_pivot,
        AgX_y_pivot,
        general_contrast,
        limits_contrast,
    )
    return converted
