import argparse
import contextlib
import dataclasses
import datetime
import enum
import logging
import sys
from pathlib import Path
from typing import Optional
from typing import ContextManager
from typing import Literal
from typing import Union

import PyOpenColorIO as ocio
import colour
import numpy

import AgXLib

LOGGER = logging.getLogger(__name__)
PARENT_DIR = Path(__file__).parent

DEFAULT_CAT = "Bradford"
DEFAULT_DECIMALS = 12


"""-------------------------------------------------------------------------------------
Matrix utilities
"""


def matrix_3x3_to_4x4(matrix: numpy.ndarray) -> numpy.ndarray:
    """
    Convert a 3x3 matrix to a 4x4 matrix as such :
    [[ value  value  value  0. ]
     [ value  value  value  0. ]
     [ value  value  value  0. ]
     [ 0.     0.     0.    1. ]]

    Returns:
        4x4 matrix
    """

    output = numpy.append(matrix, [[0], [0], [0]], axis=1)
    output = numpy.append(output, [[0, 0, 0, 1]], axis=0)
    return output


def matrix_format_ocio(matrix: numpy.ndarray) -> list[float]:
    """
    Format the given 3x3 matrix to an OCIO parameters complient list.

    Args:
        matrix: 3x3 matrix
    Returns:
        list: 4x4 matrix in a single line list.
    """
    new_matrix = matrix_3x3_to_4x4(matrix)
    # "un-nest" the matrix by ensuring we have a flat list
    new_matrix = numpy.concatenate(new_matrix).tolist()
    return new_matrix


def matrix_whitepoint_cat(
    source_whitepoint: numpy.ndarray,
    target_whitepoint: numpy.ndarray,
    cat: str = DEFAULT_CAT,
) -> numpy.ndarray:
    """Return the matrix to perform a chromatic adaptation with the given
    parameters.

    Args:
        source_whitepoint: source whitepoint name as xy coordinates
        target_whitepoint: target whitepoint name as xy coordinates
        cat: chromatic adaptation transform method to use.

    Returns:
        chromatic adaptation matrix from test viewing conditions
         to reference viewing conditions. A 3x3 matrix.
    """

    matrix = colour.adaptation.matrix_chromatic_adaptation_VonKries(
        colour.xy_to_XYZ(source_whitepoint),
        colour.xy_to_XYZ(target_whitepoint),
        transform=cat,
    )

    return matrix


def matrix_primaries_transform_ocio(
    source: Union[colour.RGB_Colourspace, Literal["XYZ"]],
    target: Union[colour.RGB_Colourspace, Literal["XYZ"]],
    source_whitepoint: Optional[numpy.ndarray] = None,
    target_whitepoint: Optional[numpy.ndarray] = None,
    cat: str = DEFAULT_CAT,
    decimals: int = DEFAULT_DECIMALS,
) -> list[float]:
    """
    By given a source and target colorspace, return the corresponding
    colorspace conversion matrix.
    You can use "XYZ" as a source or target.

    Args:
        source: source colorspace, use "XYZ" for CIE-XYZ.
        target: target colorspace, use "XYZ" for CIE-XYZ.
        source_whitepoint: whitepoint coordinates as [x, y]
        target_whitepoint: whitepoint coordinates as [x, y]
        cat: chromatic adaptation transform
        decimals: number of decimal after zero to conserve
    Returns:
        4x4 matrix in a single line list.
    """
    matrix_cat = None
    if source_whitepoint is not None and target_whitepoint is not None:
        matrix_cat = matrix_whitepoint_cat(
            source_whitepoint=source_whitepoint,
            target_whitepoint=target_whitepoint,
            cat=cat,
        )

    if source == "XYZ" or target == "XYZ":
        if target == "XYZ":
            matrix = source.matrix_RGB_to_XYZ

            if matrix_cat is not None:
                matrix = numpy.dot(matrix_cat, matrix)

        else:
            matrix = target.matrix_XYZ_to_RGB

            if matrix_cat is not None:
                matrix = numpy.dot(matrix, matrix_cat)

    else:
        matrix = source.matrix_RGB_to_XYZ

        if matrix_cat is not None:
            matrix = numpy.dot(matrix_cat, source.matrix_RGB_to_XYZ)

        matrix = numpy.dot(target.matrix_XYZ_to_RGB, matrix)

    matrix = matrix.round(decimals)
    return matrix_format_ocio(matrix)


"""-------------------------------------------------------------------------------------
Config utilities
"""


class ColorspaceFamily(enum.Enum):
    """
    The various families used to categorise colorspaces
    """

    colorspaces = "Colorspaces"
    agx = "AgX"
    util_curves = "Utilities/Curves"
    view_agx_srgb = "Views/AgX sRGB"
    view_agx_bt1886 = "Views/AgX BT.1886"
    view_agx_displayp3 = "Views/AgX Display P3"
    view_appareance = "Views/Appearance"


@dataclasses.dataclass
class _Colorspace:
    """
    simple wrapper function on ocio.ColorSpace to have better default/type-hinting
    """

    name: str
    family: Optional[ColorspaceFamily] = None
    bitdepth: ocio.BitDepth = ocio.BIT_DEPTH_UNKNOWN
    aliases: Optional[list[str]] = None
    description: str = ""
    encoding: str = ""
    equalityGroup: str = ""
    categories: Optional[list[str]] = None
    isData: bool = False
    allocation: ocio.Allocation = ocio.ALLOCATION_UNIFORM
    allocationVars: Optional[list[float]] = None
    toReference: Optional[ocio.Transform] = None
    fromReference: Optional[ocio.Transform] = None
    referenceSpace: ocio.ReferenceSpaceType = ocio.REFERENCE_SPACE_SCENE

    def asOCIO(self) -> ocio.ColorSpace:
        aliases = self.aliases or []
        categories = self.categories or []
        allocationVars = [float(number) for number in self.allocationVars or []]
        family = self.family.value or ""
        return ocio.ColorSpace(
            referenceSpace=self.referenceSpace,
            name=self.name,
            aliases=aliases,
            description=self.description,
            family=family,
            encoding=self.encoding,
            equalityGroup=self.equalityGroup,
            categories=categories,
            bitDepth=self.bitdepth,
            isData=self.isData,
            allocation=self.allocation,
            allocationVars=allocationVars,
            toReference=self.toReference,
            fromReference=self.fromReference,
        )

    def set_transforms_from_reference(self, transforms: list[ocio.Transform]):
        if len(transforms) == 1:
            self.fromReference = transforms[0]
            return

        group_transform = ocio.GroupTransform()
        for transform in transforms:
            group_transform.appendTransform(transform)

        self.fromReference = group_transform

    def set_transforms_to_reference(self, transforms: list[ocio.Transform]):
        if len(transforms) == 1:
            self.toReference = transforms[0]
            return

        group_transform = ocio.GroupTransform()
        for transform in transforms:
            group_transform.appendTransform(transform)

        self.toReference = group_transform


@dataclasses.dataclass
class _View:
    name: str
    """
    Human readable name of the view.
    """

    colorspace: str
    """
    Existing colorspace name that the view is using.
    """

    looks: list[str] = dataclasses.field(default_factory=list)
    """
    List of existing look names. Optionally prepend with + or - to add or remove the look.
    """


@contextlib.contextmanager
def build_ocio_colorspace(
    name: str,
    config: ocio.Config,
) -> ContextManager[_Colorspace]:
    """
    To use as::

        with build_ocio_colorspace("my Colorspace", config) as colorspace:
            colorspace.isData = True
    """
    colorspace = _Colorspace(name=name)
    try:
        yield colorspace
    finally:
        ocio_colorspace = colorspace.asOCIO()
        config.addColorSpace(ocio_colorspace)


@contextlib.contextmanager
def build_display_views(
    display_name: str, config: ocio.Config
) -> ContextManager[list[_View]]:
    """
    To use as::

        with build_display_views("my Display", config) as display:
            display.append(_View("myView", "my Colorspace"))
    """
    views: list[_View] = []
    try:
        yield views
    finally:
        for view in views:
            config.addDisplayView(
                display=display_name,
                view=view.name,
                colorSpaceName=view.colorspace,
                looks=",".join(view.looks),
            )


"""-------------------------------------------------------------------------------------
Config definition
"""


class AgXcConfig(ocio.Config):
    version = "0.2.5"
    lut_dir_name = "LUTs"

    def __init__(self):
        super().__init__()

        self.header: list[str] = [
            f"# version: {self.version}",
            f"# name: AgXc",
            f"# built on: {datetime.datetime.now()}",
            "# // visit https://github.com/MrLixm/AgXc",
            "# // and inspect the python build script for details",
        ]
        self.overrides: list[str] = [
            "",
            # XXX: this is ignored by OCIO on v1 API but we want to keep it
            "name: AgXc",
            "",
            # XXX: this is ignored by OCIO on v1 API but we want to keep it but
            #   as some apps spit out warning without
            "environment: {}",
        ]
        self.lut_sRGB = "sRGB-EOTF-inverse.spi1d"
        self.lut_AgX = "AgX_Default_Contrast.spi1d"
        self._luts: dict[str, colour.LUT1D] = {}

        self.colorspace_Linear_sRGB = "Linear sRGB"
        self.colorspace_AgX_Log = "AgX Log (Kraken)"
        self.colorspace_EOTF_2_2 = "2.2 EOTF Encoding"
        self.colorspace_EOTF_2_4 = "2.4 EOTF Encoding"
        self.colorspace_sRGB_2_2 = "sRGB - 2.2"
        self.colorspace_sRGB_EOTF = "sRGB - EOTF"
        self.colorspace_Display_P3 = "Display P3"
        self.colorspace_BT_1886 = "BT.1886"
        self.colorspace_AgX_Base = "AgX Base"
        self.colorspace_AgX_Base_sRGB = "AgX Base sRGB"
        self.colorspace_AgX_Base_BT1886 = "AgX Base BT.1886"
        self.colorspace_AgX_Base_DisplayP3 = "AgX Base Display P3"
        self.colorspace_Appearance_PunchysRGB = "Appearance Punchy sRGB"
        self.colorspace_Appearance_Punchy_DisplayP3 = "Appearance Punchy Display P3"
        self.colorspace_Appearance_Punchy_BT1886 = "Appearance Punchy BT.1886"
        self.colorspace_Passthrough = "Passthrough"
        self.colorspace_ACEScg = "ACEScg"
        self.colorspace_ACES20651 = "ACES2065-1"
        self.colorspace_CIE_XYZ_D65 = "CIE - XYZ - D65"

        self.look_punchy = "Punchy"

        self.setVersion(1, 0)
        self.setName("AgXc")  # XXX: name is not a OCIO v1 feature
        self.setDescription(
            "AgX image rendering initially designed by Troy Sobotka.\n"
            "Adapted by Liam Collod with full permissions from Troy Sobotka.\n"
            f"C.A.T. used for whitepoint conversions is <{DEFAULT_CAT}>.\n"
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

        srgb_colorspace = colour.RGB_COLOURSPACES["sRGB"]
        illum_1931 = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]
        whitepoint_d65 = illum_1931["D65"]

        with build_ocio_colorspace(self.colorspace_Linear_sRGB, self) as colorspace:
            colorspace.name = self.colorspace_Linear_sRGB
            colorspace.description = "Open Domain Linear BT.709 Tristimulus"
            colorspace.family = ColorspaceFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            colorspace.allocation = ocio.ALLOCATION_LG2
            colorspace.allocationVars = [-10, 7, 0.0056065625]

        with build_ocio_colorspace(self.colorspace_AgX_Log, self) as colorspace:
            colorspace.name = self.colorspace_AgX_Log
            colorspace.description = "AgX Log (Kraken)"
            colorspace.family = ColorspaceFamily.agx
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [-12.47393, 4.026069]

            inset_matrix = AgXLib.get_reshaped_colorspace_matrix(
                src_gamut=srgb_colorspace.primaries,
                src_whitepoint=whitepoint_d65,
                inset_r=0.2,
                inset_g=0.2,
                inset_b=0.2,
            )
            inset_matrix = matrix_format_ocio(numpy.linalg.inv(inset_matrix))
            colorspace.set_transforms_from_reference(
                [
                    # the 2 CLDTransform are a hack to clamp negatives
                    # 2nd one has a minuscule offset else considered no-op and no clamp applied
                    ocio.CDLTransform(power=[2.0, 2.0, 2.0]),
                    ocio.CDLTransform(power=[0.500001, 0.500001, 0.500001]),
                    ocio.MatrixTransform(matrix=inset_matrix),
                    ocio.AllocationTransform(
                        allocation=ocio.ALLOCATION_LG2,
                        vars=[-12.47393, 4.026069],
                    ),
                ]
            )

        with build_ocio_colorspace(self.colorspace_EOTF_2_2, self) as colorspace:
            colorspace.name = self.colorspace_EOTF_2_2
            colorspace.description = "transfer-function: 2.2 Exponent EOTF Encoding"
            colorspace.family = ColorspaceFamily.util_curves
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.ExponentTransform(
                        value=[2.2, 2.2, 2.2, 1],
                        direction=ocio.TRANSFORM_DIR_INVERSE,
                    ),
                ]
            )

        with build_ocio_colorspace(self.colorspace_EOTF_2_4, self) as colorspace:
            colorspace.name = self.colorspace_EOTF_2_4
            colorspace.description = "transfer-function: 2.4 Exponent EOTF Encoding"
            colorspace.family = ColorspaceFamily.util_curves
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.ExponentTransform(
                        value=[2.4, 2.4, 2.4, 1],
                        direction=ocio.TRANSFORM_DIR_INVERSE,
                    ),
                ]
            )

        with build_ocio_colorspace(self.colorspace_sRGB_2_2, self) as colorspace:
            colorspace.name = self.colorspace_sRGB_2_2
            colorspace.description = (
                "sRGB with transfer-function simplified to the 2.2 power function."
            )
            colorspace.family = ColorspaceFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0.0, 1.0]
            colorspace.set_transforms_from_reference(
                [
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_EOTF_2_2,
                    ),
                ]
            )

        with build_ocio_colorspace(self.colorspace_sRGB_EOTF, self) as colorspace:
            colorspace.name = self.colorspace_sRGB_EOTF
            colorspace.description = 'sRGB IEC 61966-2-1 2.2 Exponent Reference EOTF Display\nThis "colorspace" is required by Redshift.'
            colorspace.family = ColorspaceFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0.0, 1.0]
            colorspace.set_transforms_to_reference(
                [
                    ocio.FileTransform(
                        src=self.lut_sRGB,
                        interpolation=ocio.INTERP_LINEAR,
                    ),
                ]
            )

        with build_ocio_colorspace(self.colorspace_Display_P3, self) as colorspace:
            colorspace.name = self.colorspace_Display_P3
            colorspace.description = (
                "Display P3 2.2 Exponent EOTF Display. For Apple hardware."
            )
            colorspace.family = ColorspaceFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0.0, 1.0]

            src_colorspace: colour.RGB_Colourspace = colour.RGB_COLOURSPACES["sRGB"]
            src_colorspace.use_derived_transformation_matrices(True)
            dst_colorspace: colour.RGB_Colourspace = colour.RGB_COLOURSPACES["DCI-P3"]
            dst_colorspace.use_derived_transformation_matrices(True)
            matrix = matrix_primaries_transform_ocio(
                source=src_colorspace,
                target=dst_colorspace,
                source_whitepoint=src_colorspace.whitepoint,
                target_whitepoint=dst_colorspace.whitepoint,
            )
            colorspace.set_transforms_from_reference(
                [
                    ocio.MatrixTransform(matrix=matrix),
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_EOTF_2_2,
                    ),
                ]
            )

        with build_ocio_colorspace(self.colorspace_BT_1886, self) as colorspace:
            colorspace.name = self.colorspace_BT_1886
            colorspace.description = "BT.1886 2.4 Exponent EOTF Display. Also known as Rec.709 transfer function."
            colorspace.family = ColorspaceFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_EOTF_2_4,
                    )
                ]
            )

        with build_ocio_colorspace(self.colorspace_AgX_Base, self) as colorspace:
            colorspace.name = self.colorspace_AgX_Base
            colorspace.description = (
                "AgX Base Image Encoding, output is already display encoded."
            )
            colorspace.family = ColorspaceFamily.agx
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
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

        with build_ocio_colorspace(self.colorspace_AgX_Base_sRGB, self) as colorspace:
            colorspace.name = self.colorspace_AgX_Base_sRGB
            colorspace.description = "AgX Base Image Encoding for sRGB Displays"
            colorspace.family = ColorspaceFamily.view_agx_srgb
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_AgX_Base,
                    )
                ]
            )

        with build_ocio_colorspace(self.colorspace_AgX_Base_BT1886, self) as colorspace:
            colorspace.name = self.colorspace_AgX_Base_BT1886
            colorspace.description = "AgX Base Image Encoding for BT.1886 Displays"
            colorspace.family = ColorspaceFamily.view_agx_bt1886
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_AgX_Base,
                    ),
                    ocio.ColorSpaceTransform(
                        src=self.colorspace_EOTF_2_2,
                        dst=self.colorspace_EOTF_2_4,
                    ),
                ]
            )

        with build_ocio_colorspace(
            self.colorspace_AgX_Base_DisplayP3, self
        ) as colorspace:
            colorspace.name = self.colorspace_AgX_Base_DisplayP3
            colorspace.description = "AgX Base Image Encoding for Display P3 Displays"
            colorspace.family = ColorspaceFamily.view_agx_displayp3
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_AgX_Base,
                    ),
                    ocio.ColorSpaceTransform(
                        src=self.colorspace_EOTF_2_2,
                        dst=self.colorspace_Display_P3,
                    ),
                ]
            )

        with build_ocio_colorspace(
            self.colorspace_Appearance_PunchysRGB, self
        ) as colorspace:
            colorspace.name = self.colorspace_Appearance_PunchysRGB
            colorspace.description = (
                "A punchy and more chroma laden look for sRGB displays"
            )
            colorspace.family = ColorspaceFamily.view_appareance
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.LookTransform(
                        src="reference",
                        dst=self.colorspace_AgX_Base,
                        looks=self.look_punchy,
                    )
                ]
            )

        with build_ocio_colorspace(
            self.colorspace_Appearance_Punchy_DisplayP3, self
        ) as colorspace:
            colorspace.name = self.colorspace_Appearance_Punchy_DisplayP3
            colorspace.description = (
                "A punchy and more chroma laden look for Display P3 displays"
            )
            colorspace.family = ColorspaceFamily.view_appareance
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.LookTransform(
                        src="reference",
                        dst=self.colorspace_AgX_Base,
                        looks=self.look_punchy,
                    ),
                    ocio.ColorSpaceTransform(
                        src=self.colorspace_EOTF_2_2,
                        dst=self.colorspace_Display_P3,
                    ),
                ]
            )

        with build_ocio_colorspace(
            self.colorspace_Appearance_Punchy_BT1886, self
        ) as colorspace:
            colorspace.name = self.colorspace_Appearance_Punchy_BT1886
            colorspace.description = (
                "A punchy and more chroma laden look for BT.1886 displays"
            )
            colorspace.family = ColorspaceFamily.view_appareance
            colorspace.bitdepth = ocio.BIT_DEPTH_UNKNOWN
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.set_transforms_from_reference(
                [
                    ocio.LookTransform(
                        src="reference",
                        dst=self.colorspace_AgX_Base,
                        looks=self.look_punchy,
                    ),
                    ocio.ColorSpaceTransform(
                        src=self.colorspace_EOTF_2_2,
                        dst=self.colorspace_EOTF_2_4,
                    ),
                ]
            )

        with build_ocio_colorspace(self.colorspace_Passthrough, self) as colorspace:
            colorspace.name = self.colorspace_Passthrough
            colorspace.description = (
                'Passthrough means no transformations. Also know as "raw".'
            )
            colorspace.family = ColorspaceFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            colorspace.allocation = ocio.ALLOCATION_UNIFORM
            colorspace.allocationVars = [0, 1]
            colorspace.isData = True
            colorspace.equalityGroup = "scalar"

        with build_ocio_colorspace(self.colorspace_ACEScg, self) as colorspace:
            colorspace.name = self.colorspace_ACEScg
            colorspace.description = "ACES rendering space for CGI. Also known as AP1."
            colorspace.family = ColorspaceFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            colorspace.allocation = ocio.ALLOCATION_LG2
            colorspace.allocationVars = [-8, 5, 0.00390625]

            src_colorspace = "XYZ"
            dst_colorspace: colour.RGB_Colourspace = colour.RGB_COLOURSPACES["ACEScg"]
            dst_colorspace.use_derived_transformation_matrices(True)
            matrix = matrix_primaries_transform_ocio(
                source=src_colorspace,
                target=dst_colorspace,
                source_whitepoint=whitepoint_d65,
                target_whitepoint=dst_colorspace.whitepoint,
            )
            colorspace.set_transforms_from_reference(
                [
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_CIE_XYZ_D65,
                    ),
                    ocio.MatrixTransform(matrix=matrix),
                ]
            )

        with build_ocio_colorspace(self.colorspace_ACES20651, self) as colorspace:
            colorspace.name = self.colorspace_ACES20651
            colorspace.description = "ACES Interchange format. Also known as AP0."
            colorspace.family = ColorspaceFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            colorspace.allocation = ocio.ALLOCATION_LG2
            colorspace.allocationVars = [-8, 5, 0.00390625]

            src_colorspace = "XYZ"
            dst_colorspace: colour.RGB_Colourspace = colour.RGB_COLOURSPACES[
                "ACES2065-1"
            ]
            dst_colorspace.use_derived_transformation_matrices(True)
            matrix = matrix_primaries_transform_ocio(
                source=src_colorspace,
                target=dst_colorspace,
                source_whitepoint=whitepoint_d65,
                target_whitepoint=dst_colorspace.whitepoint,
            )
            colorspace.set_transforms_from_reference(
                [
                    ocio.ColorSpaceTransform(
                        src="reference",
                        dst=self.colorspace_CIE_XYZ_D65,
                    ),
                    ocio.MatrixTransform(matrix=matrix),
                ]
            )

        with build_ocio_colorspace(self.colorspace_CIE_XYZ_D65, self) as colorspace:
            colorspace.name = self.colorspace_CIE_XYZ_D65
            colorspace.description = "CIE 1931 Colorspace with a D65 whitepoint."
            colorspace.family = ColorspaceFamily.colorspaces
            colorspace.bitdepth = ocio.BIT_DEPTH_F32
            colorspace.allocation = ocio.ALLOCATION_LG2
            colorspace.allocationVars = [-8, 5, 0.00390625]

            src_colorspace: colour.RGB_Colourspace = colour.RGB_COLOURSPACES["sRGB"]
            src_colorspace.use_derived_transformation_matrices(True)
            dst_colorspace = "XYZ"
            matrix = matrix_primaries_transform_ocio(
                source=src_colorspace,
                target=dst_colorspace,
                source_whitepoint=src_colorspace.whitepoint,
                target_whitepoint=whitepoint_d65,
            )
            colorspace.set_transforms_from_reference(
                [
                    ocio.MatrixTransform(matrix=matrix),
                ]
            )

    def _build_display_view(self):
        with build_display_views("sRGB", self) as display:
            display.append(_View("AgX Punchy", self.colorspace_Appearance_PunchysRGB))
            display.append(_View("AgX", self.colorspace_AgX_Base_sRGB))
            display.append(_View("Disabled", self.colorspace_Passthrough))
            display.append(_View("Display Native", self.colorspace_sRGB_2_2))

        with build_display_views("Display P3", self) as display:
            display.append(
                _View("AgX Punchy", self.colorspace_Appearance_Punchy_DisplayP3)
            )
            display.append(_View("AgX", self.colorspace_AgX_Base_DisplayP3))
            display.append(_View("Disabled", self.colorspace_Passthrough))
            display.append(_View("Display Native", self.colorspace_Display_P3))

        with build_display_views("BT.1886", self) as display:
            display.append(
                _View("AgX Punchy", self.colorspace_Appearance_Punchy_BT1886)
            )
            display.append(_View("AgX", self.colorspace_AgX_Base_BT1886))
            display.append(_View("Disabled", self.colorspace_Passthrough))
            display.append(_View("Display Native", self.colorspace_BT_1886))

        self.setActiveDisplays(":".join(["sRGB"]))
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
        target_dir = directory / self.lut_dir_name
        for lut_filename, lut in self._luts.items():
            target_path = target_dir / lut_filename
            LOGGER.debug(f"writing {target_path}")
            colour.write_LUT(lut, str(target_path))


def get_cli(argv=None):
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(
        "agxc-ocio-build",
        description="Create the AgXc OCIO config.",
    )

    parser.add_argument(
        "--target_dir",
        type=str,
        help="filesystem path to an existing directory",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
    )

    parsed = parser.parse_args(argv)
    return parsed


def main():
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

    LOGGER.info(f"generating ocio config")
    ocio_config = AgXcConfig()
    ocio_config.validate()

    ocio_config_path = target_dir / "config.ocio"
    LOGGER.info(f"writing ocio config to <{ocio_config_path}>")
    ocio_config.save_to_disk(ocio_config_path)

    luts_path = ocio_config_path.parent
    LOGGER.info(f"writing luts to <{luts_path}>")
    ocio_config.save_luts_to_disk(luts_path)


if __name__ == "__main__":
    main()
