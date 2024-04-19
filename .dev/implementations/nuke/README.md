# src

This is the source "code" that must be compiled to produce the results that can
be seen one level up.

# developing

All the `.nk` file are handwritten (no copy-paste from nuke).

They incorporate a "variable syntax" that allow inserting nuke script at build
time. Example:
```
Group {
  name myGroup
}
 %GROUP_CONTENT:{"name": "innerNode", "ypos": 150}%
end_group
```
In the above the variable `GROUP_CONTENT` is defined in the `build.py` and
is assigned to the content it must be replaced with. Additionally everything after
the smei colon `:` is a json dict of knobs overrides to apply on the top node.


# build instructions

# prerequisites

* `python>=3.10`
* internet connection for file download

# steps

Run `build.py` with a python intepreter. BEFORE you would need to "precompile"
the blink script for [AgXcTonescale](AgXcTonescale) :

- In the desired nuke version create a new BlinkScript node :
    ```
    BlinkScript {
     inputs 1
     recompileCount 2
     ProgramGroup 1
     addUserKnob {20 User}
     addUserKnob {22 extract_compile T "node = nuke.thisNode()\nprint(repr(node\[\"kernelSource\"].getValue()))\nprint()\nprint(repr(node\[\"KernelDescription\"].getValue()))"}
    }
    ```
- Paste the `.blink` code of this repo in the node
- Click `Recompile` button
- Click the `extract_compile` button in the User tab of the node
- In the script editor look at the 3 last lines that have been printed (be careful the
 line are wrapped).
- Copy the first line to a file `AgXcTonescale/AgXcTonescale.blink.src`
  * make sure to remove the trailling quotes `'`
  * make sure there is only one line
- Copy the third line after the blank one to a file `AgXcTonescale/AgXcTonescale.blink.desc`
  * make sure to remove the trailling quotes `'`
  * make sure there is only one line

Those steps would need to be executed again each time the blink script is modified.