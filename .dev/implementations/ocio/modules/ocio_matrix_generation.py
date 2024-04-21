from typing import Optional

from typing import Literal
from typing import Union

import colour
import numpy

DEFAULT_CAT = "Bradford"
DEFAULT_DECIMALS = 12


def matrix_3x3_to_4x4(matrix: numpy.ndarray) -> numpy.ndarray:
    """
    Convert a 3x3 matrix to a 4x4 matrix as such :
    [[ value  value  value  0. ]
     [ value  value  value  0. ]
     [ value  value  value  0. ]
     [ 0.     0.     0.    1. ]]

    Returns:
        4x4 matrix
    """

    output = numpy.append(matrix, [[0], [0], [0]], axis=1)
    output = numpy.append(output, [[0, 0, 0, 1]], axis=0)
    return output


def matrix_format_ocio(matrix: numpy.ndarray) -> list[float]:
    """
    Format the given 3x3 matrix to an OCIO parameters complient list.

    Args:
        matrix: 3x3 matrix
    Returns:
        list: 4x4 matrix in a single line list.
    """
    new_matrix = matrix_3x3_to_4x4(matrix)
    # "un-nest" the matrix by ensuring we have a flat list
    new_matrix = numpy.concatenate(new_matrix).tolist()
    return new_matrix


def matrix_whitepoint_cat(
    source_whitepoint: numpy.ndarray,
    target_whitepoint: numpy.ndarray,
    cat: str = DEFAULT_CAT,
) -> numpy.ndarray:
    """Return the matrix to perform a chromatic adaptation with the given
    parameters.

    Args:
        source_whitepoint: source whitepoint name as xy coordinates
        target_whitepoint: target whitepoint name as xy coordinates
        cat: chromatic adaptation transform method to use.

    Returns:
        chromatic adaptation matrix from test viewing conditions
         to reference viewing conditions. A 3x3 matrix.
    """

    matrix = colour.adaptation.matrix_chromatic_adaptation_VonKries(
        colour.xy_to_XYZ(source_whitepoint),
        colour.xy_to_XYZ(target_whitepoint),
        transform=cat,
    )

    return matrix


def matrix_primaries_transform_ocio(
    source: Union[colour.RGB_Colourspace, Literal["XYZ"]],
    target: Union[colour.RGB_Colourspace, Literal["XYZ"]],
    source_whitepoint: Optional[numpy.ndarray] = None,
    target_whitepoint: Optional[numpy.ndarray] = None,
    cat: str = DEFAULT_CAT,
    decimals: int = DEFAULT_DECIMALS,
) -> list[float]:
    """
    By given a source and target colorspace, return the corresponding
    colorspace conversion matrix.
    You can use "XYZ" as a source or target.

    Args:
        source: source colorspace, use "XYZ" for CIE-XYZ.
        target: target colorspace, use "XYZ" for CIE-XYZ.
        source_whitepoint: whitepoint coordinates as [x, y]
        target_whitepoint: whitepoint coordinates as [x, y]
        cat: chromatic adaptation transform
        decimals: number of decimal after zero to conserve
    Returns:
        4x4 matrix in a single line list.
    """
    matrix_cat = None
    if source_whitepoint is not None and target_whitepoint is not None:
        matrix_cat = matrix_whitepoint_cat(
            source_whitepoint=source_whitepoint,
            target_whitepoint=target_whitepoint,
            cat=cat,
        )

    if source == "XYZ" or target == "XYZ":
        if target == "XYZ":
            matrix = source.matrix_RGB_to_XYZ

            if matrix_cat is not None:
                matrix = numpy.dot(matrix_cat, matrix)

        else:
            matrix = target.matrix_XYZ_to_RGB

            if matrix_cat is not None:
                matrix = numpy.dot(matrix, matrix_cat)

    else:
        matrix = source.matrix_RGB_to_XYZ

        if matrix_cat is not None:
            matrix = numpy.dot(matrix_cat, source.matrix_RGB_to_XYZ)

        matrix = numpy.dot(target.matrix_XYZ_to_RGB, matrix)

    matrix = matrix.round(decimals)
    return matrix_format_ocio(matrix)
