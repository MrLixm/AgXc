"""
Using colour & python to generate HLSL code for colorspace conversions.
"""
import itertools
import dataclasses
import re
from typing import Optional, List

import colour
import numpy

ROUND_THRESHOLD = 9


def slugify(string: str, preserve_case: bool = True) -> str:
    """
    Convert to code variable compatible name.
    """
    if not preserve_case:
        string = string.lower()

    output = string.replace("-", "")
    output = re.sub(r"\W", "_", output)
    output = re.sub(r"_{2,}", "_", output)
    output = output.rstrip("_")
    return output


def convert3x3MatrixToHlslStr(matrix: numpy.ndarray) -> str:
    """

    Args:
        matrix: 3x3 matrix as numpy array

    Returns:
        partial HLSL variable declaration.
    """
    return (
        "\\\n"
        f"  {round(matrix[0][0], ROUND_THRESHOLD)}, {round(matrix[0][1], ROUND_THRESHOLD)}, {round(matrix[0][2], ROUND_THRESHOLD)},\\\n"
        f"  {round(matrix[1][0], ROUND_THRESHOLD)}, {round(matrix[1][1], ROUND_THRESHOLD)}, {round(matrix[1][2], ROUND_THRESHOLD)},\\\n"
        f"  {round(matrix[2][0], ROUND_THRESHOLD)}, {round(matrix[2][1], ROUND_THRESHOLD)}, {round(matrix[2][2], ROUND_THRESHOLD)}\\\n"
    )


def generateCommentHeader(title: str, description: Optional[str] = None) -> str:
    """
    Generate an HLSL comment block to summarize the code that can be found under.
    """
    max_length = 80

    out_str = "/* "
    out_str += "-" * max_length + "\n"
    out_str += title + "\n"
    if description:
        out_str += "\n"
        out_str += description + "\n"
    out_str += "-" * max_length + " */\n"
    return out_str


@dataclasses.dataclass
class Whitepoint:

    name: str
    coordinates: numpy.ndarray
    """
    CIE xy coordinates as a ndarray(2,)
    """

    id: int = dataclasses.field(default_factory=itertools.count().__next__, init=False)

    def __post_init__(self):
        self.safe_name = slugify(self.name)

    def __hash__(self):
        return hash(self.name)


@dataclasses.dataclass
class Cat:

    name: str
    id: int = dataclasses.field(default_factory=itertools.count().__next__, init=False)

    def __post_init__(self):
        self.safe_name = slugify(self.name)

    def __hash__(self):
        return hash(self.name)


@dataclasses.dataclass
class AssemblyColorspace:

    name: str
    id: int = dataclasses.field(default_factory=itertools.count().__next__, init=False)

    def __post_init__(self):
        self.safe_name = slugify(self.name)

    def __hash__(self):
        return hash(self.name)


@dataclasses.dataclass
class HlslVariable:

    name: str
    definition: str


def processCat(
    whitepoint_source: Whitepoint,
    whitepoint_target: Whitepoint,
    cat: Cat,
) -> HlslVariable:

    matrix_cat = colour.adaptation.matrix_chromatic_adaptation_VonKries(
        colour.xy_to_XYZ(whitepoint_source.coordinates),
        colour.xy_to_XYZ(whitepoint_target.coordinates),
        cat.name,
    )

    variable_name = f"matrix_cat_{cat.safe_name}_{whitepoint_source.safe_name}_to_{whitepoint_target.safe_name}"
    variable_def = (
        f"#define {variable_name} float3x3({convert3x3MatrixToHlslStr(matrix_cat)})\n"
    )
    return HlslVariable(variable_name, variable_def)


def processColorspaceMatrix(colorspace: colour.RGB_Colourspace) -> str:
    """

    Args:
        colorspace:

    Returns:
        valid HLSL code snippet
    """
    out_str = ""
    out_str += f"// {colorspace.name}\n"
    colorspaceName = slugify(colorspace.name)
    matrix = colorspace.matrix_RGB_to_XYZ
    out_str += f"#define matrix_{colorspaceName}_to_XYZ float3x3({convert3x3MatrixToHlslStr(matrix)})\n"
    matrix = colorspace.matrix_XYZ_to_RGB
    out_str += f"#define matrix_{colorspaceName}_from_XYZ float3x3({convert3x3MatrixToHlslStr(matrix)})\n"
    return out_str


class Generator:
    """
    Generate HLSL code as a string following the given input attributes.
    """

    def __init__(
        self,
        colorspace_names: list[str],
        whitepoint_names: list[str],
        cat_names: list[str],
        assembly_colorspaces_names: list[str],
    ):

        self.colorspace_list: List[colour.RGB_Colourspace] = [
            colour.RGB_COLOURSPACES[colorspace_name]
            for colorspace_name in colorspace_names
        ]

        illuminant1931: dict = colour.CCS_ILLUMINANTS[
            "CIE 1931 2 Degree Standard Observer"
        ]

        self.whitepoint_list: list[Whitepoint] = [
            Whitepoint(whitepoint_name, illuminant1931[whitepoint_name])
            for whitepoint_name in whitepoint_names
        ]

        self.cat_list: list[Cat] = [Cat(cat_name) for cat_name in cat_names]

        self.assembly_colorspace_list: list[AssemblyColorspace] = [
            AssemblyColorspace(colorspace_name)
            for colorspace_name in assembly_colorspaces_names
        ]

    def generateCode(self) -> str:
        """
        Returns:
            valid HLSL code snippet
        """

        str_colorspace = self._generateMatricesBlock()
        str_cat = self._generateCatBlock()

        return f"{str_cat}\n\n{str_colorspace}"

    def _generateMatricesBlock(self) -> str:

        out_str = generateCommentHeader("Matrices")
        out_str += "\n"

        for colorspace in self.colorspace_list:

            out_str += processColorspaceMatrix(colorspace) + "\n"

        return out_str

    def _generateCatBlock(self) -> str:

        out_str = generateCommentHeader("Chromatic Adaptation Transforms")
        out_str += "\n"

        whitepoint_combinaison_list = list(
            itertools.product(self.whitepoint_list, repeat=2)
        )

        cat_variable_dict = dict()

        for cat in self.cat_list:

            for whitepoint_combinaison in whitepoint_combinaison_list:

                whitepoint_source = whitepoint_combinaison[0]
                whitepoint_target = whitepoint_combinaison[1]

                if whitepoint_source == whitepoint_target:
                    continue

                cat_variable = processCat(whitepoint_source, whitepoint_target, cat)
                generated_id = (cat.id, whitepoint_source.id, whitepoint_target.id)
                cat_variable_dict[generated_id] = cat_variable

                out_str += cat_variable.definition
                continue

        out_str += "\n"

        for cat in self.cat_list:
            out_str += f"uniform int catid_{cat.safe_name} = {cat.id};\n"

        out_str += "\n"

        for whitepoint in self.whitepoint_list:
            out_str += (
                f"uniform int whitepointid_{whitepoint.safe_name} = {whitepoint.id};\n"
            )

        out_str += "\n\n"
        out_str += "float3x3 getChromaticAdaptationTransformMatrix(int cat_name, int whitepoint_source, int whitepoint_target){\n"

        for cat_variable_id, cat_variable in cat_variable_dict.items():
            out_str += f"    if (cat_name == {cat_variable_id[0]} && whitepoint_source == {cat_variable_id[1]} && whitepoint_target == {cat_variable_id[2]})"
            out_str += f" return {cat_variable.name};\n"

        out_str += "}"

        return out_str


def main():

    generator = Generator(
        colorspace_names=[
            "sRGB",
            "DCI-P3",
            "Display P3",
            "Adobe RGB (1998)",
            "ITU-R BT.2020",
        ],
        whitepoint_names=[
            "D60",
            "D65",
            "DCI-P3",
        ],
        cat_names=[
            "XYZ Scaling",
            "Bradford",
            "CAT02",
            "Von Kries",
        ],
        assembly_colorspaces_names=[
            "Passthrough",
            "sRGB Display (EOTF)",
            "sRGB Display (2.2)",
            "sRGB Linear",
            "BT.709 Display (2.4)",
            "DCI-P3 Display (2.6)",
            "Apple Display P3",
        ],
    )
    print(generator.generateCode())
    return


if __name__ == "__main__":
    main()
