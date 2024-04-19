__all__ = ("BaseGenerator",)

import dataclasses
import logging
from abc import abstractmethod

from obs_codegen._colorcomponents import Whitepoint
from obs_codegen._colorcomponents import Cat
from obs_codegen._colorcomponents import AssemblyColorspace
from obs_codegen._colorcomponents import ColorspaceGamut
from obs_codegen._colorcomponents import TransferFunction

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BaseGenerator:
    """
    Generate HLSL code as a string following the given input attributes.
    """

    colorspaces_gamut: list[ColorspaceGamut]
    whitepoints: list[Whitepoint]
    cats: list[Cat]
    colorspaces_assemblies: list[AssemblyColorspace]
    transfer_functions: list[TransferFunction]

    @abstractmethod
    def generateCode(self) -> str:
        """
        Returns:
            valid "standalone" code snippet
        """
        pass
