# Developer documentation

# Introduction.

- `AgX.lua` : direct interface with OBS used for building the GUI
- `AgX.hlsl` : GPU shader with the actual AgX code.
- `colorspace.hlsl` : side-library imported in `AgX.hlsl`
  - this is actually the public interface of the `colorscience/` "package".
- `colorscience/` library of hlsl modules for color manipulation. some of the modules
are code-generated and not intended to be edited directly. Directly editable modules are :
  - `math.hlsl`
  - `cctf.hlsl`

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
