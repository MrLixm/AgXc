import json
import logging
import re
import shutil
import sys
import tempfile
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)


THIS_DIR = Path(__file__).parent
TEMP_DIR = Path(tempfile.mkdtemp(prefix="AgXc-nuke-build"))


class BuildPaths:
    src_AgXcDRT_node = THIS_DIR / "AgXcDRT" / "AgXcDRT-template.nk"
    assert src_AgXcDRT_node.exists()

    src_AgXcTonescale_node = THIS_DIR / "AgXcTonescale" / "AgXcTonescale-template.nk"
    assert src_AgXcTonescale_node.exists()

    src_AgXcTonescale_blink_src = THIS_DIR / "AgXcTonescale" / "AgXcTonescale.blink.src"
    assert src_AgXcTonescale_blink_src.exists()
    src_AgXcTonescale_blink_desc = (
        THIS_DIR / "AgXcTonescale" / "AgXcTonescale.blink.desc"
    )
    assert src_AgXcTonescale_blink_desc.exists()

    dst_dir = THIS_DIR.parent
    dst_AgXcDRT_node = dst_dir / "AgXcDRT.nk"
    dst_AgXcTonescale_node = dst_dir / "AgXcTonescale.nk"


def _download_file(url: str, target_file: Path) -> Path:
    url_opener = urllib.request.build_opener()
    # this prevents some website from blocking the connection (example: Blender)
    url_opener.addheaders = [("User-agent", "Mozilla/5.0")]

    with url_opener.open(url) as url_stream, open(target_file, "wb") as file:
        shutil.copyfileobj(url_stream, file)

    return target_file


def _download_web_nukenode(url: str, license_url: Optional[str] = None) -> str:
    """
    Download a .nk file from the web and ensure it can be inserted into other nk file.

    Optional append its license on top.

    Args:
        url: web url to the raw nk file.
    """
    temp_file = TEMP_DIR / str(uuid.uuid4())

    src_node = _download_file(url, temp_file).read_text("utf-8")
    temp_file.unlink()
    src_node = src_node.rstrip("\n")

    src_license = []
    if license_url:
        src_license = _download_file(license_url, temp_file).read_text("utf-8")
        temp_file.unlink()
        src_license = src_license.rstrip("\n")
        src_license = src_license.split("\n")

    newnode = src_node.split("\n")
    if newnode[0].startswith("set cut_paste_input"):
        newnode = newnode[1:]
    if newnode[0].startswith("push $cut_paste_input"):
        newnode = newnode[1:]

    # append license on top as comment
    newnode = ["#" + line for line in src_license] + newnode

    newnode = [f"# startfrom: {url}"] + newnode + ["# endfrom"]

    newnode = "\n".join(newnode)
    return newnode


def _sanitize_nuke_script(script: str, convert_new_lines=True) -> str:
    if convert_new_lines:
        newscript = script.replace("\\", r"\\")
        newscript = newscript.split("\n")
        newscript = r"\n".join(newscript)
    else:
        newscript = script.split(r"\n")
        newscript = [line.replace("\\", r"\\") for line in newscript]
        newscript = r"\n".join(newscript)

    newscript = newscript.replace('"', r"\"")
    newscript = newscript.replace("{", r"\{")
    newscript = newscript.replace("}", r"\}")
    newscript = newscript.replace("[", r"\[")
    return newscript


def _get_nuke_syntax_topnode_lines(nuke_script: list[str]) -> tuple[int, int]:
    """
    From a nuke script return the line on that start and end the initialization of the
    top node. Example::

        0 # header comment
        1 Group {
        2  name myGroup
        3  someKnob {{tcl expression}}
        4 }
        5 end_group
        6 Dot {
        7 }

    will return (1,4)

    Args:
        nuke_script: nuke syntax as list of lines

    Returns:
        index of start line, index of end line
    """
    start_index = -1
    end_index = -1
    brack_open_count = 0

    for line_index, line in list(enumerate(nuke_script)):
        if line.strip(" ").startswith("#"):
            continue

        if "{" in line and start_index == -1:
            start_index = line_index
            brack_open_count = 1
            continue

        brack_open_count += line.count("{")
        # remove escaped brackets that doesn't count
        brack_open_count -= line.count(r"\{")

        brack_open_count -= line.count("}")
        # add back escaped brackets that doesn't count
        brack_open_count += line.count(r"\}")

        if brack_open_count == 0:
            end_index = line_index
            break

    return start_index, end_index


def _override_nuke_node_knobs(
    nuke_node: list[str],
    overrides: dict[str, str],
) -> list[str]:
    """
    Parser that is able to override knobs values on a nuke node provided as list of lines.

    Args:
        nuke_node:
            as list of lines.
        overrides:
            knobs override to apply where key="knob name" and value="new knob value".
            One must avoid to create a key named "addUserKnob" !!

    Returns:
        nuke_node with overrides, still as list of lines
    """
    new_node = list(nuke_node)  # make a copy
    _overrides = dict(overrides)  # make a copy

    # // we replace existing knob assignation by our overrides :
    for line_index, line in enumerate(new_node):
        # we stop parsing at the end of the first top node definition
        if line.startswith("}"):
            break

        for override_name, overrides_value in overrides.items():
            if re.match(rf"\s*{override_name}\s", line.strip(" ")):
                new_node[line_index] = f" {override_name} {overrides_value}"
                # we cannot pop a dict we are iterating over, so pop the copy
                _overrides.pop(override_name)

    _, node_end_init_index = _get_nuke_syntax_topnode_lines(new_node)

    # // we add leftover overrides that were not initally set on the node
    for override_name, overrides_value in _overrides.items():
        new_node.insert(node_end_init_index, f" {override_name} {overrides_value}")

    return new_node


def _replace_variable_in_line(
    line: str, name: str, new_lines: list[str]
) -> Optional[list[str]]:
    """
    Replace the given variable with the given lines.

    If the variable is not in the line, None is returned.

    Also handle the system to override nuke knobs defined in the variable "suffix"::

        %VAR_NAME:{"knob name": "knob value", ...}%
    """
    if not line.strip(" ").startswith(f"%{name}"):
        return None

    new_lines = list(new_lines)  # make a copy

    override_pattern = re.compile(r"\s*%(?P<name>\w+):?(?P<overrides>.*)%")
    overrides: Optional[str] = override_pattern.search(line).group("overrides")
    if overrides:
        overrides: Optional[dict] = json.loads(overrides)
        LOGGER.debug(f"({name}): applying overrides {overrides}")
        new_lines = _override_nuke_node_knobs(new_lines, overrides)

    # calculate how much the variable is indented in the original line
    indent = len(line) - len(line.lstrip(" "))
    # add the indent calculated previously to each line
    return [" " * indent + new_line for new_line in new_lines]


def build_AgXcDRT():
    template_node = BuildPaths.src_AgXcDRT_node.read_text("utf-8")

    LOGGER.info("downloading PlotSlice node")
    plotslice_node = _download_web_nukenode(
        url="https://github.com/jedypod/nuke-colortools/raw/master/toolsets/visualize/PlotSlice.nk",
        license_url="https://github.com/jedypod/nuke-colortools/raw/master/LICENSE.md",
    )

    LOGGER.info("downloading SigmoidParabolic node")
    sigmoidp_node = _download_web_nukenode(
        url="https://github.com/jedypod/nuke-colortools/raw/master/toolsets/transfer_function/SigmoidParabolic.nk",
        license_url="https://github.com/jedypod/nuke-colortools/raw/master/LICENSE.md",
    )

    LOGGER.info("downloading Log2Shaper node")
    log2_node = _download_web_nukenode(
        url="https://github.com/jedypod/nuke-colortools/raw/master/toolsets/transfer_function/Log2Shaper.nk",
        license_url="https://github.com/jedypod/nuke-colortools/raw/master/LICENSE.md",
    )

    LOGGER.info("downloading PrimariesInset node")
    primariesinset_node = _download_web_nukenode(
        url="https://github.com/MrLixm/Foundry_Nuke/raw/main/src/primaries_inset/PrimariesInset.nk",
    )

    tonescale_node = BuildPaths.dst_AgXcTonescale_node.read_text("utf-8")

    new_node = []

    for line in template_node.split("\n"):
        # we can only have one variable defined per line
        new_lines = _replace_variable_in_line(
            line,
            name="NODE_PlotSlice",
            new_lines=plotslice_node.split("\n"),
        )
        new_lines = new_lines or _replace_variable_in_line(
            line,
            name="NODE_SigmoidParabolic",
            new_lines=sigmoidp_node.split("\n"),
        )
        new_lines = new_lines or _replace_variable_in_line(
            line,
            name="NODE_AgXcTonescale",
            new_lines=tonescale_node.split("\n"),
        )
        new_lines = new_lines or _replace_variable_in_line(
            line,
            name="NODE_Log2Shaper",
            new_lines=log2_node.split("\n"),
        )
        new_lines = new_lines or _replace_variable_in_line(
            line,
            name="NODE_PrimariesInset",
            new_lines=primariesinset_node.split("\n"),
        )
        if new_lines:
            new_node += new_lines
        else:
            new_node.append(line)

    new_node = "\n".join(new_node)
    LOGGER.info(f"writting <{BuildPaths.dst_AgXcDRT_node}>")
    BuildPaths.dst_AgXcDRT_node.write_text(new_node, "utf-8")


def build_AgXcTonescale():
    template_node = BuildPaths.src_AgXcTonescale_node.read_text("utf-8")

    blink_source = BuildPaths.src_AgXcTonescale_blink_src.read_text("utf-8")
    blink_source = _sanitize_nuke_script(blink_source, False)
    blink_source = f'kernelSource "{blink_source}"'

    blink_desc = BuildPaths.src_AgXcTonescale_blink_desc.read_text("utf-8")
    blink_desc = _sanitize_nuke_script(blink_desc, False)
    blink_desc = f'KernelDescription "{blink_desc}"'

    new_node = []

    for line in template_node.split("\n"):
        # we can only have one variable defined per line
        new_lines = _replace_variable_in_line(
            line,
            name="BLINK_SRC",
            new_lines=[blink_source],
        )
        new_lines = new_lines or _replace_variable_in_line(
            line,
            name="BLINK_DESC",
            new_lines=[blink_desc],
        )
        if new_lines:
            new_node += new_lines
        else:
            new_node.append(line)

    new_node = "\n".join(new_node)
    LOGGER.info(f"writting <{BuildPaths.dst_AgXcDRT_node}>")
    BuildPaths.dst_AgXcTonescale_node.write_text(new_node, "utf-8")


def build():
    LOGGER.info(f"build started")
    build_AgXcTonescale()
    build_AgXcDRT()
    LOGGER.info("build finished")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="{levelname: <7} | {asctime} [{name}] {message}",
        style="{",
        stream=sys.stdout,
    )
    build()
