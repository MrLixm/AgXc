/*
HLSL implementation of AgX for OBS.

AgX is originally designed by Troy Sobotka.

References:
- [1] https://github.com/Fubaxiusz/fubax-shaders/blob/master/Shaders/LUTTools.fx
*/

float3 _applyAgXLog(float3 Image)
/*
    Prepare the data for display encoding. Converted to log domain.
*/
{

    float3x3 agx_compressed_matrix = {
        0.84247906, 0.0784336, 0.07922375,
        0.04232824, 0.87846864, 0.07916613,
        0.04237565, 0.0784336, 0.87914297
    };

    Image = max(0.0, Image); // clamp negatives
    // why this doesn't work ??
    // Image = mul(agx_compressed_matrix, Image);
	Image = apply_matrix(Image, agx_compressed_matrix);

    if (USE_OCIO_LOG)
        Image = cctf_log2_ocio_transform(Image);
    else
        Image = cctf_log2_normalized_from_open_domain(Image, -10.0, 6.5);

    Image = clamp(Image, 0.0, 1.0);
    return Image;
}

float3 _applyAgXLUT(float3 Image)
/*
    Apply the AgX 1D curve on log encoded data.

    The output is similar to AgX Base which is considered
    sRGB - Display, but here we linearize it.

    -- ref[1] for LUT implementation
*/
{

    float3 lut3D = Image * (AgXLUT_BLOCK_SIZE-1);

    float2 lut2D[2];
    // Front
    lut2D[0].x = floor(lut3D.z) * AgXLUT_BLOCK_SIZE+lut3D.x;
    lut2D[0].y = lut3D.y;
    // Back
    lut2D[1].x = ceil(lut3D.z) * AgXLUT_BLOCK_SIZE+lut3D.x;
    lut2D[1].y = lut3D.y;

    // Convert from texel to texture coords
    lut2D[0] = (lut2D[0]+0.5) * AgXLUT_PIXEL_SIZE;
    lut2D[1] = (lut2D[1]+0.5) * AgXLUT_PIXEL_SIZE;

    // Bicubic LUT interpolation
    Image = lerp(
        AgXLUT.Sample(LUTSampler, lut2D[0]).rgb, // Front Z
        AgXLUT.Sample(LUTSampler, lut2D[1]).rgb, // Back Z
        frac(lut3D.z)
    );
    // LUT apply the transfer function so we remove it to keep working on linear data.
    Image = cctf_decoding_Power_2_2(Image);
    return Image;
}

float3 _applyOutset(float3 Image)
/*
    Outset is the inverse of the inset applied during `applyAgXLog`
    and restore chroma.
*/
{

    float3x3 agx_compressed_matrix_inverse = {
        1.1968790, -0.09802088, -0.09902975,
        -0.05289685, 1.15190313, -0.09896118,
        -0.05297163, -0.09804345, 1.15107368
    };
	Image = apply_matrix(Image, agx_compressed_matrix_inverse);

    return Image;
}

float3 applyAgX(float3 Image)
/*
    Apply the chain of operations for the AgX DRT.
*/
{
    Image = _applyAgXLog(Image);
    Image = _applyAgXLUT(Image);
    return Image;
}

float3 applyAgXOutset(float3 Image)
/*
    Apply the chain of operations for the AgX DRT but apply the outset operation.
*/
{
    Image = applyAgX(Image);
    Image = _applyOutset(Image);
    return Image;
}