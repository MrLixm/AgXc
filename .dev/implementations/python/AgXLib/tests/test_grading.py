import numpy

from AgXLib.grading import sigmoid_parabolic
from AgXLib.grading import tonemap_piecewise_power


# compared to nuke reference implementation
def test_sigmoid_parabolic():
    source = numpy.array([0.107])
    expected = numpy.array([0.02841447])
    result = sigmoid_parabolic(source, 1.86, 0.5)
    numpy.testing.assert_allclose(result, expected, atol=10e-5)

    source = numpy.array([0.107, 0.306, 0.56])
    expected = numpy.array([0.02429, 0.17149, 0.52774])
    result = sigmoid_parabolic(source, 1.86, 0.6)
    numpy.testing.assert_allclose(result, expected, atol=10e-5)

    source = numpy.array([0.107, 0.306, 0.56])
    expected = numpy.array([0.02429, 0.21853, 0.52629])
    result = sigmoid_parabolic(source, (1.86, 1.5, 1.9), 0.6)
    numpy.testing.assert_allclose(result, expected, atol=10e-5)


# compared to nuke reference implementation
def test_tonemap_piecewise_power():
    source = numpy.array([0.107])
    expected = numpy.array([0.00490])
    result = tonemap_piecewise_power(source)
    numpy.testing.assert_allclose(result, expected, atol=10e-5)

    source = numpy.array([0.107])
    expected = numpy.array([0.04799])
    result = tonemap_piecewise_power(
        source,
        0.4,
        0.65,
        2.88,
        0.1,
        0.15,
    )
    numpy.testing.assert_allclose(result, expected, atol=10e-5)

    source = numpy.array([0.107, 0.306, 0.56])
    expected = numpy.array([0.00490, 0.11461, 0.67382])
    result = tonemap_piecewise_power(source)
    numpy.testing.assert_allclose(result, expected, atol=10e-5)

    source = numpy.array([0.107, 0.306, 0.56])
    expected = numpy.array([0.00667, 0.10389, 0.69844])
    result = tonemap_piecewise_power(source, slope=(2.8, 3.2, 3.5))
    numpy.testing.assert_allclose(result, expected, atol=10e-5)
