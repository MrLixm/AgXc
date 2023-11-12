/* --------------------------------------------------------------------------------
Transfer functions
-------------------------------------------------------------------------------- */

float3 cctf_log2_normalized_from_open_domain(float3 color, float minimum_ev, float maximum_ev)
/*
    Output log domain encoded data.

    Similar to OCIO lg2 AllocationTransform.

    ref[1]
*/
{
    float in_midgrey = 0.18;

    // remove negative before log transform
    color = max(0.0, color);
    // avoid infinite issue with log -- ref[1]
    color = (color  < 0.00003051757) ? (0.00001525878 + color) : (color);
    color = clamp(
        log2(color / in_midgrey),
        float3(minimum_ev, minimum_ev, minimum_ev),
        float3(maximum_ev,maximum_ev,maximum_ev)
    );
    float total_exposure = maximum_ev - minimum_ev;

    return (color - minimum_ev) / total_exposure;
}

// exactly the same as above but I let it for reference
float3 cctf_log2_ocio_transform(float3 color)
/*
    Output log domain encoded data.

    Copy of OCIO lg2 AllocationTransform with the AgX Log values.

    :param color: rgba linear color data
*/
{
    // remove negative before log transform
    color = max(0.0, color);
    color = (color  < 0.00003051757) ? (log2(0.00001525878 + color * 0.5)) : (log2(color));

    // obtained via m = ocio.MatrixTransform.Fit(oldMin=[-12.47393, -12.47393, -12.47393, 0.0], oldMax=[4.026069, 4.026069, 4.026069, 1.0])
    float3x3 fitMatrix = float3x3(
        0.060606064279155415, 0.0, 0.0,
        0.0, 0.060606064279155415, 0.0,
        0.0, 0.0, 0.060606064279155415
    );
    // obtained via same as above
    float fitMatrixOffset = 0.7559958033936851;
    color = mul(fitMatrix, color);
    color += fitMatrixOffset.xxx;

    return color;
}

float3 cctf_decoding_sRGB_EOTF(float3 color){
    // ref[2]
    return (color <= 0.04045) ? (color / 12.92) : (powsafe((color + 0.055) / 1.055, 2.4));
}

float3 cctf_encoding_sRGB_EOTF(float3 color){
    // ref[2]
    return (color <= 0.0031308) ? (color * 12.92) : (1.055 * powsafe(color, 1/2.4) - 0.055);
}

float3 cctf_decoding_Power_2_2(float3 color){return powsafe(color, 2.2);}

float3 cctf_encoding_Power_2_2(float3 color){return powsafe(color, 1/2.2);}

float3 cctf_decoding_BT_709(float3 color){return powsafe(color, 2.4);}

float3 cctf_encoding_BT_709(float3 color){return powsafe(color, 1/2.4);}

float3 cctf_decoding_DCIP3(float3 color){return powsafe(color, 2.6);}

float3 cctf_encoding_DCIP3(float3 color){return powsafe(color, 1/2.6);}

float3 cctf_encoding_BT_2020(float3 color){return (color < 0.0181) ? color * 4.5 : 1.0993 * powsafe(color, 0.45) - (1.0993 - 1);}

float3 cctf_decoding_BT_2020(float3 color){return (color < cctf_encoding_BT_2020(0.0181)) ? color / 4.5 : powsafe((color + (1.0993 - 1)) / 1.0993, 1 / 0.45) ;}

float3 cctf_decoding_Display_P3(float3 color){return cctf_decoding_sRGB_EOTF(color);}

float3 cctf_encoding_Display_P3(float3 color){return cctf_encoding_sRGB_EOTF(color);}

float3 cctf_decoding_Adobe_RGB_1998(float3 color){return powsafe(color, 2.19921875);}

float3 cctf_encoding_Adobe_RGB_1998(float3 color){return powsafe(color, 1/2.19921875);}
