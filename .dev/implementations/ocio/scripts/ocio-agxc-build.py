import argparse
import logging
import sys
from pathlib import Path

PARENT_DIR = Path(__file__).parent
ADDITIONAL_MODULES_DIR = str(PARENT_DIR.parent / "python")

if ADDITIONAL_MODULES_DIR not in sys.path:
    print(f"explicitely adding '{ADDITIONAL_MODULES_DIR}' to sys.path")
    sys.path.append(ADDITIONAL_MODULES_DIR)

from ocio_AgXc_config import ConfigVariant
from ocio_AgXc_config import Dcc
from ocio_AgXc_config import AgXcConfig

LOGGER = logging.getLogger(__name__)

_CONFIG_VARIANTS = [
    ConfigVariant("default_OCIO-v1", ocio_version=1, dcc_support=Dcc.none),
    ConfigVariant("default_OCIO-v2", ocio_version=2, dcc_support=Dcc.none),
    ConfigVariant("all-dccs_OCIO-v1", ocio_version=1, dcc_support=Dcc.any),
    ConfigVariant("all-dccs_OCIO-v2", ocio_version=2, dcc_support=Dcc.any),
    ConfigVariant("blender_OCIO-v2", ocio_version=2, dcc_support=Dcc.blender),
    ConfigVariant("redshift_OCIO-v2", ocio_version=2, dcc_support=Dcc.redshift),
]
CONFIG_VARIANTS = {cv.name: cv for cv in _CONFIG_VARIANTS}

DEFAULT_TARGET_DIR = PARENT_DIR.parent.parent.parent.parent / "ocio"


def get_cli(argv=None):
    """
    Retrieve the command line arguments provided by user.
    """
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(
        "agxc-ocio-build",
        description="Create the AgXc OCIO config.",
    )
    default_variants = list(CONFIG_VARIANTS.keys())
    parser.add_argument(
        "--variants",
        type=str,
        nargs="*",
        default=default_variants,
        help="List of config variants to build (default: %(default)s)",
    )
    parser.add_argument(
        "--target_dir",
        type=Path,
        default=DEFAULT_TARGET_DIR,
        help="Filesystem path to an existing directory to export the ocio config in (default: %(default)s)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Display DEBUG logging message.",
    )

    parsed = parser.parse_args(argv)
    return parsed


def main():
    """
    Parse command line arguments and generate the AgXc config on disk.
    """
    cli = get_cli()
    log_level = logging.DEBUG if cli.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="{levelname: <7} | {asctime} [{name}:{funcName}] {message}",
        style="{",
        stream=sys.stdout,
    )

    target_dir: Path = cli.target_dir
    variants: list[str] = cli.variants
    variants: list[ConfigVariant] = [CONFIG_VARIANTS[variant] for variant in variants]

    if not target_dir.exists():
        raise FileNotFoundError(
            f"Target directory must exist on disk. Got <{target_dir}>."
        )

    for index, variant in enumerate(variants):
        LOGGER.info(
            f"{index+1}/{len(variants)} generating ocio config variant {variant}"
        )
        ocio_config = AgXcConfig(variant=variant)
        ocio_config.validate()

        ocio_config_path = target_dir / f"AgXc_{variant.name}"
        if not ocio_config_path.exists():
            LOGGER.debug(f"mkdir({ocio_config_path})")
            ocio_config_path.mkdir()

        ocio_config_path = ocio_config_path / "config.ocio"
        LOGGER.info(f"writing ocio config to <{ocio_config_path}>")
        ocio_config.save_to_disk(ocio_config_path)

        luts_path = ocio_config_path.parent / ocio_config.lut_dir_name
        if not luts_path.exists():
            LOGGER.debug(f"mkdir({luts_path})")
            luts_path.mkdir()

        LOGGER.info(f"writing luts to <{luts_path}>")
        ocio_config.save_luts_to_disk(luts_path)


if __name__ == "__main__":
    main()
