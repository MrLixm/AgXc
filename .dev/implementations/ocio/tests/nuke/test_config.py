from pathlib import Path

import nuke


def main():
    print("test started")

    # XXX: we assume current working directory is correctly set
    this_dir = Path(".").resolve()
    repo_dir = this_dir.parent.parent.parent.parent.parent

    agx_config_path = repo_dir / "ocio" / "config.ocio"
    assert agx_config_path.exists(), agx_config_path
    assert agx_config_path.is_absolute(), agx_config_path

    # XXX: nuke expect posix-like paths
    agx_config_path = agx_config_path.as_posix()

    nuke.root()["colorManagement"].setValue("OCIO")
    nuke.root()["OCIO_config"].setValue("custom")
    nuke.root()["customOCIOConfigPath"].setValue(agx_config_path)

    assert nuke.usingOcio()
    ocio_error = nuke.root()["ocio_config_error_knob"].value().lstrip(" ")
    assert not ocio_error, ocio_error

    ocio_display_node = nuke.createNode("OCIODisplay")
    assert ocio_display_node["display"].value() == "sRGB"
    assert ocio_display_node["view"].value() == "AgX Punchy"
    print("test finished")


if __name__ == "__main__":
    main()
