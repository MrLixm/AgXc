import contextlib
import dataclasses
import enum

from typing import Optional
from typing import ContextManager

import PyOpenColorIO as ocio


class BaseFamily(enum.Enum):
    """
    An abstract class to define multiple colorspace families
    """

    pass


@dataclasses.dataclass
class Colorspace:
    """
    simple wrapper function on ocio.ColorSpace to have better default/type-hinting
    """

    name: str
    family: Optional[BaseFamily] = None
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
class View:
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
) -> ContextManager[Colorspace]:
    """
    To use as::

        with build_ocio_colorspace("my Colorspace", config) as colorspace:
            colorspace.isData = True
    """
    colorspace = Colorspace(name=name)
    try:
        yield colorspace
    finally:
        ocio_colorspace = colorspace.asOCIO()
        config.addColorSpace(ocio_colorspace)


@contextlib.contextmanager
def build_display_views(
    display_name: str, config: ocio.Config
) -> ContextManager[list[View]]:
    """
    To use as::

        with build_display_views("my Display", config) as display:
            display.append(_View("myView", "my Colorspace"))
    """
    views: list[View] = []
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
