import dataclasses
import logging
import sys
from pathlib import Path
from typing import Type
from typing import TypeVar

import colour

from obs_codegen import Whitepoint
from obs_codegen import Cat
from obs_codegen import AssemblyColorspace
from obs_codegen import ColorspaceGamut
from obs_codegen import TransferFunction
from obs_codegen import BaseGenerator
from obs_codegen import HlslGenerator
from obs_codegen import LuaGenerator

LOGGER = logging.getLogger(__name__)


BaseGeneratorType = TypeVar("BaseGeneratorType", bound=BaseGenerator)


@dataclasses.dataclass
class ColorManagementConfig:
    colorspaces_gamut: list[ColorspaceGamut]
    whitepoints: list[Whitepoint]
    cats: list[Cat]
    colorspaces_assemblies: list[AssemblyColorspace]
    transfer_functions: list[TransferFunction]

    def use_with_generator(
        self, generator_class: Type[BaseGeneratorType]
    ) -> BaseGeneratorType:
        instance = generator_class(
            colorspaces_gamut=self.colorspaces_gamut,
            whitepoints=self.whitepoints,
            cats=self.cats,
            colorspaces_assemblies=self.colorspaces_assemblies,
            transfer_functions=self.transfer_functions,
        )
        return instance


def get_config():
    illuminant1931: dict = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]

    transfer_function_power_2_2 = TransferFunction("Power 2.2")
    transfer_function_sRGB_EOTF = TransferFunction("sRGB EOTF")
    transfer_function_BT709 = TransferFunction("BT.709")
    transfer_function_DCIP3 = TransferFunction("DCI-P3")
    transfer_function_Display_P3 = TransferFunction("Display P3")
    transfer_function_Adobe_RGB_1998 = TransferFunction("Adobe RGB 1998")
    transfer_function_BT2020 = TransferFunction("BT.2020")
    transfer_function_FLog = TransferFunction("FLog")
    transfer_function_FLog2 = TransferFunction("FLog2")
    transfer_function_NLog = TransferFunction("NLog")
    transfer_function_SLog = TransferFunction("SLog")
    transfer_function_SLog2 = TransferFunction("SLog2")
    transfer_function_SLog3 = TransferFunction("SLog3")
    transfer_function_VLog = TransferFunction("VLog")

    transfer_function_list = [
        transfer_function_power_2_2,
        transfer_function_sRGB_EOTF,
        transfer_function_BT709,
        transfer_function_DCIP3,
        transfer_function_Display_P3,
        transfer_function_Adobe_RGB_1998,
        transfer_function_BT2020,
        transfer_function_FLog,
        transfer_function_FLog2,
        transfer_function_NLog,
        transfer_function_SLog,
        transfer_function_SLog2,
        transfer_function_SLog3,
        transfer_function_VLog,
    ]

    # fmt: off
    colorspace_gamut_sRGB = ColorspaceGamut.fromColourColorspaceName("sRGB")
    colorspace_gamut_DCIP3 = ColorspaceGamut.fromColourColorspaceName("DCI-P3")
    colorspace_gamut_Display_P3 = ColorspaceGamut.fromColourColorspaceName("Display P3")
    colorspace_gamut_Adobe_RGB_1998 = ColorspaceGamut.fromColourColorspaceName("Adobe RGB (1998)")
    colorspace_gamut_ITUR_BT_2020 = ColorspaceGamut.fromColourColorspaceName("ITU-R BT.2020")
    colorspace_gamut_Cinema_Gamut = ColorspaceGamut.fromColourColorspaceName("Cinema Gamut")
    colorspace_gamut_S_Gamut = ColorspaceGamut.fromColourColorspaceName("S-Gamut")
    colorspace_gamut_S_Gamut3_Cine = ColorspaceGamut.fromColourColorspaceName("S-Gamut3.Cine")
    colorspace_gamut_V_Gamut = ColorspaceGamut.fromColourColorspaceName("V-Gamut")
    colorspace_gamut_list = [
        colorspace_gamut_sRGB,
        colorspace_gamut_DCIP3,
        colorspace_gamut_Display_P3,
        colorspace_gamut_Adobe_RGB_1998,
        colorspace_gamut_ITUR_BT_2020,
        colorspace_gamut_Cinema_Gamut,
        colorspace_gamut_S_Gamut,
        colorspace_gamut_S_Gamut3_Cine,
        colorspace_gamut_V_Gamut,
    ]
    # fmt: on

    whitepoint_D60 = Whitepoint("D60", illuminant1931["D60"])
    whitepoint_D65 = Whitepoint("D65", illuminant1931["D65"])
    whitepoint_DCIP3 = Whitepoint("DCI-P3", illuminant1931["DCI-P3"])
    whitepoint_list = [whitepoint_D60, whitepoint_D65, whitepoint_DCIP3]

    assembly_colorspace_Passthrough = AssemblyColorspace(
        "Passthrough",
        None,
        None,
        None,
    )
    assembly_colorspace_sRGB_Display_EOTF = AssemblyColorspace(
        "sRGB Display (EOTF)",
        colorspace_gamut_sRGB,
        whitepoint_D65,
        transfer_function_sRGB_EOTF,
    )
    assembly_colorspace_sRGB_Display_2_2 = AssemblyColorspace(
        "sRGB Display (2.2)",
        colorspace_gamut_sRGB,
        whitepoint_D65,
        transfer_function_power_2_2,
    )
    assembly_colorspace_sRGB_Linear = AssemblyColorspace(
        "sRGB Linear",
        colorspace_gamut_sRGB,
        whitepoint_D65,
        None,
    )
    assembly_colorspace_BT_709_Display_2_4 = AssemblyColorspace(
        "BT.709 Display (2.4)",
        colorspace_gamut_sRGB,
        whitepoint_D65,
        transfer_function_BT709,
    )
    assembly_colorspace_DCIP3_Display_2_6 = AssemblyColorspace(
        "DCI-P3 Display (2.6)",
        colorspace_gamut_DCIP3,
        whitepoint_DCIP3,
        transfer_function_DCIP3,
    )
    assembly_colorspace_DCIP3_D65_Display_2_6 = AssemblyColorspace(
        "DCI-P3 D65 Display (2.6)",
        colorspace_gamut_DCIP3,
        whitepoint_D65,
        transfer_function_DCIP3,
    )
    assembly_colorspace_DCIP3_D60_Display_2_6 = AssemblyColorspace(
        "DCI-P3 D60 Display (2.6)",
        colorspace_gamut_DCIP3,
        whitepoint_D60,
        transfer_function_DCIP3,
    )
    assembly_colorspace_Apple_Display_P3 = AssemblyColorspace(
        "Apple Display P3",
        colorspace_gamut_Display_P3,
        whitepoint_DCIP3,
        transfer_function_Display_P3,
    )
    assembly_colorspace_Adobe_RGB_1998_Display = AssemblyColorspace(
        "Adobe RGB 1998 Display",
        colorspace_gamut_Adobe_RGB_1998,
        whitepoint_D65,
        transfer_function_Adobe_RGB_1998,
    )
    assembly_colorspace_BT_2020_Display_OETF = AssemblyColorspace(
        "BT.2020 Display (OETF)",
        colorspace_gamut_ITUR_BT_2020,
        whitepoint_D65,
        transfer_function_BT2020,
    )
    assembly_colorspace_BT_2020_Linear = AssemblyColorspace(
        "BT.2020 Linear",
        colorspace_gamut_ITUR_BT_2020,
        whitepoint_D65,
        None,
    )
    assembly_colorspace_DCIP3_Linear = AssemblyColorspace(
        "DCI-P3 Linear",
        colorspace_gamut_DCIP3,
        whitepoint_DCIP3,
        None,
    )
    assembly_colorspace_Cinema_Gamut = AssemblyColorspace(
        "Cinema Gamut (Canon)",
        colorspace_gamut_Cinema_Gamut,
        whitepoint_D65,
        None,
    )
    assembly_colorspace_F_Gamut_FLog = AssemblyColorspace(
        "F-Gamut FLog (Fujifilm)",
        colorspace_gamut_ITUR_BT_2020,
        whitepoint_D65,
        transfer_function_FLog,
    )
    assembly_colorspace_F_Gamut_FLog2 = AssemblyColorspace(
        "F-Gamut FLog2 (Fujifilm)",
        colorspace_gamut_ITUR_BT_2020,
        whitepoint_D65,
        transfer_function_FLog2,
    )
    assembly_colorspace_N_Gamut = AssemblyColorspace(
        "N-Gamut (Nikon)",
        colorspace_gamut_ITUR_BT_2020,
        whitepoint_D65,
        transfer_function_NLog,
    )
    assembly_colorspace_S_Gamut = AssemblyColorspace(
        "S-Gamut (Sony)",
        colorspace_gamut_S_Gamut,
        whitepoint_D65,
        transfer_function_SLog,
    )
    assembly_colorspace_S_Gamut2 = AssemblyColorspace(
        "S-Gamut2 (Sony)",
        colorspace_gamut_S_Gamut,
        whitepoint_D65,
        transfer_function_SLog2,
    )
    assembly_colorspace_S_Gamut3 = AssemblyColorspace(
        "S-Gamut3 (Sony)",
        colorspace_gamut_S_Gamut,
        whitepoint_D65,
        transfer_function_SLog3,
    )
    assembly_colorspace_S_Gamut3_Cine = AssemblyColorspace(
        "S-Gamut3.Cine (Sony)",
        colorspace_gamut_S_Gamut3_Cine,
        whitepoint_D65,
        transfer_function_SLog3,
    )
    assembly_colorspace_V_Gamut = AssemblyColorspace(
        "V-Gamut (Panasonic)",
        colorspace_gamut_V_Gamut,
        whitepoint_D65,
        transfer_function_VLog,
    )
    assembly_colorspace_list = [
        assembly_colorspace_Passthrough,
        assembly_colorspace_sRGB_Display_EOTF,
        assembly_colorspace_sRGB_Display_2_2,
        assembly_colorspace_sRGB_Linear,
        assembly_colorspace_BT_709_Display_2_4,
        assembly_colorspace_DCIP3_Display_2_6,
        assembly_colorspace_DCIP3_D65_Display_2_6,
        assembly_colorspace_DCIP3_D60_Display_2_6,
        assembly_colorspace_Apple_Display_P3,
        assembly_colorspace_Adobe_RGB_1998_Display,
        assembly_colorspace_BT_2020_Display_OETF,
        assembly_colorspace_BT_2020_Linear,
        assembly_colorspace_DCIP3_Linear,
        assembly_colorspace_Cinema_Gamut,
        assembly_colorspace_F_Gamut_FLog,
        assembly_colorspace_F_Gamut_FLog2,
        assembly_colorspace_N_Gamut,
        assembly_colorspace_S_Gamut,
        assembly_colorspace_S_Gamut2,
        assembly_colorspace_S_Gamut3,
        assembly_colorspace_S_Gamut3_Cine,
        assembly_colorspace_V_Gamut,
    ]

    config = ColorManagementConfig(
        colorspaces_gamut=colorspace_gamut_list,
        whitepoints=whitepoint_list,
        cats=[
            Cat("XYZ Scaling"),
            Cat("Bradford"),
            Cat("CAT02"),
            Cat("Von Kries"),
        ],
        colorspaces_assemblies=assembly_colorspace_list,
        transfer_functions=transfer_function_list,
    )
    return config


class BuildPaths:
    root = Path(__file__).parent.parent.parent / "obs-script"
    assert root.exists()

    hlsl_colorscience_root = root / "_lib_colorscience"
    assert hlsl_colorscience_root.exists()

    hlsl_colorscience_cctfa = hlsl_colorscience_root / "cctf-auto.hlsl"
    hlsl_colorscience_colorspace = hlsl_colorscience_root / "colorspace.hlsl"
    hlsl_colorscience_gamut = hlsl_colorscience_root / "gamut.hlsl"
    hlsl_colorscience_cat = hlsl_colorscience_root / "cat.hlsl"


def build():
    LOGGER.info("started build.")

    colormanagement_config = get_config()

    generator_hlsl = colormanagement_config.use_with_generator(HlslGenerator)

    hlsl_code_mapping = {
        BuildPaths.hlsl_colorscience_cctfa: generator_hlsl.generateTransferFunctionBlock(),
        BuildPaths.hlsl_colorscience_cat: generator_hlsl.generateCatBlock(),
        BuildPaths.hlsl_colorscience_gamut: generator_hlsl.generateMatricesBlock(),
        BuildPaths.hlsl_colorscience_colorspace: generator_hlsl.generateColorspacesBlock(),
    }

    for target_path, hlsl_code in hlsl_code_mapping.items():
        hlsl_code = (
            "// code generated by automatic build; do not manually edit\n" + hlsl_code
        )
        LOGGER.info(f"writting <{target_path}> ...")
        target_path.write_text(hlsl_code)

    LOGGER.info("generating lua code ...")
    generator_lua = colormanagement_config.use_with_generator(LuaGenerator)
    lua_code = generator_lua.generateCode()
    print(lua_code)
    LOGGER.info("finished build.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="{levelname: <7} | {asctime} [{name}] {message}",
        style="{",
        stream=sys.stdout,
    )
    build()
