import numpy

from AgXLib.grading import sigmoid_parabolic


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
