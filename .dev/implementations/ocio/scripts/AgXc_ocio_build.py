import argparse
import dataclasses
import datetime
import enum
import logging
import sys
from pathlib import Path
from typing import Optional
from typing import Union

import PyOpenColorIO as ocio
import colour
import numpy

import AgXLib

LOGGER = logging.getLogger(__name__)
PARENT_DIR = Path(__file__).parent

ADDITIONAL_MODULES_DIR = str(PARENT_DIR / "modules")

if ADDITIONAL_MODULES_DIR not in sys.path:
    sys.path.append(ADDITIONAL_MODULES_DIR)

from giting import get_current_commit_hash
from ocio_matrix_generation import matrix_primaries_transform_ocio
from ocio_matrix_generation import matrix_format_ocio
from ocio_config_helpers import View
from ocio_config_helpers import BaseFamily
from ocio_config_helpers import build_ocio_colorspace
from ocio_config_helpers import build_display_views
from ocio_config_helpers import ImageColorspace


_COMMIT_HASH = get_current_commit_hash(PARENT_DIR)


def set_colorspace_linear(colour_colorspace: colour.RGB_Colourspace):
    colour_colorspace.cctf_decoding = colour.models.linear_function
    colour_colorspace.cctf_encoding = colour.models.linear_function


class AgXcFamily(BaseFamily):
    """
    The various families used to categorise colorspaces
    """

    colorspaces = "Colorspaces"
    agx = "AgX"
    util_curves = "Utilities/Curves"
    views = "Views"


class Dcc(enum.Enum):
    any = enum.auto()
    """
    imply all DCCs
    """

    none = enum.auto()
    """
    imply no DCCs
    """

    blender = enum.auto()

    redshift = enum.auto()


@dataclasses.dataclass
class ConfigVariant:
    name: str
    """
    unique filesystem-safe name
    """

    ocio_version: int
    """
    major version of the OCIO API for this variant
    """

    dcc_support: Optional[Dcc]
    """
    The dcc this variant was made for.
    """

    def __str__(self) -> str:
        return self.name


class AgXcConfig(ocio.Config):
    version = "1.0.0.rc.2"
    lut_dir_name = "LUTs"
    default_cat = "Bradford"
    decimal_precision = 12

    def __init__(self, variant: ConfigVariant):
        super().__init__()

        self._variant = variant

        self.use_ocio_v1 = self._variant.ocio_version == 1

        self.header: list[str] = [
            f"# version: {self.version}",
            f"# name: AgXc",
            f"# variant: {variant.name}",
            f"# built-on: {datetime.datetime.now()}",
            # XXX: the build being part of a commit we reference the previous commit
            #   which is better than nothing I guess.
            f"# previous-commit-hash: {_COMMIT_HASH}",
            "# // visit https://github.com/MrLixm/AgXc",
            "# // and inspect the python build script for details",
        ]
        self.overrides: list[str] = []
        self.lut_sRGB = "sRGB-EOTF-inverse.spi1d"
        self.lut_AgX_tonescale_default = "AgX-tonescale-default.spi1d"
        self.lut_AgX_tonescale_hardtoe = "AgX-tonescale-hardtoe.spi1d"
        self.lut_luma_compensation = "luminance-compensation.cube"
        self.lut_satmax_2 = "saturation-max-2.cube"
        self._luts: dict[str, Union[colour.LUT3D, colour.LUT1D]] = {}

        self.look_punchy = "Punchy"
        self.looks = [
            self.look_punchy,
        ]

        self.colorspace_EOTF_2_2 = "2.2-EOTF-Encoding"
        self.colorspace_EOTF_2_4 = "2.4-EOTF-Encoding"
        self.colorspace_sRGB_linear = "sRGB-linear"
        self.colorspace_sRGB_2_2 = "sRGB-2.2"
        self.colorspace_sRGB_EOTF = "sRGB-texture"
        self.colorspace_Display_P3 = "Display-P3"
        self.colorspace_BT1886 = "BT.1886"
        self.colorspace_AgX_Log = "AgXc-log"
        self.colorspace_AgX_Base = "AgXc.base"
        self.colorspace_AgX_softer = "AgXc.softer"
        self.colorspace_AgX_tonescale = "AgXc-tonescale-default"
        self.colorspace_AgX_tonescale_hardtoe = "AgXc-tonescale-hardtoe"
        self.colorspace_Passthrough = "Passthrough"
        self.colorspace_ACEScg = "ACEScg"
        self.colorspace_ACES20651 = "ACES2065-1"
        self.colorspace_CIE_XYZ_D65 = "CIE-XYZ-D65"
        self.colorspace_BT2020_linear = "BT.2020-linear"

        self.working_colorspace_name = self.colorspace_BT2020_linear
        self.working_colour_colorspace = colour.models.RGB_COLOURSPACE_BT2020.copy()
        self.working_colour_colorspace.use_derived_transformation_matrices(True)
        set_colorspace_linear(self.working_colour_colorspace)

        if variant.dcc_support == Dcc.redshift:
            self.reference_colorspace_name = self.colorspace_sRGB_linear
            self.reference_colour_colorspace = colour.models.RGB_COLOURSPACE_sRGB.copy()
        else:
            self.reference_colorspace_name = self.colorspace_BT2020_linear
            self.reference_colour_colorspace = (
                colour.models.RGB_COLOURSPACE_BT2020.copy()
            )
        self.reference_colour_colorspace.use_derived_transformation_matrices(True)
        set_colorspace_linear(self.reference_colour_colorspace)

        self.display_colorspaces = [
            self.colorspace_sRGB_2_2,
            self.colorspace_Display_P3,
            self.colorspace_BT1886,
        ]

        self.image_renderings = [
            self.colorspace_AgX_Base,
            self.colorspace_AgX_softer,
        ]

        self.image_colorspaces: list[ImageColorspace] = []

        # we do a matrix of image_rendering x look x display_colorspace to define how
        # much "image" colorspace we need to create
        for image_rendering in self.image_renderings:
            # XXX: order matters as they are used to build the Display/Views
            #   and the first view is usually the "default" view in DCC (ex: Blender)
            for look in self.looks + [None]:
                for display_colorspace in self.display_colorspaces:
                    image_colorspace = ImageColorspace(
                        image_rendering=image_rendering,
                        display_colorspace=display_colorspace,
                        look=look,
                        look_space=self.reference_colorspace_name,
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
        self.setRole("matte_paint", self.colorspace_sRGB_2_2)
        self.setRole("reference", self.reference_colorspace_name)
        self.setRole("scene_linear", self.working_colorspace_name)
        self.setRole("texture_paint", self.colorspace_sRGB_2_2)
        self.setRole("aces_interchange", self.colorspace_ACES20651)
        self.setRole("cie_xyz_d65_interchange", self.colorspace_CIE_XYZ_D65)

        # https://docs.blender.org/manual/en/latest/render/color_management.html#opencolorio-configuration
        if variant.dcc_support in [Dcc.any, Dcc.blender]:
            self.setRole("color_picking", self.working_colorspace_name)
            self.setRole("default_sequencer", self.working_colorspace_name)
            self.setRole("default_byte", self.colorspace_sRGB_2_2)
            self.setRole("default_float", self.colorspace_sRGB_linear)

        self._build_looks()
        self._build_colorspaces()
        self._build_luts()
        self._build_display_view()

    def _build_luts(self):
        if self._variant.dcc_support != Dcc.redshift:
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
            name=Path(self.lut_AgX_tonescale_default).stem,
            domain=lut_domain,
            comments=[
                "AgX 1D tonescale with following configuration",
                "   min_EV = -10.0",
                "   max_EV = +6.5",
                "   general_contrast = 2.0",
                "   limits_contrast = (3.0, 3.25)",
            ],
        )
        self._luts[self.lut_AgX_tonescale_default] = lut

        lut_domain = [0.0, 1.0]
        array = colour.LUT1D.linear_table(4096, lut_domain)
        array = AgXLib.apply_AgX_tonescale(
            array,
            min_EV=-10,
            max_EV=+6.8,
            pivot_y=0.33,
            general_contrast=2.74,
            limits_contrast=(3.45, 3.25),
        )
        lut = colour.LUT1D(
            table=array,
            name=Path(self.lut_AgX_tonescale_hardtoe).stem,
            domain=lut_domain,
            comments=[
                "AgX 1D tonescale with following configuration",
                "   min_EV = -10.0",
                "   max_EV = +6.8",
                "   general_contrast = 2.74",
                "   limits_contrast = (3.45, 3.25)",
            ],
        )
        self._luts[self.lut_AgX_tonescale_hardtoe] = lut

        lut_domain = numpy.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
        array = colour.LUT3D.linear_table(64, lut_domain)
        array = colour.models.log_decoding_Log2(
            array,
            min_exposure=-10,
            max_exposure=+15,
            middle_grey=0.18,
        )
        array = AgXLib.reshape.apply_luminance_compensation(
            array,
            luma_weights=(0.33, 0.88, 0.2),
        )
        array = colour.models.log_encoding_Log2(
            array,
            min_exposure=-10,
            max_exposure=+15,
            middle_grey=0.18,
        )
        lut = colour.LUT3D(
            table=array,
            name="Luminance Compensation",
            domain=lut_domain,
            comments=[],
        )
        self._luts[self.lut_luma_compensation] = lut

        lut_domain = numpy.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
        array = colour.LUT3D.linear_table(64, lut_domain)
        array = AgXLib.grading.saturation_max(array, amount=2.0)
        lut = colour.LUT3D(
            table=array,
            name="Saturation with max luma calculation to apply on log encoding.",
            domain=lut_domain,
            comments=[],
        )
        self._luts[self.lut_satmax_2] = lut

    def _build_looks(self):
        look = ocio.Look(
            name=self.look_punchy,
            processSpace=self.colorspace_AgX_Log,
            description="A punchy and more chroma laden look.",
            transform=ocio.GroupTransform(
                [
                    ocio.FileTransform(
                        src=self.lut_satmax_2,
                        interpolation=ocio.INTERP_TETRAHEDRAL,
                    ),
                    ocio.CDLTransform(
                        slope=(1.01,) * 3,
                        offset=(0.038,) * 3,
                        power=(1.24,) * 3,
                    ),
                ]
            ),
        )
        self.addLook(look)

    def _build_colorspaces(self):
        illum_1931 = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]
        whitepoint_d65 = illum_1931["D65"]

        def get_conversion_matrix(colorspace_name: str) -> list[float]:
            if colorspace_name == "XYZ":
                _src: str = "XYZ"
                _src_whitepoint = whitepoint_d65
            else:
                _src: colour.RGB_Colourspace = colour.RGB_COLOURSPACES[colorspace_name]
                _src.use_derived_transformation_matrices(True)
                _src_whitepoint = _src.whitepoint
            return matrix_primaries_transform_ocio(
                source=self.reference_colour_colorspace,
                target=_src,
                source_whitepoint=self.reference_colour_colorspace.whitepoint,
                target_whitepoint=_src_whitepoint,
                cat=self.default_cat,
                decimals=self.decimal_precision,
            )

        def get_matrix_transform(
            colorspace_name: str,
        ) -> Optional[ocio.MatrixTransform]:
            _matrix = get_conversion_matrix(colorspace_name)
            # if identity matrix, discard
            if _matrix == [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]:
                return None
            return ocio.MatrixTransform(matrix=_matrix)

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
            colorspace.description = "sRGB with 2.2 power function transfer-function."
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0.0, 1.0]
            colorspace.set_transforms_from_reference(
                [
                    get_matrix_transform("sRGB"),
                    transform_eotf_22,
                ]
            )

        # XXX: https://github.com/MrLixm/AgXc/issues/2
        with build_ocio_colorspace(self.colorspace_sRGB_EOTF, self) as colorspace:

            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0.0, 1.0]

            if self._variant.dcc_support == Dcc.redshift:
                colorspace.description = (
                    "sRGB IEC 61966-2-1 2.2 Exponent Reference EOTF Display.\n"
                    "This colorspace is required by Redshift to work."
                )
                colorspace.set_transforms_from_reference(
                    [
                        get_matrix_transform("sRGB"),
                        # XXX: redshift specifically need those 2 transforms to
                        #   "find" the sRGB colorspace.
                        ocio.ExponentWithLinearTransform(
                            gamma=[2.4, 2.4, 2.4, 1.0],
                            offset=[0.055, 0.055, 0.055, 0.0],
                            direction=ocio.TRANSFORM_DIR_INVERSE,
                        ),
                        ocio.RangeTransform(
                            minInValue=0, minOutValue=0, maxInValue=1, maxOutValue=1
                        ),
                    ]
                )
            else:
                colorspace.description = (
                    "sRGB colorspace with piecewise transfer-function."
                )
                colorspace.set_transforms_from_reference(
                    [
                        get_matrix_transform("sRGB"),
                        transform_eotf_srgb,
                    ]
                )

        with build_ocio_colorspace(self.colorspace_Display_P3, self) as colorspace:
            colorspace.description = (
                "Display P3 2.2 Exponent EOTF Display. For Apple hardware."
            )
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0.0, 1.0]

            colorspace.set_transforms_from_reference(
                [
                    get_matrix_transform("DCI-P3"),
                    transform_eotf_22,
                ]
            )

        with build_ocio_colorspace(self.colorspace_BT1886, self) as colorspace:
            colorspace.description = "sRGB primaries, D65 whitepoint and 2.4 Exponent EOTF. Also known as Rec.709."
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0, 1]

            colorspace.set_transforms_from_reference(
                [
                    get_matrix_transform("sRGB"),
                    transform_eotf_24,
                ]
            )

        # // AgX colorspaces

        def get_agx_transform(soft_variant=False):
            # XXX: all the inset/rotate values were produced from experimentation in Nuke
            #   using the "MacAdam moments" experiment from jpzambrano:
            #   https://community.acescentral.com/t/aces-2-0-cam-drt-development/4700/434
            src_matrix_pre_inset = AgXLib.get_reshaped_colorspace_matrix(
                src_gamut=self.working_colour_colorspace.primaries,
                src_whitepoint=self.working_colour_colorspace.whitepoint,
                inset_r=0.62,
                inset_g=0.55,
                inset_b=0.58,
                rotate_r=10,
                rotate_g=4,
                rotate_b=19,
            )
            pre_inset_matrix = matrix_format_ocio(
                numpy.linalg.inv(src_matrix_pre_inset)
            )
            src_matrix_inset = AgXLib.get_reshaped_colorspace_matrix(
                src_gamut=self.working_colour_colorspace.primaries,
                src_whitepoint=self.working_colour_colorspace.whitepoint,
                inset_r=0.62,
                inset_g=0.5,
                inset_b=0.5,
                rotate_r=16,
                rotate_g=-24,
                rotate_b=-12,
            )
            inset_matrix = matrix_format_ocio(numpy.linalg.inv(src_matrix_inset))

            src_matrix_outset = AgXLib.get_reshaped_colorspace_matrix(
                src_gamut=self.working_colour_colorspace.primaries,
                src_whitepoint=self.working_colour_colorspace.whitepoint,
                inset_r=0.62,
                inset_g=0.5,
                inset_b=0.5,
                # outset doesnt restore rotation
                rotate_r=0,
                rotate_g=0,
                rotate_b=0,
            )
            outset_matrix = matrix_format_ocio(src_matrix_outset)
            restore_matrix = get_conversion_matrix("sRGB")

            tonescale_lut = (
                self.lut_AgX_tonescale_hardtoe
                if soft_variant
                else self.lut_AgX_tonescale_default
            )

            if soft_variant:
                linearize_transform = [
                    ocio.CDLTransform(slope=(0.82, 0.82, 0.82)),
                ]
            else:
                linearize_transform = [
                    ocio.ColorSpaceTransform(
                        src=self.colorspace_EOTF_2_4,
                        dst="reference",
                    ),
                ]

            if self.reference_colorspace_name == self.working_colorspace_name:
                transforms = []
            else:
                transforms = [
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.working_colorspace_name,
                    ),
                ]

            transforms += [
                # pre-inset
                ocio.MatrixTransform(matrix=pre_inset_matrix),
                # lumninance compensation as 3D Lut
                ocio.AllocationTransform(
                    allocation=ocio.ALLOCATION_LG2,
                    vars=[-10, 15],
                ),
                ocio.FileTransform(
                    src=self.lut_luma_compensation,
                    interpolation=ocio.INTERP_LINEAR,
                ),
                ocio.AllocationTransform(
                    allocation=ocio.ALLOCATION_LG2,
                    vars=[-10, 15],
                    direction=ocio.TRANSFORM_DIR_INVERSE,
                ),
                # inset
                ocio.MatrixTransform(matrix=inset_matrix),
                # log-encoding for tonescale
                ocio.ColorSpaceTransform(
                    src="reference",
                    dst=self.colorspace_AgX_Log,
                ),
                # tonescale
                ocio.FileTransform(
                    src=tonescale_lut,
                    interpolation=ocio.INTERP_LINEAR,
                ),
                # outset to inverse inset
                ocio.MatrixTransform(matrix=outset_matrix),
                # no idea why we need this, but it looks better with
                ocio.MatrixTransform(matrix=restore_matrix),
            ]
            transforms += linearize_transform
            return transforms

        with build_ocio_colorspace(self.colorspace_AgX_Log, self) as colorspace:
            colorspace.description = "AgX Log encoding."
            colorspace.family = AgXcFamily.agx
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocationVars = [-12.47393, 4.026069]

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
                    ocio.AllocationTransform(
                        allocation=ocio.ALLOCATION_LG2,
                        vars=[-12.47393, 4.026069],
                    ),
                ]
            )

        with build_ocio_colorspace(self.colorspace_AgX_Base, self) as colorspace:
            colorspace.description = (
                "AgXc image rendering transform.\n"
                "Output is encoded in working colorspace."
            )
            colorspace.family = AgXcFamily.agx
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                get_agx_transform(soft_variant=False)
            )

        with build_ocio_colorspace(self.colorspace_AgX_softer, self) as colorspace:
            colorspace.description = (
                "AgXc image rendering transform.\n"
                "The tonescale produce a softer result in highlights."
                "Output is encoded in working colorspace."
            )
            colorspace.family = AgXcFamily.agx
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0, 1]

            colorspace.set_transforms_from_reference(
                get_agx_transform(soft_variant=True)
            )

        with build_ocio_colorspace(self.colorspace_AgX_tonescale, self) as colorspace:
            colorspace.description = "AgXc 1D curve. Output is linear.\n"
            colorspace.family = AgXcFamily.agx
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            if self.use_ocio_v1:
                colorspace.allocationVars = [0, 1]

            colorspace.set_transforms_from_reference(
                [
                    # log-encoding for tonescale
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_AgX_Log,
                    ),
                    # tonescale
                    ocio.FileTransform(
                        src=self.lut_AgX_tonescale_default,
                        interpolation=ocio.INTERP_LINEAR,
                    ),
                    # the tonescale already include the EOTF so linearize
                    ocio.ColorSpaceTransform(
                        src=self.colorspace_EOTF_2_4,
                        dst="reference",
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

        with build_ocio_colorspace(self.colorspace_sRGB_linear, self) as colorspace:
            colorspace.description = (
                "Standard sRGB colorspace with linear transfer-function."
            )
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-10, 7, 0.0056065625]

            colorspace.set_transforms_from_reference(
                [
                    get_matrix_transform("sRGB"),
                ]
            )

        with build_ocio_colorspace(self.colorspace_ACEScg, self) as colorspace:
            colorspace.description = "ACES rendering space for CGI. Also known as AP1."
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-8, 5, 0.00390625]

            colorspace.set_transforms_from_reference(
                [
                    get_matrix_transform("ACEScg"),
                ]
            )

        with build_ocio_colorspace(self.colorspace_ACES20651, self) as colorspace:
            colorspace.description = "ACES Interchange format. Also known as AP0."
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-8, 5, 0.00390625]

            colorspace.set_transforms_from_reference(
                [
                    get_matrix_transform("ACES2065-1"),
                ]
            )

        with build_ocio_colorspace(self.colorspace_CIE_XYZ_D65, self) as colorspace:
            colorspace.description = "CIE 1931 Colorspace with a D65 whitepoint."
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-8, 5, 0.00390625]

            colorspace.set_transforms_from_reference(
                [
                    get_matrix_transform("XYZ"),
                ]
            )

        with build_ocio_colorspace(self.colorspace_BT2020_linear, self) as colorspace:
            colorspace.name = self.colorspace_BT2020_linear
            colorspace.description = (
                "The ITU-R BT.2020 colorspace with a linear transfer-function.\n"
                "A very wide gamut on the edge of the spectral locus, with a D65 whitepoint.\n"
                "Also the reference/working colorspace for this config."
            )
            colorspace.family = AgXcFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            if self.use_ocio_v1:
                colorspace.allocation = ocio.ALLOCATION_LG2
                colorspace.allocationVars = [-8, 5, 0.00390625]

            colorspace.set_transforms_from_reference(
                [
                    get_matrix_transform("ITU-R BT.2020"),
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

        # we create a display with just the image-rendering
        # this is useful to apply grading after image-rendering but before display-rendering
        # one could argue than in that case it's not useful to have it as a Display, and
        # the user can already pick the existing colorspace.
        with build_display_views("Pre-Display", self) as display:
            display.append(View(self.colorspace_AgX_Base, self.colorspace_AgX_Base))
            display.append(View(self.colorspace_AgX_softer, self.colorspace_AgX_softer))

        self.setActiveDisplays(":".join([self.colorspace_sRGB_2_2, "Pre-Display"]))
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


_CONFIG_VARIANTS = [
    ConfigVariant("default_OCIO-v1", ocio_version=1, dcc_support=Dcc.none),
    ConfigVariant("default_OCIO-v2", ocio_version=2, dcc_support=Dcc.none),
    ConfigVariant("all-dccs_OCIO-v1", ocio_version=1, dcc_support=Dcc.any),
    ConfigVariant("all-dccs_OCIO-v2", ocio_version=2, dcc_support=Dcc.any),
    ConfigVariant("blender_OCIO-v2", ocio_version=2, dcc_support=Dcc.blender),
    ConfigVariant("redshift_OCIO-v2", ocio_version=2, dcc_support=Dcc.redshift),
]
CONFIG_VARIANTS = {cv.name: cv for cv in _CONFIG_VARIANTS}

DEFAULT_TARGET_DIR = PARENT_DIR.parent.parent.parent / "ocio"


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
