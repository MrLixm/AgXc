import dataclasses
import logging
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

LOGGER = logging.getLogger(__name__)
PARENT_DIR = Path(__file__).parent
REPO_ROOT = PARENT_DIR.parent.parent.parent.parent

SOURCE_ASSETS_DIR = REPO_ROOT / ".dev" / "assets"
TARGET_DOC_DIR = REPO_ROOT / "doc"

# https://www.colour-science.org:8010/apps/rgb_colourspace_transformation_matrix?input-colourspace=ACES2065-1&output-colourspace=sRGB&chromatic-adaptation-transform=CAT02&formatter=str&decimals=6
AP0_TO_SRGB = [
    2.521649,
    -1.136889,
    -0.384918,
    -0.275214,
    1.369705,
    -0.094392,
    -0.015925,
    -0.147806,
    1.163806,
]


def _oiiotool_export(
    base_command: list[str],
    target_path: Path,
    bitdepth: str,
    compression: str = None,
    srgb_encoded: bool = False,
) -> list[str]:
    output_command = ["-d", bitdepth]
    if srgb_encoded:
        output_command += ["--colorconvert", "linear", "sRGB"]
    if compression:
        output_command += ["--compression", compression]
    output_command += ["-o", str(target_path)]

    oiiotoolpath = shutil.which("oiiotool")
    if not oiiotoolpath:
        raise FileNotFoundError("Could not find oiiotool program on system.")

    command = [oiiotoolpath] + base_command + output_command
    return command


def oiiotool_ocio_render(
    src_path: Path,
    dst_path: Path,
    text_left: tuple[str, str],
    text_right: str,
    ocio_config: Path,
    ocio_display: str,
    ocio_view: str,
    ocio_srgb_lin: str,
    ocio_look: str = "",
) -> list[str]:
    command = ["-i", str(src_path)]
    command += [
        # all images are assumed to be ACES2065-1 encoded
        "--ccmatrix:transpose=1",
        ",".join(map(str, AP0_TO_SRGB)),
        "--colorconfig",
        str(ocio_config),
    ]
    if ocio_look:
        command += [
            f"--ociolook:from={ocio_srgb_lin}:to={ocio_srgb_lin}",
            ocio_look,
        ]
    command += [
        f"--ociodisplay:from={ocio_srgb_lin}",
        ocio_display,
        ocio_view,
    ]
    command += [
        "--resize:filter=box",
        "0x864",
        "--cut",
        "0,0,{TOP.width},{TOP.height+100}",
        "--text:x=40:y={TOP.height-47}:shadow=0:size=34:color=1,1,1,1:yalign=bottom",
        text_left[0],
        "--text:x=40:y={TOP.height-42}:shadow=0:size=24:color=1,1,1,1:yalign=top",
        text_left[1],
        "--text:x={TOP.width-40}:y={TOP.height-45}:shadow=0:size=34:color=1,1,1,1:yalign=center:xalign=right",
        text_right,
    ]
    return _oiiotool_export(
        base_command=command,
        target_path=dst_path,
        bitdepth="uint8",
        compression="jpeg:98",
        srgb_encoded=False,
    )


def oiiotool_generate_expo_bands(
    src_path: Path,
    dst_path: Path,
    text_left: str,
    text_right: str,
    ocio_config: Path,
    ocio_display: str,
    ocio_view: str,
    ocio_srgb_lin: str,
    ocio_look: str = "",
    band_number: int = 7,
    band_exposure_offset: int = 2,
    band_width: float = 0.3,
    band_x_offset: float = 0.0,
) -> list[str]:

    if band_number % 2 == 0:
        raise ValueError(f"band_number can only be an odd number; got {band_number}")

    command = []

    middle_index = math.ceil(band_number / 2)
    limits = band_exposure_offset * (middle_index - 1)
    bands: list[int] = list(range(limits * -1, limits + 1, band_exposure_offset))
    for band_exposure in bands:
        command += [
            "-i",
            str(src_path),
            "--cut",
            f"{{TOP.width//{1/band_width:.2f}}}x{{TOP.height}}+{{TOP.width//{1 / band_x_offset:.2f}}}+0",
            "--mulc",
            str(round(2**band_exposure, 2)),
        ]
        command += [
            # all images are assumed to be ACES2065-1 encoded
            "--ccmatrix:transpose=1",
            ",".join(map(str, AP0_TO_SRGB)),
            "--colorconfig",
            str(ocio_config),
        ]
        if ocio_look:
            command += [
                f"--ociolook:from={ocio_srgb_lin}:to={ocio_srgb_lin}",
                ocio_look,
            ]
        command += [
            f"--ociodisplay:from={ocio_srgb_lin}",
            ocio_display,
            ocio_view,
        ]
        command += [
            "--text:x={TOP.width/2}:y={TOP.height-25}:shadow=4:size=44:color=1,1,1,1",
            f"{band_exposure:+}",
        ]
    command += [
        "--mosaic",
        f"{len(bands)}x1",
        "--resize:filter=box",
        "0x864",
        "--cut",
        "0,0,{TOP.width},{TOP.height+100}",
        "--text:x=40:y={TOP.height-45}:shadow=0:size=34:color=1,1,1,1:yalign=center",
        text_left,
        "--text:x={TOP.width-40}:y={TOP.height-45}:shadow=0:size=24:color=1,1,1,1:yalign=center:xalign=right",
        text_right,
    ]
    return _oiiotool_export(
        base_command=command,
        target_path=dst_path,
        bitdepth="uint8",
        compression="jpeg:98",
        srgb_encoded=False,
    )


def oiiotool_tile(images: list[Path], dst_path: Path) -> list[str]:
    command = []
    for image in images:
        command += ["-i", str(image)]

    columns = math.ceil(math.sqrt(len(images)))
    rows = math.ceil(len(images) / columns)
    command += [
        "--mosaic",
        f"{columns}x{rows}",
        "--resize:filter=box",
        "0x1080",
    ]
    return _oiiotool_export(
        base_command=command,
        target_path=dst_path,
        bitdepth="uint8",
        compression="jpeg:98",
        srgb_encoded=False,
    )


@dataclasses.dataclass
class OcioConfigRenderer:
    name: str
    filename: str
    config_path: Path
    # this is a hack as tehre is more chance an OCIO config has a sRGB-lin colorspace than ACES2065-1
    srgb_lin: str
    display: str
    view: str
    look: str = ""

    def generate_exposure_bands(
        self,
        src_path: Path,
        dst_path: Path,
        band_x_offset: float,
    ):
        look_str = f", look='{self.look}'" if self.look else ""
        command = oiiotool_generate_expo_bands(
            src_path=src_path,
            dst_path=dst_path,
            text_left=f"{src_path.stem} - {self.name}",
            text_right=f"(display='{self.display}', view='{self.view}'{look_str})",
            ocio_config=self.config_path,
            ocio_display=self.display,
            ocio_view=self.view,
            ocio_srgb_lin=self.srgb_lin,
            ocio_look=self.look,
            band_number=7,
            band_width=0.2,
            band_exposure_offset=2,
            band_x_offset=band_x_offset,
        )
        LOGGER.debug(f"subprocess.run({command})")
        subprocess.run(command)

    def generate_full_render(
        self,
        src_path: Path,
        dst_path: Path,
    ):
        look_str = f", look='{self.look}'" if self.look else ""
        command = oiiotool_ocio_render(
            src_path=src_path,
            dst_path=dst_path,
            text_left=(
                f"{self.name}",
                f"(display='{self.display}', view='{self.view}'{look_str})",
            ),
            text_right=f"{src_path.stem}",
            ocio_config=self.config_path,
            ocio_display=self.display,
            ocio_view=self.view,
            ocio_srgb_lin=self.srgb_lin,
            ocio_look=self.look,
        )
        LOGGER.debug(f"subprocess.run({command})")
        subprocess.run(command)


@dataclasses.dataclass
class SourceAsset:
    path: Path
    exposure_bands_offset: float  # 0-1 range, percentage of image width
    skip_bands: bool = False


def main(target_dir: Path):

    agxc_path = REPO_ROOT / "ocio" / "AgXc_default_OCIO-v2" / "config.ocio"
    agxc_version = Path(REPO_ROOT, "ocio", ".version").read_text("utf-8")

    src_assets = [
        SourceAsset(
            path=SOURCE_ASSETS_DIR / "CAlc-D8T-dragon.exr",
            exposure_bands_offset=0.45,
        ),
        SourceAsset(
            path=SOURCE_ASSETS_DIR / "Cblr-GFD-spring.exr",
            exposure_bands_offset=0.3,
        ),
        SourceAsset(
            path=SOURCE_ASSETS_DIR / "PAmsk-R65-christmas.exr",
            exposure_bands_offset=0.3,
        ),
        SourceAsset(
            path=SOURCE_ASSETS_DIR / "PWdc-85R-braidmaker.exr",
            exposure_bands_offset=0.3,
        ),
        SourceAsset(
            path=SOURCE_ASSETS_DIR / "CGts-W0L-sweep.exr",
            exposure_bands_offset=0,
            skip_bands=True,
        ),
        SourceAsset(
            path=SOURCE_ASSETS_DIR / "CAtm-FGH-specbox.exr",
            exposure_bands_offset=0,
            skip_bands=True,
        ),
    ]

    renderers = [
        OcioConfigRenderer(
            name=f"AgXc_default-v{agxc_version}",
            filename="AgXc",
            config_path=agxc_path,
            srgb_lin="sRGB-linear",
            display="sRGB-2.2",
            view="AgXc.base Punchy",
        ),
        # OcioConfigRenderer(
        #     name="ACES v2.1.0_aces-v1.3_ocio-v2.3",
        #     filename="ACES",
        #     config_path=Path(
        #         r"F:\softwares\apps\ocio\configs\aces-official\cg-2.0.0\2.1.0\cg-config-v2.1.0_aces-v1.3_ocio-v2.3.ocio"
        #     ),
        #     srgb_lin="Linear Rec.709 (sRGB)",
        #     display="sRGB - Display",
        #     view="ACES 1.0 - SDR Video",
        # ),
        OcioConfigRenderer(
            name="ACES v2.1.0_aces-v1.3_ocio-v2.3 + GM",
            filename="ACES-gm",
            config_path=Path(
                r"F:\softwares\apps\ocio\configs\aces-official\cg-2.0.0\2.1.0\cg-config-v2.1.0_aces-v1.3_ocio-v2.3.ocio"
            ),
            srgb_lin="Linear Rec.709 (sRGB)",
            display="sRGB - Display",
            view="ACES 1.0 - SDR Video",
            look="ACES 1.3 Reference Gamut Compression",
        ),
        # OcioConfigRenderer(
        #     name="spi-anim",
        #     filename="spi-anim",
        #     config_path=Path(
        #         r"F:\softwares\apps\ocio\configs\imageworks\0bb079c\spi-anim\config.ocio"
        #     ),
        #     srgb_lin="lnf",
        #     display="sRGB",
        #     view="Film",
        # ),
        OcioConfigRenderer(
            name="native (no image rendering)",
            filename="native",
            config_path=agxc_path,
            srgb_lin="sRGB-linear",
            display="sRGB-2.2",
            view="Display Native",
        ),
        OcioConfigRenderer(
            name="Blender Filmic",
            filename="filmic",
            config_path=Path(
                r"F:\softwares\apps\ocio\configs\filmic\1.1.0\config.ocio"
            ),
            srgb_lin="Linear",
            display="sRGB",
            view="Filmic Log Encoding Base",
            look="Base Contrast",
        ),
    ]

    stime = time.time()

    if not target_dir.exists():
        LOGGER.debug(f"mkdir('{target_dir}')")
        target_dir.mkdir()

    target_dir = target_dir / "images"
    if not target_dir.exists():
        LOGGER.debug(f"mkdir('{target_dir}')")
        target_dir.mkdir()

    # TODO there is surely a loot of room to speedup the below code by parallelizing
    #   the subprocesses execution.

    for src_asset in src_assets:

        src_path: Path = src_asset.path
        target_src_dir = target_dir / src_asset.path.stem
        if target_src_dir.exists():
            LOGGER.debug(f"rmtree({target_src_dir})")
            shutil.rmtree(target_src_dir)
        LOGGER.debug(f"mkdir({target_src_dir})")
        target_src_dir.mkdir()

        bands_outputs = []
        full_outputs = []

        for renderer in renderers:
            dst_path = target_src_dir / f"{src_path.stem}.full.{renderer.filename}.jpg"
            LOGGER.info(f"generating '{dst_path.name}' ...")
            renderer.generate_full_render(
                src_path=src_path,
                dst_path=dst_path,
            )
            full_outputs.append(dst_path)

            if src_asset.skip_bands:
                continue

            dst_path = (
                target_src_dir / f"{src_path.stem}.exposures.{renderer.filename}.jpg"
            )
            LOGGER.info(f"generating '{dst_path.name}' ...")
            renderer.generate_exposure_bands(
                src_path=src_path,
                dst_path=dst_path,
                band_x_offset=src_asset.exposure_bands_offset,
            )
            bands_outputs.append(dst_path)

        if bands_outputs:
            # create a mosaic which combine all the image created by the renderers
            dst_path = target_src_dir / f"{src_path.stem}.exposures.overview.jpg"
            LOGGER.info(f"generating '{dst_path.name}' ...")
            command = oiiotool_tile(bands_outputs, dst_path)
            LOGGER.debug(f"subprocess.run({command})")
            subprocess.run(command)

        if full_outputs:
            dst_path = target_src_dir / f"{src_path.stem}.full.overview.jpg"
            LOGGER.info(f"generating '{dst_path.name}' ...")
            command = oiiotool_tile(full_outputs, dst_path)
            LOGGER.debug(f"subprocess.run({command})")
            subprocess.run(command)

    etime = time.time() - stime
    LOGGER.info(f"finished in {etime:.1f}s")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="{levelname: <7} | {asctime} [{name}:{funcName}] {message}",
        style="{",
        stream=sys.stdout,
    )
    main(TARGET_DOC_DIR)
