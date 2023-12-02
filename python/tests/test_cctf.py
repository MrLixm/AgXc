import numpy

from AgXLib.cctf import convert_open_domain_to_normalized_log2
from AgXLib.cctf import convert_normalized_log2_to_open_domain


def test_convert_open_domain_to_normalized_log2():
    source = numpy.array([0.333])
    expected = numpy.array([0.333])
    _ = convert_open_domain_to_normalized_log2(source)
    numpy.testing.assert_equal(source, expected)

    source = numpy.array([-0.05])
    expected = numpy.array([0.0])
    result = convert_open_domain_to_normalized_log2(source)
    numpy.testing.assert_allclose(result, expected)


def test_convert_normalized_log2_to_open_domain():
    source = numpy.array([0.333], dtype=numpy.float64)
    intermediate = convert_open_domain_to_normalized_log2(source)
    result = convert_normalized_log2_to_open_domain(intermediate)
    numpy.testing.assert_allclose(result, source)

    source = numpy.array([0.333, -0.05, 2.83, 0.0, 0.00123], dtype=numpy.float64)
    expected = numpy.array([0.333, 0.0, 2.83, 0.0, 0.00123], dtype=numpy.float64)
    intermediate = convert_open_domain_to_normalized_log2(source)
    result = convert_normalized_log2_to_open_domain(intermediate)
    numpy.testing.assert_allclose(result, expected)
