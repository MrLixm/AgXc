import colour
import numpy

from AgXLib import convert_imagery_to_AgX_closeddomain


def _make_linear(colorspace: colour.RGB_Colourspace) -> colour.RGB_Colourspace:
    colorspace.cctf_decoding = colour.linear_function
    colorspace.cctf_encoding = colour.linear_function
    return colorspace


def test_convert_imagery_to_AgX_closeddomain():
    source = numpy.array([0.0])
    source_colorspace = _make_linear(colour.RGB_COLOURSPACES["sRGB"])
    expected = numpy.array([0.0])
    result = convert_imagery_to_AgX_closeddomain(
        source,
        source_colorspace,
        inset=(0.0, 0.0, 0.0),
        rotate=(0.0, 0.0, 0.0),
    )
    # TODO finish test, for now just test there is no error raised
    # numpy.testing.assert_allclose(result, expected)
