import logging
import math
import shutil
import subprocess
import sys
from pathlib import Path

import OpenImageIO as oiio
import PyOpenColorIO as ocio
import numpy

LOGGER = logging.getLogger(Path(__file__).name)
THISDIR = Path(__file__).parent

OUTPUTS_DIR = THISDIR / "_outputs"

OCIO_DIR = THISDIR.parent.parent.parent.parent.parent / "ocio"


def _oiiotool_export(
    base_command: list[str],
    target_path: Path,
    bitdepth: str,
    compression: str = None,
    srgb_encoded: bool = False,
):
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

    LOGGER.debug(f"subprocess.run('{' '.join(command)}')")
    subprocess.run(command, check=True, text=True)


def generate_image_src(
    image_path,
    width: int,
    height: int,
    bitdepth: str,
    compression: str = None,
    srgb_encoded: bool = False,
    text_msg: str = "AgXc",
):
    """
    Generate a synthetic OpenEXR test image on disk.

    The visual consists of:
    - a noisy colored background with a 64px size checker overlaid
    - 2 side gradually linear ramp with the left in [0-16] range and right [0-1]
    - a central text box

    ! The generation of those images is not guaranteed to produce the exact same values
    between machines and platforms.

    Args:
        image_path: fileystem path to a file to write to.
        width: width of the image is to create in pixels
        height: height of the image is to create in pixels
        bitdepth: bitdepth of the file to write to. must be compatible with the file format.
        compression: compression of the file to write to. must be compatible with the file format.
        srgb_encoded: True to apply sRGB EOTF on encoding, False to keep it linear.
        text_msg: text to display on the image center.
    """
    sizex = f"{width}x{height}"
    gen_command: list[str] = [
        # diagonal colored gradient
        f"--pattern fill:topleft=.1,.1,.1,0.5:topright=1,0,0,0.7:bottomleft=0,1,0,0.3:bottomright=0,0,1,0.3 {sizex} 4",
        # checkerboard pattern
        f"--pattern checker:width=64:height=64:color1=.2,.2,.2,1:color2=.6,.6,.6,1 {sizex} 4",
        "--over",
        # add noise
        "--noise:type=gaussian:seed=666:nchannels=3",
    ]

    # centered horizontal/vertical lines
    x_center = round(width / 2)
    y_center = round(height / 2)
    line_color = "1,1,1,1"
    gen_command += [
        f"--line:color={line_color} {0},{y_center},{width},{y_center}",
        f"--line:color={line_color} {x_center},{height},{x_center},{0}",
        # add one pixel thickness
        f"--line:color={line_color} {0},{y_center+1},{width},{y_center+1}",
        f"--line:color={line_color} {x_center+1},{height},{x_center+1},{0}",
        # add one pixel thickness again (so final width = 3 pixels)
        f"--line:color={line_color} {0},{y_center-1},{width},{y_center-1}",
        f"--line:color={line_color} {x_center-1},{height},{x_center-1},{0}",
    ]

    # top-bottom gradient with huge value range, on the left
    width_10p = round(width * 0.1)
    height_70p = round(height * 0.7)
    offset_x_5p = round(width * 0.05)
    offset_y_center = round((height - height_70p) / 2)
    gen_command += [
        f"--pattern fill:bottom=0,0,0,1:top=16,16,16,1 {width_10p}x{height_70p}+{offset_x_5p}+{offset_y_center} 4",
        "--swap --over",
    ]

    # top-bottom gradient with h0-1 range, on the right
    offset_x_5pright = width - round(width * 0.05) - width_10p
    gen_command += [
        f"--pattern fill:bottom=0,0,0,1:top=1,1,1,1 {width_10p}x{height_70p}+{offset_x_5pright}+{offset_y_center} 4",
        "--swap --over",
    ]

    # create a box with 25% spacing and a 3pixel line thickness
    dist_x_25 = round(width / 4)
    dist_x_75 = round(width / 4 * 3)
    dist_y_25 = round(height / 4)
    dist_y_75 = round(height / 4 * 3)
    line_color = "1,1,0,1"
    gen_command += [
        f"--box:color={line_color} {dist_x_25},{dist_y_25},{dist_x_75},{dist_y_75}",
        f"--box:color={line_color} {dist_x_25-1},{dist_y_25-1},{dist_x_75-1},{dist_y_75-1}",
        f"--box:color={line_color} {dist_x_25-2},{dist_y_25-2},{dist_x_75-2},{dist_y_75-2}",
    ]

    # create a darker centered box behind the upcoming text
    text_height = round(height * 0.2)
    xmin = round(x_center - text_height)
    xmax = round(x_center + text_height)
    ymin = round(y_center + text_height / 2 + text_height * 0.1)
    ymax = round(y_center - text_height / 2 - text_height * 0.1)
    gen_command += [
        f"--box:color=0,0,0.05,0.5:fill=1 {xmin},{ymax},{xmax},{ymin}",
        # we also want the box to affect the alpha with a value of 0.5, thus
        # creating a box that is already premultiplied
        f"--pattern fill:color=0,0,0,0.5 {sizex} 4",
        f"--crop {xmin},{ymax},{xmax},{ymin}",
        "--sub",
    ]

    # create a basic centered text
    gen_command += [
        f"--text:x={x_center}:y={y_center}:xalign=center:yalign=center:size={text_height}",
        f"{text_msg}",
    ]

    gen_command = " ".join(gen_command).split(" ")

    _oiiotool_export(
        base_command=gen_command,
        target_path=image_path,
        bitdepth=bitdepth,
        compression=compression,
        srgb_encoded=srgb_encoded,
    )


def generate_contact_sheet(
    image_paths: list[Path],
    target_path: Path,
    bitdepth: str,
    header: str = "",
    max_columns: int = 4,
    gap_size: int = 12,
    srgb_encoded: bool = False,
    compression: str = None,
):

    if len(image_paths) <= max_columns:
        tiles_w, tiles_h = (len(image_paths), 1)
    else:
        tiles_w = max_columns
        tiles_h = math.ceil(len(image_paths) / max_columns)

    gen_command = []
    for path in image_paths:
        gen_command += [
            "-i",
            str(path),
            "--ch",
            "R,G,B",
            "--box:color=0,0,0,0.8:fill=1",
            "0,{TOP.height-24},{TOP.width},{TOP.height}",
            # bottom-left text with 10px margin
            "--text:x=10:y={TOP.height-8}:shadow=0:size=12:color=1,1,1,1",
            f"{path.stem.split('__', 1)[-1]}",
        ]
    gen_command += [
        f"--mosaic:pad={gap_size}",
        f"{tiles_w}x{tiles_h}",
        "--cut",
        "-{0},-{1},{{TOP.width+{0}}},{{TOP.height+{0}}}".format(
            gap_size, gap_size + 20
        ),
    ]
    if header:
        gen_command += [
            "--text:x=10:y=18:shadow=0:size=14:color=1,1,1,1",
            header,
        ]
    _oiiotool_export(
        base_command=gen_command,
        target_path=target_path,
        bitdepth=bitdepth,
        compression=compression,
        srgb_encoded=srgb_encoded,
    )


def get_config_version(config_path: Path) -> str | None:
    content = config_path.read_text("utf-8")
    for line in content.splitlines():
        buf = line.replace(" ", "")
        if buf.startswith("#version:"):
            return buf.replace("#version:", "").strip(" ")
    return None


def main(output_dir: Path):

    configs_version_path = OCIO_DIR / ".version"
    configs_version = configs_version_path.read_text("utf-8")

    output_dir.mkdir(exist_ok=True)
    target_root_dir = output_dir / configs_version
    if target_root_dir.exists():
        shutil.rmtree(target_root_dir)
    target_root_dir.mkdir()

    src_image_path = target_root_dir / "src.exr"
    generate_image_src(
        src_image_path,
        width=200,
        height=200,
        bitdepth="float",
        compression="zips",
    )
    src_image: oiio.ImageInput = oiio.ImageInput.open(str(src_image_path))
    src_image: numpy.ndarray = src_image.read_image(chbegin=0, chend=4, format="float")

    outputs_by_config: dict[Path, list[Path]] = {}

    config_paths = list(OCIO_DIR.glob("**/config.ocio"))
    config_paths_n = len(config_paths)
    for index, config_path in enumerate(config_paths):
        config_path = Path(config_path)
        config: ocio.Config = ocio.Config.CreateFromFile(str(config_path))
        config.validate()
        target_dir = target_root_dir / config_path.parent.name
        target_dir.mkdir(exist_ok=True)

        colorspaces: list[ocio.ColorSpace] = list(config.getColorSpaces())
        colorspaces_n = len(colorspaces)
        for subindex, colorspace in enumerate(colorspaces):
            src_colorspace = "scene_linear"
            dst_colorspace = colorspace.getName()

            prefix = f"[{index+1}/{config_paths_n} - {subindex+1}/{colorspaces_n}]"
            LOGGER.info(f"{prefix} processing {src_colorspace} > {dst_colorspace}")
            processor = config.getProcessor(src_colorspace, dst_colorspace)
            cpu: ocio.CPUProcessor = processor.getDefaultCPUProcessor()
            buf = src_image.copy()
            cpu.applyRGBA(buf)
            buf = oiio.ImageBuf(buf)

            target_path = target_dir / f"{src_colorspace}__{dst_colorspace}.exr"
            LOGGER.info(f"writing {target_path}")
            buf.write(str(target_path))

            outputs_by_config.setdefault(config_path, []).append(target_path)

        mosaic_path = target_dir / "mosaic.jpg"
        header = f"{config_path.parent.name} (v{configs_version})"
        generate_contact_sheet(
            image_paths=outputs_by_config[config_path],
            target_path=mosaic_path,
            bitdepth="uint8",
            header=header,
            max_columns=5,
            compression="jpeg:99",
            srgb_encoded=False,
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="{levelname: <7} | {asctime} [{name}:{funcName}] {message}",
        style="{",
        stream=sys.stdout,
    )
    main(output_dir=OUTPUTS_DIR)
