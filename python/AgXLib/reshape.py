"""
Mathematical operations to change the shape of a colorspace's gamut while maintaining
its whitepoint.
"""
import logging
import math

import numpy

import colour

LOGGER = logging.getLogger(__name__)


def _lerp(amount: float, a1: float, a2: float) -> float:
    """
    Linear interpolation between a1 and a2.
    """
    return (1.0 - amount) * a1 + amount * a2


def rotate_point_around(
    src_point: numpy.ndarray,
    center: numpy.ndarray,
    angle: float,
) -> numpy.ndarray:
    """
    References:
        - [1] https://stackoverflow.com/a/2259502/13806195

    Args:
        src_point: of shape=(2,), point to rotate
        center: of shape=(2,), center for the rotation.
        angle: in radians.

    Returns:
        new rotated point of shape=(2,).
    """
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)

    new_point = numpy.array([0.0, 0.0])

    # translate point back to origin
    new_point[0] = src_point[0] - center[0]
    new_point[1] = src_point[1] - center[1]

    # rotate points
    new_point[0] = new_point[0] * cos_a - new_point[1] * sin_a
    new_point[1] = new_point[0] * sin_a + new_point[1] * cos_a

    # translate back
    new_point[0] = new_point[0] + center[0]
    new_point[1] = new_point[1] + center[1]

    return new_point


def get_inset_gamut(
    src_gamut: numpy.ndarray,
    src_whitepoint: numpy.ndarray,
    inset_r: float,
    inset_g: float,
    inset_b: float,
) -> numpy.ndarray:
    """
    Create a smaller variant of the given gamut while keeping its whitepoint untouched.

    Args:
        src_gamut: gamut CIExy coordinates as shape=(3,2).
        src_whitepoint: whitepoint CIExy coordinates as shape=(2,).
        inset_r: red inset amount, [-0,1] range
        inset_g: green inset amount, [-0,1] range
        inset_b: blue inset amount, [-0,1] range

    Returns:
        new smaller gamut CIExy coordinates as shape=(3,2).
    """
    new_gamut = numpy.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])

    new_gamut[0][0] = _lerp(inset_r, src_gamut[0][0], src_whitepoint[0])
    new_gamut[0][1] = _lerp(inset_r, src_gamut[0][1], src_whitepoint[1])
    new_gamut[1][0] = _lerp(inset_g, src_gamut[1][0], src_whitepoint[0])
    new_gamut[1][1] = _lerp(inset_g, src_gamut[1][1], src_whitepoint[1])
    new_gamut[2][0] = _lerp(inset_b, src_gamut[2][0], src_whitepoint[0])
    new_gamut[2][1] = _lerp(inset_b, src_gamut[2][1], src_whitepoint[1])

    return new_gamut


def get_rotated_gamut(
    src_gamut: numpy.ndarray,
    src_whitepoint: numpy.ndarray,
    rotate_r: float,
    rotate_g: float,
    rotate_b: float,
) -> numpy.ndarray:
    """
    Rotate the given gamut primaries around the given whitepoint by the given amount for
    each primary.

    Args:
        src_gamut: gamut CIExy coordinates as shape=(3,2).
        src_whitepoint: whitepoint CIExy coordinates as shape=(2,). Used as center for rotation.
        rotate_r: angle of rotation in degree, [-0,360+] range
        rotate_g: angle of rotation in degree, [-0,360+] range
        rotate_b: angle of rotation in degree, [-0,360+] range

    Returns:
        new rotated gamut CIExy coordinates as shape=(3,2).
    """
    new_gamut = numpy.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])

    # degree to radians
    d2r = math.pi / 180

    new_gamut[0] = rotate_point_around(
        src_point=src_gamut[0],
        center=src_whitepoint,
        angle=rotate_r * d2r,
    )
    new_gamut[1] = rotate_point_around(
        src_point=src_gamut[1],
        center=src_whitepoint,
        angle=rotate_g * d2r,
    )
    new_gamut[2] = rotate_point_around(
        src_point=src_gamut[2],
        center=src_whitepoint,
        angle=rotate_b * d2r,
    )

    return new_gamut


def get_reshaped_colorspace_matrix(
    src_gamut: numpy.ndarray,
    src_whitepoint: numpy.ndarray,
    inset_r: float,
    inset_g: float,
    inset_b: float,
    rotate_r: float,
    rotate_g: float,
    rotate_b: float,
) -> numpy.ndarray:
    """
    Get the normalised 3x3 primary matrix that allow to convert from the given src
    gamut/whitepoint to its reshaped variant.

    That new variant is supposed to have a smaller footprint if insets are not 0.0.

    Args:
        src_gamut: gamut CIExy coordinates as shape=(3,2).
        src_whitepoint: whitepoint CIExy coordinates as shape=(2,). Used as center for operations.
        inset_r: amount of inset for red primary, [-0,1] range
        inset_g: amount of inset for green primary, [-0,1] range
        inset_b: amount of inset for blue primary, [-0,1] range
        rotate_r: angle of rotation for red primary in degree, [-0,360+] range
        rotate_g: angle of rotation for green primary in degree, [-0,360+] range
        rotate_b: angle of rotation for blue primary in degree, [-0,360+] range

    Returns:
        3x3 normalised_primary_matrix as array of shape=(3,3).
    """
    gamut_inset = get_inset_gamut(
        src_gamut,
        src_whitepoint,
        inset_r,
        inset_g,
        inset_b,
    )
    gamut_rotated = get_rotated_gamut(
        gamut_inset,
        src_whitepoint,
        rotate_r,
        rotate_g,
        rotate_b,
    )

    src_to_XYZ = colour.normalised_primary_matrix(src_gamut, src_whitepoint)
    dst_to_XYZ = colour.normalised_primary_matrix(gamut_rotated, src_whitepoint)
    dst_from_XYZ = numpy.linalg.inv(dst_to_XYZ)

    return colour.algebra.matrix_dot(dst_from_XYZ, src_to_XYZ)


if __name__ == "__main__":
    m = get_reshaped_colorspace_matrix(
        numpy.array([[0.64, 0.33], [0.3, 0.6], [0.15, 0.06]]),
        numpy.array([0.3127, 0.329]),
        0.3 + 0.08,
        0.3 + 0.0,
        0.3 + 0.2,
        5,
        0,
        -6,
    )
    print(m)
    print(numpy.linalg.inv(m))
