import argparse
import dataclasses
import datetime
import enum
import logging
import sys
from pathlib import Path
from typing import Optional

import PyOpenColorIO as ocio
import colour
import numpy

import AgXLib

LOGGER = logging.getLogger(__name__)
PARENT_DIR = Path(__file__).parent

ADDITIONAL_MODULES_DIR = str(PARENT_DIR / "modules")

if ADDITIONAL_MODULES_DIR not in sys.path:
    sys.path.append(ADDITIONAL_MODULES_DIR)

from ocio_matrix_generation import matrix_primaries_transform_ocio
from ocio_matrix_generation import matrix_format_ocio
from ocio_config_helpers import View
from ocio_config_helpers import BaseFamily
from ocio_config_helpers import build_ocio_colorspace
from ocio_config_helpers import build_display_views
from ocio_config_helpers import ImageColorspace


class AgXcFamily(BaseFamily):
    """
    The various families used to categorise colorspaces
    """

    colorspaces = "Colorspaces"
    agx = "AgX"
    util_curves = "Utilities/Curves"
    views = "Views"


class AgXcConfigVariant(enum.Enum):
    default_ociov1 = "default_OCIO-v1"
    default_ociov2 = "default_OCIO-v2"

    @classmethod
    def get_all(cls):
        return [
            cls.default_ociov1,
            cls.default_ociov2,
        ]


class AgXcConfig(ocio.Config):
    version = "0.2.5"
    lut_dir_name = "LUTs"
    default_cat = "Bradford"
    decimal_precision = 12

    def __init__(self, variant: AgXcConfigVariant):
        super().__init__()

        self._variant = variant

        self.use_ocio_v1 = self._variant is self._variant.default_ociov1

        self.header: list[str] = [
            f"# version: {self.version}",
            f"# name: AgXc",
            f"# variant: {variant.value}",
            f"# built on: {datetime.datetime.now()}",
            "# // visit https://github.com/MrLixm/AgXc",
            "# // and inspect the python build script for details",
        ]
        self.overrides: list[str] = []
        self.lut_sRGB = "sRGB-EOTF-inverse.spi1d"
        self.lut_AgX = "AgX_Default_Contrast.spi1d"
        self._luts: dict[str, colour.LUT1D] = {}

        self.look_punchy = "Punchy"
        self.looks = [
            self.look_punchy,
        ]

        self.colorspace_Linear_sRGB = "sRGB-linear"
        self.colorspace_AgX_Log = "AgX-Log-(Kraken)"
        self.colorspace_EOTF_2_2 = "2.2-EOTF-Encoding"
        self.colorspace_EOTF_2_4 = "2.4-EOTF-Encoding"
        self.colorspace_sRGB_2_2 = "sRGB-2.2"
        self.colorspace_sRGB_EOTF = "sRGB-EOTF"
        self.colorspace_Display_P3 = "Display-P3"
        self.colorspace_BT_1886 = "BT.1886"
        self.colorspace_AgX_Base = "AgX"
        self.colorspace_Passthrough = "Passthrough"
        self.colorspace_ACEScg = "ACEScg"
        self.colorspace_ACES20651 = "ACES2065-1"
        self.colorspace_CIE_XYZ_D65 = "CIE-XYZ-D65"
        self.colorspace_Linear_BT2020 = "BT.2020-linear"

        self.display_colorspaces = [
            self.colorspace_sRGB_2_2,
            self.colorspace_sRGB_EOTF,
            self.colorspace_Display_P3,
            self.colorspace_BT_1886,
        ]

        self.image_renderings = [
            self.colorspace_AgX_Base,
        ]

        self.image_colorspaces: list[ImageColorspace] = []

        # we do a matrix of image_rendering x look x display_colorspace to define how
        # much "image" colorspace we need to create
        for image_rendering in self.image_renderings:
            for look in [None] + self.looks:
                for display_colorspace in self.display_colorspaces:
                    image_colorspace = ImageColorspace(
                        image_rendering=image_rendering,
                        display_colorspace=display_colorspace,
                        look=look,
                    )
                    self.image_colorspaces.append(image_colorspace)

        if self.use_ocio_v1:
            self.setVersion(1, 0)
            self.overrides = [
                "",
                # XXX: this is ignored by OCIO on v1 API but we want to keep it
                "name: AgXc",
                "",
                # XXX: this is ignored by OCIO on v1 API but we want to keep it but
                #   as some apps spit out warning without
                "environment: {}",
            ]

        else:
            self.setVersion(2, 0)
            self.setName("AgXc")

        self.setDescription(
            "AgX image rendering initially designed by Troy Sobotka.\n"
            "Adapted by Liam Collod with full permissions from Troy Sobotka.\n"
            f"C.A.T. used for whitepoint conversions is <{self.default_cat}>.\n"
        )
        self.setStrictParsingEnabled(True)
        self.setSearchPath(self.lut_dir_name)

        self.setRole("color_picking", self.colorspace_sRGB_2_2)
        self.setRole("color_timing", self.colorspace_sRGB_2_2)
        self.setRole("compositing_log", self.colorspace_AgX_Log)
        self.setRole("data", self.colorspace_Passthrough)
        self.setRole("default", self.colorspace_sRGB_2_2)
        self.setRole("default_byte", self.colorspace_sRGB_2_2)
        self.setRole("default_float", self.colorspace_Linear_sRGB)
        self.setRole("default_sequencer", self.colorspace_sRGB_2_2)
        self.setRole("matte_paint", self.colorspace_sRGB_2_2)
        self.setRole("reference", self.colorspace_Linear_sRGB)
        self.setRole("scene_linear", self.colorspace_Linear_sRGB)
        self.setRole("texture_paint", self.colorspace_sRGB_2_2)
        self.setRole("aces_interchange", self.colorspace_ACES20651)
        self.setRole("cie_xyz_d65_interchange", self.colorspace_CIE_XYZ_D65)

        self._build_looks()
        self._build_colorspaces()
        self._build_luts()
        self._build_display_view()

    def _build_luts(self):
        lut_domain = [0.0, 1.0]
        array = colour.LUT1D.linear_table(4096, lut_domain)
        array = colour.models.RGB_COLOURSPACE_sRGB.cctf_decoding(array)
        lut = colour.LUT1D(
            table=array,
            name="sRGB EOTF decoding",
            domain=lut_domain,
            comments=[
                "sRGB IEC 61966-2-1 2.2 Exponent Reference EOTF Display. Decoding function."
            ],
        )
        self._luts[self.lut_sRGB] = lut

        lut_domain = [0.0, 1.0]
        array = colour.LUT1D.linear_table(4096, lut_domain)
        array = AgXLib.apply_AgX_tonescale(array)
        lut = colour.LUT1D(
            table=array,
            name="sRGB EOTF decoding",
            domain=lut_domain,
            comments=[
                "AgX 1D tonescale with following configuration",
                "   min_EV = -10.0",
                "   max_EV = +6.5",
                "   general_contrast = 2.0",
                "   limits_contrast = (3.0, 3.25)",
            ],
        )
        self._luts[self.lut_AgX] = lut

    def _build_looks(self):
        look = ocio.Look(
            name=self.look_punchy,
            processSpace=self.colorspace_AgX_Base,
            description="A punchy and more chroma laden look.",
            transform=ocio.CDLTransform(power=[1.3, 1.3, 1.3], sat=1.2),
        )
        self.addLook(look)

    def _build_colorspaces(self):
        colorspaces = colour.RGB_COLOURSPACES
        illum_1931 = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]
        whitepoint_d65 = illum_1931["D65"]

        reference_colorspace: colour.RGB_Colourspace = colorspaces["sRGB"]
        reference_colorspace.use_derived_transformation_matrices(True)

        def get_conversion_matrix(colorspace_name: str) -> list[float]:
            if colorspace_name == "XYZ":
                _src = "XYZ"
                _src_whitepoint = whitepoint_d65
            else:
                _src: colour.RGB_Colourspace = colorspaces[colorspace_name]
                _src.use_derived_transformation_matrices(True)
                _src_whitepoint = _src.whitepoint
            return matrix_primaries_transform_ocio(
                source=reference_colorspace,
                target=_src,
                source_whitepoint=reference_colorspace.whitepoint,
                target_whitepoint=_src_whitepoint,
                cat=self.default_cat,
                decimals=self.decimal_precision,
            )

        transform_eotf_22 = ocio.ExponentTransform(
            value=[2.2, 2.2, 2.2, 1],
            direction=ocio.TRANSFORM_DIR_INVERSE,
        )
        transform_eotf_24 = ocio.ExponentTransform(
            value=[2.4, 2.4, 2.4, 1],
            direction=ocio.TRANSFORM_DIR_INVERSE,
        )
        transform_eotf_srgb = ocio.FileTransform(
            src=self.lut_sRGB,
            interpolation=ocio.INTERP_LINEAR,
        )

        # // utilities

        with build_ocio_colorspace(self.colorspace_EOTF_2_2, self) as colorspace:
            colorspace.description = "transfer-function: 2.2 Exponent EOTF Encoding"
            colorspace.family = AgXcFamily.util_curves
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference([transform_eotf_22])

        with build_ocio_colorspace(self.colorspace_EOTF_2_4, self) as colorspace:
            colorspace.description = "transfer-function: 2.4 Exponent EOTF Encoding"
            colorspace.family = AgXcFamily.util_curves
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference([transform_eotf_24])

        # // display-referred colorspaces

        with build_ocio_colorspace(self.colorspace_sRGB_2_2, self) as colorspace:
            colorspace.description = (
                "sRGB with transfer-function simplified to the 2.2 power function."
            )
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0.0, 1.0]
            colorspace.set_transforms_from_reference([transform_eotf_22])

        with build_ocio_colorspace(self.colorspace_sRGB_EOTF, self) as colorspace:
            colorspace.description = 'sRGB IEC 61966-2-1 2.2 Exponent Reference EOTF Display\nThis "colorspace" is required by Redshift.'
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0.0, 1.0]
            colorspace.set_transforms_to_reference([transform_eotf_srgb])

        with build_ocio_colorspace(self.colorspace_Display_P3, self) as colorspace:
            colorspace.description = (
                "Display P3 2.2 Exponent EOTF Display. For Apple hardware."
            )
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0.0, 1.0]

            matrix = get_conversion_matrix("DCI-P3")
            colorspace.set_transforms_from_reference(
                [
                    ocio.MatrixTransform(matrix=matrix),
                    transform_eotf_22,
                ]
            )

        with build_ocio_colorspace(self.colorspace_BT_1886, self) as colorspace:
            colorspace.description = "BT.1886 2.4 Exponent EOTF Display. Also known as Rec.709 transfer function."
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference([transform_eotf_24])

        # // AgX colorspaces

        with build_ocio_colorspace(self.colorspace_AgX_Log, self) as colorspace:
            colorspace.description = "AgX Log (Kraken)"
            colorspace.family = AgXcFamily.agx
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocationVars = [-12.47393, 4.026069]

            inset_matrix = AgXLib.get_reshaped_colorspace_matrix(
                src_gamut=reference_colorspace.primaries,
                src_whitepoint=reference_colorspace.whitepoint,
                inset_r=0.2,
                inset_g=0.2,
                inset_b=0.2,
            )
            inset_matrix = matrix_format_ocio(numpy.linalg.inv(inset_matrix))

            if self.use_ocio_v1:
                # hack to clamp negatives only, in OCIOv1
                clamp_transform = [
                    ocio.CDLTransform(power=[2.0, 2.0, 2.0]),
                    # 2nd one has a minuscule offset else considered no-op and no clamp applied
                    ocio.CDLTransform(power=[0.500001, 0.500001, 0.500001]),
                ]
            else:
                clamp_transform = [
                    ocio.RangeTransform(minInValue=0.0, minOutValue=0.0),
                ]

            colorspace.set_transforms_from_reference(
                clamp_transform
                + [
                    ocio.MatrixTransform(matrix=inset_matrix),
                    ocio.AllocationTransform(
                        allocation=ocio.ALLOCATION_LG2,
                        vars=[-12.47393, 4.026069],
                    ),
                ]
            )

        with build_ocio_colorspace(self.colorspace_AgX_Base, self) as colorspace:
            colorspace.description = (
                "AgX Base Image Encoding, output is already display encoded."
            )
            colorspace.family = AgXcFamily.agx
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_AgX_Log,
                    ),
                    ocio.FileTransform(
                        src=self.lut_AgX,
                        interpolation=ocio.INTERP_LINEAR,
                    ),
                ]
            )

        # // open-domain colorspaces

        with build_ocio_colorspace(self.colorspace_Passthrough, self) as colorspace:
            colorspace.description = (
                'Passthrough means no transformations. Also know as "raw".'
            )
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocationVars = [0, 1]
            colorspace.isData = True
            colorspace.equalityGroup = "scalar"

        with build_ocio_colorspace(self.colorspace_Linear_sRGB, self) as colorspace:
            colorspace.description = "Open Domain Linear BT.709 Tristimulus"
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-10, 7, 0.0056065625]

        with build_ocio_colorspace(self.colorspace_ACEScg, self) as colorspace:
            colorspace.description = "ACES rendering space for CGI. Also known as AP1."
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-8, 5, 0.00390625]

            matrix = get_conversion_matrix("ACEScg")
            colorspace.set_transforms_from_reference(
                [
                    ocio.MatrixTransform(matrix=matrix),
                ]
            )

        with build_ocio_colorspace(self.colorspace_ACES20651, self) as colorspace:
            colorspace.description = "ACES Interchange format. Also known as AP0."
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-8, 5, 0.00390625]

            matrix = get_conversion_matrix("ACES2065-1")
            colorspace.set_transforms_from_reference(
                [
                    ocio.MatrixTransform(matrix=matrix),
                ]
            )

        with build_ocio_colorspace(self.colorspace_CIE_XYZ_D65, self) as colorspace:
            colorspace.description = "CIE 1931 Colorspace with a D65 whitepoint."
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-8, 5, 0.00390625]

            matrix = get_conversion_matrix("XYZ")
            colorspace.set_transforms_from_reference(
                [
                    ocio.MatrixTransform(matrix=matrix),
                ]
            )

        with build_ocio_colorspace(self.colorspace_Linear_BT2020, self) as colorspace:
            colorspace.name = self.colorspace_Linear_BT2020
            colorspace.description = (
                "The ITU-R BT.2020 colorspace with a linear transfer-function.\n"
                "A very wide gamut on the edge of the spectral locus, with a D65 whitepoint."
            )
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-8, 5, 0.00390625]

            matrix = get_conversion_matrix("ITU-R BT.2020")
            colorspace.set_transforms_from_reference(
                [
                    ocio.MatrixTransform(matrix=matrix),
                ]
            )

        # // closed-domain colorspaces (display-referred)

        for image_colorspace in self.image_colorspaces:
            with build_ocio_colorspace(image_colorspace.name, self) as colorspace:
                colorspace.description = image_colorspace.description
                colorspace.family = AgXcFamily.views
                colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
                if self.use_ocio_v1:
                    colorspace.allocationVars = [0, 1]
                colorspace.set_transforms_from_reference(image_colorspace.transforms)

    def _build_display_view(self):

        def get_image_colorspaces_from_display(
            display_name: str,
        ) -> list[ImageColorspace]:
            return [
                _image_colorspace
                for _image_colorspace in self.image_colorspaces
                if _image_colorspace.display_colorspace == display_name
            ]

        for display_colorspace in self.display_colorspaces:
            image_colorspaces = get_image_colorspaces_from_display(display_colorspace)
            with build_display_views(display_colorspace, self) as display:
                for image_colorspace in image_colorspaces:
                    display.append(
                        View(image_colorspace.view_name, image_colorspace.name)
                    )
                display.append(View("Disabled", self.colorspace_Passthrough))
                display.append(View("Display Native", display_colorspace))

        self.setActiveDisplays(":".join([self.display_colorspaces[0]]))
        self.setActiveViews(":".join([]))

    def as_text(self) -> str:
        content: list[str] = self.serialize().split("\n")
        # ocio_profile_version shoudl always be the first attribute, so overrides go after
        if self.overrides:
            for index, line in enumerate(content):
                if line.startswith("ocio_profile_version"):
                    for override in reversed(self.overrides):
                        content.insert(index + 1, override)
                    break

        content = self.header + [""] + content
        return "\n".join(content)

    def save_to_disk(self, file_path: Path):
        content = self.as_text()
        file_path.write_text(content)

    def save_luts_to_disk(self, directory):
        for lut_filename, lut in self._luts.items():
            target_path = directory / lut_filename
            LOGGER.debug(f"writing {target_path}")
            colour.write_LUT(lut, str(target_path))


def get_cli(argv=None):
    """
    Retrieve the command line arguments provided by user.
    """
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(
        "agxc-ocio-build",
        description="Create the AgXc OCIO config.",
    )

    parser.add_argument(
        "--target_dir",
        type=str,
        help="Filesystem path to an existing directory to export the ocio config in.",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Display DEBUG logging message."
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

    default_target_dir = PARENT_DIR.parent.parent.parent / "ocio"
    target_dir = Path(cli.target_dir) if cli.target_dir else default_target_dir

    if not target_dir.exists():
        raise FileNotFoundError(
            f"Target directory must exist on disk. Got <{target_dir}>."
        )

    variants = AgXcConfigVariant.get_all()
    for index, variant in enumerate(variants):
        LOGGER.info(
            f"{index+1}/{len(variants)} generating ocio config variant {variant}"
        )
        ocio_config = AgXcConfig(variant=variant)
        ocio_config.validate()

        ocio_config_path = target_dir / f"AgXc_{variant.value}"
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
