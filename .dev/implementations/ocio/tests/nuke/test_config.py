import sys
from pathlib import Path

import nuke


def main():
    print("test started")

    ocio_path = sys.argv[1]
    assert ocio_path

    ocio_path = Path(ocio_path).resolve()
    assert ocio_path.exists(), ocio_path
    assert ocio_path.is_absolute(), ocio_path

    print(f"using ocio config {ocio_path}")

    # XXX: nuke expect posix-like paths
    ocio_path = ocio_path.as_posix()

    nuke.root()["colorManagement"].setValue("OCIO")
    nuke.root()["OCIO_config"].setValue("custom")
    nuke.root()["customOCIOConfigPath"].setValue(ocio_path)

    assert nuke.usingOcio()
    ocio_error = nuke.root()["ocio_config_error_knob"].value().lstrip(" ")
    assert not ocio_error, ocio_error

    ocio_display_node = nuke.createNode("OCIODisplay")
    assert ocio_display_node["display"].value() == "sRGB"
    assert ocio_display_node["view"].value() == "AgX Punchy"
    print("test finished")


if __name__ == "__main__":
    main()
