# Developer documentation

# Introduction.

- `AgX.lua` : direct interface with OBS used for building the GUI
- `AgX.hlsl` : top-level GPU shader used in the lua script.

With that you will find additional hlsl modules that are all imported in `AgX.hlsl` :

- `lib_colorscience.hlsl`: library of hlsl modules for color manipulation
  - `_lib_colorscience/`: some of the modules are procedurally-generated and not 
   intended to be edited directly (see header comment).

The "procedurally" generated code can be found in the [../src/](../src) directory.

# Add a new colorspace.

## Case 1 : gamut/whitepoint/cctf are already there.

You will need :

1. Modify the `../src/scripts/build-colorspace_core.hlsl.py` by adding the new colorspace.
   1. This is done by adding a new instance of `AssemblyColorspace`.
2. Run the script, this will automatically take care of the hlsl code.
3. You will need to manually update the LUA code :
   1. copy the lua code generated and print in the console to `AgX.lua` where it "seems" to belong. 
   (for now just adding entries to the properties dropdown)

## Case 2 : whole new colorspace

Similar to Case 1 but :

- the step 1.1 is more complex : you also have to add a new Gamut/TransferFunction/Whitepoint
instance if needed.
- If you added a new `TransferFunction` you will need to manually write its 
hlsl code in the `colorscience/cctf.hlsl` module. Note the name of the function
can be found in `cctf-auto.hlsl` after running the build script.
