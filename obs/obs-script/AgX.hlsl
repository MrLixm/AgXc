/*
HLSL implementation of AgX for OBS.

AgX is a Display Rendering Transform designed by Troy Sobotka.

The code is not AgX-specific and actually very flexible to integrate any other DRT.

author = "Liam Collod"
repository = "https://github.com/MrLixm/AgXc"

References:
- [0] https://github.com/sobotka/AgX-S2O3/blob/main/AgX.py
- [1] https://github.com/Unity-Technologies/Graphics/blob/master/com.unity.postprocessing/PostProcessing/Shaders/Colors.hlsl
- [2] https://video.stackexchange.com/q/9866
- [3] https://github.com/Fubaxiusz/fubax-shaders/blob/master/Shaders/LUTTools.fx
- [4] https://github.com/Unity-Technologies/Graphics/blob/master/com.unity.postprocessing/PostProcessing/Shaders/Colors.hlsl#L574
- [5] https://github.com/colour-science/colour/blob/develop/colour/models/rgb/transfer_functions/srgb.py#L99
*/

// OBS-specific syntax adaptation to HLSL standard to avoid errors reported by the code editor
#define SamplerState sampler_state
#define Texture2D texture2d

// Uniform variables set by OBS (required)
uniform float4x4 ViewProj; // View-projection matrix used in the vertex shader
uniform Texture2D image;   // Texture containing the source picture

uniform int INPUT_COLORSPACE = 1;
uniform int OUTPUT_COLORSPACE = 1;
/*
colorspaceid_Passthrough = 0;
colorspaceid_sRGB_Display_EOTF = 1;
colorspaceid_sRGB_Display_2_2 = 2;
colorspaceid_sRGB_Linear = 3;
colorspaceid_BT_709_Display_2_4 = 4;
colorspaceid_DCIP3_Display_2_6 = 5;
colorspaceid_Apple_Display_P3 = 6;
*/
uniform int DRT = 1;
uniform float INPUT_EXPOSURE = 0.5;
uniform float INPUT_GAMMA = 1.0;
uniform float INPUT_SATURATION = 1.0;
uniform float INPUT_HIGHLIGHT_GAIN = 1.5;
uniform float INPUT_HIGHLIGHT_GAIN_GAMMA = 1.0;
uniform float PUNCH_EXPOSURE = 0.0;
uniform float PUNCH_SATURATION = 1.0;
uniform float PUNCH_GAMMA = 1.0;
uniform bool USE_OCIO_LOG = false;

// LUT AgX-default_contrast.lut.png
uniform texture2d AgXLUT;
#define AgXLUT_BLOCK_SIZE 32
#define AgXLUT_DIMENSIONS int2(AgXLUT_BLOCK_SIZE * AgXLUT_BLOCK_SIZE, AgXLUT_BLOCK_SIZE)
#define AgXLUT_PIXEL_SIZE 1.0 / AgXLUT_DIMENSIONS

#define colorspaceid_working_space colorspaceid_sRGB_Linear


uniform int drt_id_none = 0;
uniform int drt_id_agx = 1;
uniform int drt_id_agx_outset = 2;

/*=================
    OBS BOILERPLATE
=================*/

// Interpolation method and wrap mode for sampling a texture
sampler_state linear_clamp
{
    Filter    = Linear;     // Anisotropy / Point / Linear
    AddressU  = Clamp;      // Wrap / Clamp / Mirror / Border / MirrorOnce
    AddressV  = Clamp;      // Wrap / Clamp / Mirror / Border / MirrorOnce
    BorderColor = 00000000; // Used only with Border edges (optional)
};
sampler_state LUTSampler
{
	Filter    = Linear;
	AddressU  = Clamp;
	AddressV  = Clamp;
	AddressW  = Clamp;
};
struct VertexData
{
    float4 pos : POSITION;  // Homogeneous space coordinates XYZW
    float2 uv  : TEXCOORD0; // UV coordinates in the source picture
};
struct PixelData
{
    float4 pos : POSITION;  // Homogeneous screen coordinates XYZW
    float2 uv  : TEXCOORD0; // UV coordinates in the source picture
};

// order matters + need the constants defined above
#include "lib_math.hlsl"
#include "lib_colorscience.hlsl"
#include "lib_grading.hlsl"
#include "lib_agx.hlsl"

/*=================
    Main processes
=================*/


float3 applyInputTransform(float3 Image)
/*
    Convert input to workspace colorspace (sRGB)
*/
{
    return convertColorspaceToColorspace(Image, INPUT_COLORSPACE, colorspaceid_working_space);
}

float3 applyOpenGrading(float3 Image)
/*
    Apply creative grading on open-domain image state.

    :param Image: expected to be in a open-domain state.
*/
{

    float ImageLuma = powsafe(get_luminance(Image), INPUT_HIGHLIGHT_GAIN_GAMMA);
    Image += Image * ImageLuma.xxx * INPUT_HIGHLIGHT_GAIN;

    Image = saturation(Image, INPUT_SATURATION);
    Image = powsafe(Image, INPUT_GAMMA);
    Image *= powsafe(2.0, INPUT_EXPOSURE);
    return Image;
}

float3 applyDRT(float3 Image)
/*
    Apply the DRT selected by the user.
*/
{
    if (DRT == drt_id_agx){
        Image = applyAgX(Image);
    }
    if (DRT == drt_id_agx_outset){
        Image = applyAgXOutset(Image);
    }
    return Image;

}

float3 applyODT(float3 Image)
/*
    Apply Agx to display conversion.

    :param color: linear - sRGB data.

*/
{
    return convertColorspaceToColorspace(Image, colorspaceid_working_space, OUTPUT_COLORSPACE);
}


float3 applyDisplayGrading(float3 Image)
/*
    Apply creative grading on display-domain image state.

    :param Image: expected to be in a display-state.
*/
{
    Image = powsafe(Image, PUNCH_GAMMA);
    Image = saturation(Image, PUNCH_SATURATION);
    Image *= powsafe(2.0, PUNCH_EXPOSURE);  // not part of initial cdl
    return Image;

}


PixelData VERTEXSHADER_AgX(VertexData vertex)
{
    PixelData pixel;
    pixel.pos = mul(float4(vertex.pos.xyz, 1.0), ViewProj);
    pixel.uv  = vertex.uv;
    return pixel;
}

float4 PIXELSHADER_AgX(PixelData pixel) : TARGET
{
    float4 OriginalImage = image.Sample(linear_clamp, pixel.uv);
    float3 Image = OriginalImage.rgb;
    Image = applyInputTransform(Image);
    Image = applyOpenGrading(Image);
    Image = applyDRT(Image);
    Image = applyODT(Image);
    Image = applyDisplayGrading(Image);

    Image = convertColorspaceToColorspace(Image, 1, 4);

    return float4(Image.rgb, OriginalImage.a);
}


technique Draw
{
    pass
    {
        vertex_shader = VERTEXSHADER_AgX(vertex);
        pixel_shader  = PIXELSHADER_AgX(pixel);
    }
}