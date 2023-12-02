import dataclasses
import logging
import sys
from pathlib import Path
from typing import Callable

import colour
import numpy

import AgXLib

LOGGER = logging.getLogger(__name__)

THIS_DIR = Path(__file__).parent


def _get_colourspace(name: str) -> colour.RGB_Colourspace:
    # convenient function to have proper type hints
    return colour.RGB_COLOURSPACES[name]


def create_lut(
    processor: Callable[[numpy.ndarray], numpy.ndarray],
    resolution: int,
    name: str,
    comment: str = "",
) -> colour.LUT3D:
    domain = numpy.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
    domain_str = str(domain).replace("\n", "")
    lut = colour.LUT3D.linear_table(resolution, domain)
    lut = processor(lut)

    comment = comment + "\n" if comment else ""
    comments = (
        comment + f"LUT resolution = {resolution}\n" + f"LUT domain = {domain_str}"
    )

    return colour.LUT3D(
        table=lut,
        name=name,
        size=resolution,
        domain=domain,
        comments=comments.split("\n"),
    )


@dataclasses.dataclass
class AgXConfig:
    inset: tuple[float, float, float]
    rotate: tuple[float, float, float]
    tonescale_min_EV: float
    tonescale_max_EV: float
    tonescale_contrast: float
    tonescale_limits: tuple[float, float]
    post_gamma: float = 1.0
    colorspace_workspace_name: str = "ITU-R BT.2020"

    def copy(self) -> "AgXConfig":
        return dataclasses.replace(self)


def convert_VLog_to_AgX(
    rgbarray: numpy.ndarray,
    colorspace_dst: colour.RGB_Colourspace,
    agx_config: AgXConfig,
) -> numpy.ndarray:
    colorspace_source = _get_colourspace("V-Gamut")
    colorspace_workspace = _get_colourspace(agx_config.colorspace_workspace_name)

    # make workspace Linear
    colorspace_workspace.cctf_decoding = colour.linear_function
    colorspace_workspace.cctf_encoding = colour.linear_function

    new_array = AgXLib.convert_imagery_to_AgX_closeddomain(
        rgbarray,
        colorspace_source,
        colorspace_workspace,
        inset=agx_config.inset,
        rotate=agx_config.rotate,
        tonescale_min_EV=agx_config.tonescale_min_EV,
        tonescale_max_EV=agx_config.tonescale_max_EV,
        tonescale_contrast=agx_config.tonescale_contrast,
        tonescale_limits=agx_config.tonescale_limits,
    )

    # convert for display
    new_array = colour.RGB_to_RGB(
        new_array,
        input_colourspace=colorspace_workspace,
        output_colourspace=colorspace_dst,
        apply_cctf_decoding=True,
        apply_cctf_encoding=True,
    )

    # post-grading, originally called "Punchy"
    new_array = colour.algebra.spow(new_array, 1 / agx_config.post_gamma)

    new_array = new_array.clip(0.0, 1.0)
    return new_array


"""

USER EDITABLE

"""

# noinspection PyTypeChecker
AGX_CONFIG_LOOK1 = AgXConfig(
    # (x + Z) where Z is global inset factor
    inset=tuple(min(x + 0.15, 1.0) for x in (0.08, 0.0, 0.2)),
    rotate=(5, 0, -6),
    tonescale_min_EV=-10.0,
    tonescale_max_EV=+6.5,
    tonescale_contrast=2.0,
    tonescale_limits=(3.0, 3.25),
    post_gamma=1.0,
    colorspace_workspace_name="ITU-R BT.2020",
)

AGX_CONFIG_LOOK2 = AGX_CONFIG_LOOK1.copy()
AGX_CONFIG_LOOK2.post_gamma = 0.65

AGX_CONFIG_LOOK3 = AGX_CONFIG_LOOK1.copy()
AGX_CONFIG_LOOK3.post_gamma = 0.65
AGX_CONFIG_LOOK3.tonescale_contrast = 2.0


def transform1(array: numpy.ndarray) -> numpy.ndarray:
    colorspace_dst = _get_colourspace("sRGB")
    return convert_VLog_to_AgX(array, colorspace_dst, AGX_CONFIG_LOOK1)


def transform2(array: numpy.ndarray) -> numpy.ndarray:
    colorspace_dst = _get_colourspace("ITU-R BT.709")
    return convert_VLog_to_AgX(array, colorspace_dst, AGX_CONFIG_LOOK1)


def transform3(array: numpy.ndarray) -> numpy.ndarray:
    def bt1886decoding(x):
        return colour.algebra.spow(x, 1 / 2.4)

    def bt1886encoding(x):
        return colour.algebra.spow(x, 2.4)

    colorspace_dst = _get_colourspace("ITU-R BT.709")
    colorspace_dst.cctf_decoding = bt1886decoding
    colorspace_dst.cctf_encoding = bt1886encoding
    return convert_VLog_to_AgX(array, colorspace_dst, AGX_CONFIG_LOOK1)


def transform4(array: numpy.ndarray) -> numpy.ndarray:
    colorspace_dst = _get_colourspace("sRGB")
    return convert_VLog_to_AgX(array, colorspace_dst, AGX_CONFIG_LOOK2)


def transform5(array: numpy.ndarray) -> numpy.ndarray:
    colorspace_dst = _get_colourspace("sRGB")
    return convert_VLog_to_AgX(array, colorspace_dst, AGX_CONFIG_LOOK3)


def main():
    LOGGER.info("started")

    # lumix S5IIx documentation mentions "33 points" as maximum
    lut_resolution = 33

    # naming convention template (replace between {}):
    # in-{input colorspace}.Agx-{look id}-{workspace colorspace}.out-{output colorspace}
    lut_configs = [
        {"name": "in-VLog.AgX_look1-BT2020.out-sRGB", "func": transform1},
        {"name": "in-VLog.AgX_look1-BT2020.out-BT709", "func": transform2},
        {"name": "in-VLog.AgX_look1-BT2020.out-BT1886", "func": transform3},
        {"name": "in-VLog.AgX_look2-BT2020.out-sRGB", "func": transform4},
        {"name": "in-VLog.AgX_look3-BT2020.out-sRGB", "func": transform5},
    ]

    for lut_config in lut_configs:
        LOGGER.info(f"generating lut {lut_config['name']} size={lut_resolution} ...")
        lut = create_lut(
            lut_config["func"],
            lut_resolution,
            name=lut_config["name"],
            comment="author = Liam Collod",
        )

        lust_dst_dir = THIS_DIR / ".." / "VLog"
        lust_dst_dir.mkdir(exist_ok=True)
        lut_dst_path = lust_dst_dir / f"{lut_config['name']}.cube"

        LOGGER.info(f"writting lut to <{lut_dst_path}>")
        colour.write_LUT(lut, str(lut_dst_path))

    LOGGER.info("finished")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="{levelname: <7} | {asctime} [{name}] {message}",
        style="{",
        stream=sys.stdout,
    )
    main()