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
- [7] https://github.com/colour-science/colour/blob/develop/colour/models/rgb/transfer_functions/sony.py
- [8] https://drive.google.com/file/d/1Q1RYri6BaxtYYxX0D4zVD6lAmbwmgikc/view
- [9] https://pro-av.panasonic.net/en/cinema_camera_varicam_eva/support/pdf/VARICAM_V-Log_V-Gamut.pdf
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
        pow(10.0, ((color - flconst.d) / flconst.c)) / flconst.a - flconst.b / flconst.a;
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

struct _SLogConstants {
    float a;
    float b;
    float c;
    float d;
    float e;
    float f;
    float g;
    float h;
};
// ref[7][8]
_SLogConstants SLogConstants(){
    _SLogConstants output;
    output.a = 0.432699;
    output.b = 0.616596;
    output.c = 0.030001222851889303;
    output.d = 3.53881278538813;
    output.e = 0.03;
    output.f = 155.0;
    output.g = 219.0;
    output.h = 0.037584;
    return output;
}
// ref[7]
float3 cctf_encoding_SLog(float3 color){
     _SLogConstants slconst = SLogConstants();
     // convert from reflection to IRE
     float3 outcolor = color / 0.9;
     outcolor = color >= 0.0 ?
            (slconst.a * log10(outcolor + slconst.h) + slconst.b) + slconst.e:
            outcolor * 5.0 + slconst.c;
     // asume bitdepth=10 and out_normalised_code_value=True compared to colour
     return convert_cctf_full_to_legal(outcolor);

}
float3 cctf_decoding_SLog(float3 color){
     _SLogConstants slconst = SLogConstants();
     // asume bitdepth=10 and in_normalised_code_value=True compared to colour
     float3 outcolor = convert_cctf_legal_to_full(color);
     outcolor = color >= cctf_encoding_SLog(0.0) ?
            pow(10.0, (color - slconst.b - slconst.e) / slconst.a) - slconst.h:
            (color - slconst.c) / 5.0;
     // convert IRE to reflection
     return outcolor * 0.9;

}

float3 cctf_decoding_SLog2(float3 color){return 219.0 * cctf_decoding_SLog(color) / 155.0;}
float3 cctf_encoding_SLog2(float3 color){return cctf_encoding_SLog(color * 155.0 / 219.0);}


// ref[7]
float3 cctf_decoding_SLog3(float3 color){
     float slconst_a = 0.01125000;
     float slconst_b = 171.2102946929;
     return color >= slconst_b / 1023.0 ?
            pow(10.0, (color * 1023.0 - 420.0) / 261.5) * (0.18 + 0.01) - 0.01:
            (color * 1023.0 - 95.0) * slconst_a / (slconst_b - 95.0);
}
float3 cctf_encoding_SLog3(float3 color){
     float slconst_a = 0.01125000;
    float slconst_b = 171.2102946929;
     return color >= slconst_a ?
            (420.0 + log10((color + 0.01) / (0.18 + 0.01)) * 261.5) / 1023.0:
            (color * (slconst_b - 95.0) / slconst_a + 95.0) / 1023.0;
}

struct _VLogConstants {
    float b;
    float c;
    float d;
    float cut1;
    float cut2;
};
// ref[9]
_VLogConstants VLogConstants(){
    _VLogConstants output;
    output.b = 0.00873;
    output.c = 0.241514;
    output.d = 0.598206;
    output.cut1 = 0.01;
    output.cut2 = 0.181;
    return output;
}
float3 cctf_decoding_VLog(float3 color){
     _VLogConstants vlconst = VLogConstants();
     return color < vlconst.cut2 ?
           (color - 0.125) / 5.6:
           pow(10.0, (color - vlconst.d) / vlconst.c) - vlconst.b;
}
float3 cctf_encoding_VLog(float3 color){
     _VLogConstants vlconst = VLogConstants();
     return color < vlconst.cut1 ?
           5.6 * color + 0.125:
           vlconst.c * log10(color + vlconst.b) + vlconst.d;
}
