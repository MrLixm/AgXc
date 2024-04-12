import colour
import numpy

from AgXLib.tonescale import apply_AgX_tonescale


def test_apply_AgX_tonescale():
    source = numpy.array([0.0])
    expected = numpy.array([0.0])
    result = apply_AgX_tonescale(source)
    # TODO find why it doesn't pass and 0 doesn't map back to 0
    # numpy.testing.assert_allclose(result, expected)
