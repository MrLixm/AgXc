// code generated by automatic build; do not manually edit
/* --------------------------------------------------------------------------------
Matrices
-------------------------------------------------------------------------------- */

// sRGB
#define matrix_sRGB_to_XYZ float3x3(\
    0.4124, 0.3576, 0.1805,\
    0.2126, 0.7152, 0.0722,\
    0.0193, 0.1192, 0.9505\
)
#define matrix_sRGB_from_XYZ float3x3(\
    3.2406, -1.5372, -0.4986,\
    -0.9689, 1.8758, 0.0415,\
    0.0557, -0.204, 1.057\
)

// DCI-P3
#define matrix_DCIP3_to_XYZ float3x3(\
    0.445169816, 0.277134409, 0.17228267,\
    0.209491678, 0.721595254, 0.068913068,\
    -0.0, 0.04706056, 0.907355394\
)
#define matrix_DCIP3_from_XYZ float3x3(\
    2.72539403, -1.018003006, -0.440163195,\
    -0.795168026, 1.689732055, 0.022647191,\
    0.041241891, -0.087639019, 1.100929379\
)

// Display P3
#define matrix_Display_P3_to_XYZ float3x3(\
    0.486570949, 0.265667693, 0.198217285,\
    0.228974564, 0.691738522, 0.079286914,\
    -0.0, 0.045113382, 1.043944369\
)
#define matrix_Display_P3_from_XYZ float3x3(\
    2.493496912, -0.931383618, -0.402710784,\
    -0.82948897, 1.76266406, 0.023624686,\
    0.03584583, -0.076172389, 0.956884524\
)

// Adobe RGB (1998)
#define matrix_Adobe_RGB_1998_to_XYZ float3x3(\
    0.57667, 0.18556, 0.18823,\
    0.29734, 0.62736, 0.07529,\
    0.02703, 0.07069, 0.99134\
)
#define matrix_Adobe_RGB_1998_from_XYZ float3x3(\
    2.04159, -0.56501, -0.34473,\
    -0.96924, 1.87597, 0.04156,\
    0.01344, -0.11836, 1.01517\
)

// ITU-R BT.2020
#define matrix_ITUR_BT_2020_to_XYZ float3x3(\
    0.636958048, 0.144616904, 0.168880975,\
    0.262700212, 0.677998072, 0.059301716,\
    0.0, 0.028072693, 1.060985058\
)
#define matrix_ITUR_BT_2020_from_XYZ float3x3(\
    1.716651188, -0.355670784, -0.253366281,\
    -0.666684352, 1.616481237, 0.015768546,\
    0.017639857, -0.042770613, 0.942103121\
)


uniform int gamutid_sRGB = 0;
uniform int gamutid_DCIP3 = 1;
uniform int gamutid_Display_P3 = 2;
uniform int gamutid_Adobe_RGB_1998 = 3;
uniform int gamutid_ITUR_BT_2020 = 4;


float3x3 get_gamut_matrix_to_XYZ(int gamutid){
    if (gamutid == gamutid_sRGB             ) return matrix_sRGB_to_XYZ;
    if (gamutid == gamutid_DCIP3            ) return matrix_DCIP3_to_XYZ;
    if (gamutid == gamutid_Display_P3       ) return matrix_Display_P3_to_XYZ;
    if (gamutid == gamutid_Adobe_RGB_1998   ) return matrix_Adobe_RGB_1998_to_XYZ;
    if (gamutid == gamutid_ITUR_BT_2020     ) return matrix_ITUR_BT_2020_to_XYZ;
    return matrix_identity_3x3;
}

float3x3 get_gamut_matrix_from_XYZ(int gamutid){
    if (gamutid == gamutid_sRGB             ) return matrix_sRGB_from_XYZ;
    if (gamutid == gamutid_DCIP3            ) return matrix_DCIP3_from_XYZ;
    if (gamutid == gamutid_Display_P3       ) return matrix_Display_P3_from_XYZ;
    if (gamutid == gamutid_Adobe_RGB_1998   ) return matrix_Adobe_RGB_1998_from_XYZ;
    if (gamutid == gamutid_ITUR_BT_2020     ) return matrix_ITUR_BT_2020_from_XYZ;
    return matrix_identity_3x3;
}