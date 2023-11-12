/* --------------------------------------------------------------------------------
Transfer functions

References
----------

All data without explicit reference can assumed to be extracted/generated from `colour-science` python library.

- [1] https://github.com/sobotka/AgX-S2O3/blob/main/AgX.py
- [2] https://github.com/colour-science/colour/blob/develop/colour/models/rgb/transfer_functions/srgb.py#L99
- [3] https://dl.fujifilm-x.com/support/lut/F-Log_DataSheet_E_Ver.1.0.pdf
- [4] https://dl.fujifilm-x.com/support/lut/F-Log2_DataSheet_E_Ver.1.0.pdf
- [5] https://github.com/colour-science/colour/blob/develop/colour/models/rgb/transfer_functions/fujifilm_f_log.py
- [6] http://download.nikonimglib.com/archive3/hDCmK00m9JDI03RPruD74xpoU905/N-Log_Specification_(En)01.pdf
-------------------------------------------------------------------------------- */

float3 cctf_log2_normalized_from_open_domain(float3 color, float minimum_ev, float maximum_ev)
/*
    Output log domain encoded data.

    Similar to OCIO lg2 AllocationTransform.

    --ref[1]
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

float3 cctf_encoding_BT_2020(float3 color){
    return (color < 0.0181) ? color * 4.5 : 1.0993 * powsafe(color, 0.45) - (1.0993 - 1);
}
float3 cctf_decoding_BT_2020(float3 color){
    return (color < cctf_encoding_BT_2020(0.0181)) ? color / 4.5 : powsafe((color + (1.0993 - 1)) / 1.0993, 1 / 0.45) ;
}

float3 cctf_decoding_Display_P3(float3 color){return cctf_decoding_sRGB_EOTF(color);}
float3 cctf_encoding_Display_P3(float3 color){return cctf_encoding_sRGB_EOTF(color);}

float3 cctf_decoding_Adobe_RGB_1998(float3 color){return powsafe(color, 2.19921875);}
float3 cctf_encoding_Adobe_RGB_1998(float3 color){return powsafe(color, 1/2.19921875);}


struct _FLogConstants {
    float a;
    float b;
    float c;
    float d;
    float e;
    float f;
    float cut1;
    float cut2;
};
// ref[3]
_FLogConstants FLogConstants(){
    _FLogConstants output;
    output.a = 0.555556;
    output.b = 0.009468;
    output.c = 0.344676;
    output.d = 0.790453;
    output.e = 8.735631;
    output.f = 0.092864;
    output.cut1 = 0.00089;
    output.cut2 = 0.10053777522386;
    return output;
}
// ref[4]
_FLogConstants FLog2Constants(){
    _FLogConstants output;
    output.a = 5.555556;
    output.b = 0.064829;
    output.c = 0.245281;
    output.d = 0.384316;
    output.e = 8.799461;
    output.f = 0.092864;
    output.cut1 = 0.000889;
    output.cut2 = 0.100686685370811;
    return output;
}

// ref[3][4][5]
float3 _cctf_decoding_FLog(float3 color, _FLogConstants flconst){
    return color < flconst.cut2 ?
        (color - flconst.f) / flconst.e :
        powsafe(10.0, ((color - flconst.d) / flconst.c)) / flconst.a - flconst.b / flconst.a;
}
float3 _cctf_encoding_FLog(float3 color, _FLogConstants flconst){
    return color < flconst.cut1 ?
        flconst.e * color + flconst.f :
        flconst.c * log10(flconst.a * color + flconst.b) + flconst.d;
}

float3 cctf_decoding_FLog(float3 color){return _cctf_decoding_FLog(color, FLogConstants());}
float3 cctf_encoding_FLog(float3 color){return _cctf_encoding_FLog(color, FLogConstants());}

float3 cctf_decoding_FLog2(float3 color){return _cctf_decoding_FLog(color, FLog2Constants());}
float3 cctf_encoding_FLog2(float3 color){return _cctf_encoding_FLog(color, FLog2Constants());}

struct _NLogConstants {
    float a;
    float b;
    float c;
    float d;
    float cut1;
    float cut2;
};
// ref[6]
_NLogConstants NLogConstants(){
    _NLogConstants output;
    output.a = 650.0/1023.0;
    output.b = 0.0075;
    output.c = 150.0/1023.0;
    output.d = 619.0/1023.0;
    output.cut1 = 0.328;
    output.cut2 = 452.0/1023.0;
    return output;
}
// ref[6]
float3 cctf_decoding_NLog(float3 color){
     _NLogConstants nlconst = NLogConstants();
     return color < nlconst.cut2 ?
            powsafe(color/nlconst.a, 3.0) - nlconst.b:
            exp((color - nlconst.d) / nlconst.c);
}
float3 cctf_encoding_NLog(float3 color){
     _NLogConstants nlconst = NLogConstants();
     return color < nlconst.cut1 ?
            nlconst.a * powsafe(color + nlconst.b, 1.0/3.0):
            nlconst.c * log(color) + nlconst.d;
}
