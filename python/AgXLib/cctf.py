import logging

import colour.models
import numpy

LOGGER = logging.getLogger(__name__)

# shorter alias
Ndarray = numpy.ndarray


def convert_open_domain_to_normalized_log2(
    in_od: Ndarray,
    minimum_ev: float = -10.0,
    maximum_ev: float = +6.5,
    in_midgrey: float = 0.18,
) -> Ndarray:
    """
    "lin to log" operation.


    Similar to OCIO lg2 AllocationTransform.

    References:
        - [1] https://github.com/sobotka/AgX-S2O3/blob/main/AgX.py

    Args:
        in_od: floating point image in open-domain state
        minimum_ev:
        maximum_ev:
        in_midgrey:
    """
    out_log = numpy.where(
        in_od <= numpy.finfo(float).eps,
        0.0,
        colour.models.log_encoding_Log2(
            in_od,
            middle_grey=in_midgrey,
            min_exposure=minimum_ev,
            max_exposure=maximum_ev,
        ),
    )
    return out_log


def convert_normalized_log2_to_open_domain(
    in_log2: Ndarray,
    minimum_ev: float = -10.0,
    maximum_ev: float = +6.5,
    in_midgrey: float = 0.18,
) -> Ndarray:
    """
    "log to lin" operation.

    Similar to OCIO lg2 AllocationTransform.

    References:
        - [1] https://github.com/sobotka/AgX-S2O3/blob/main/AgX.py

    Args:
        in_log2: image in log encoding
        minimum_ev:
        maximum_ev:
        in_midgrey:
    """
    od = colour.models.log_decoding_Log2(
        in_log2,
        middle_grey=in_midgrey,
        min_exposure=minimum_ev,
        max_exposure=maximum_ev,
    )
    return numpy.where(od <= 0.00017578125, 0.0, od)
