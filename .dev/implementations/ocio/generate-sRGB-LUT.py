import logging
import sys
from pathlib import Path

import colour

LOGGER = logging.getLogger(__name__)

THIS_DIR = Path(__file__).parent


def generate_sRGB_LUT() -> colour.LUT1D:
    lut_size = 4096
    lut_domain = [0.0, 1.0]

    array = colour.LUT1D.linear_table(lut_size, lut_domain)
    array = colour.models.RGB_COLOURSPACE_sRGB.cctf_decoding(array)

    lut = colour.LUT1D(
        table=array,
        name="sRGB EOTF decoding",
        domain=[0.0, 1.0],
        comments=[
            "sRGB IEC 61966-2-1 2.2 Exponent Reference EOTF Display. Decoding function."
        ],
    )
    return lut


def main():
    repoRootDir = THIS_DIR.parent.parent.parent
    targetPath = repoRootDir / "ocio" / "LUTs" / "sRGB-EOTF-inverse.spi1d"

    LOGGER.info(f"generating sRGB lut")
    lut = generate_sRGB_LUT()
    LOGGER.info(f"writing sRGB lut to <{targetPath}>")
    colour.write_LUT(lut, str(targetPath))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="{levelname: <7} | {asctime} [{name}] {message}",
        style="{",
        stream=sys.stdout,
    )
    main()
