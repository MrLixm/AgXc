/*
References :
- [2] Ohno, Yoshi (2014). Practical Use and Calculation of CCT and Duv. LEUKOS, 10(1), 47–55. doi:10.1080/15502724.2014.839020
- [3] https://en.wikipedia.org/wiki/Planckian_locus#Approximation
- [4] SMPTE Recommended Practice - Derivation of Basic Television Color Equations https://ieeexplore.ieee.org/document/7291155
*/
// require "lib_math.hlsl"

// initially recommended to 0.01 but was not stable on the whole CCT range
#define ohno_deltaT float(2.0)


float2 convert_CCT_to_uv_Krystek1985(float CCT){
    /*
        Convert the given CCT to CIE 1960 u,v colorspace values using Krystek's method.

        Krystek's method is an approximation and not intended for accuracy.

        :param CCT: in kelvin, ~[1000-15000] range
        --[3]
    */
    float CCT_2 = pow(CCT,2.0);
    float u = 0.860117757 + 1.54118254 * pow(10.0,-4.0) * CCT + 1.28641212 * pow(10.0,-7.0) * CCT_2;
    u = u / (1.0 + 8.42420235 * pow(10.0,-4.0) * CCT + 7.08145163 * pow(10.0,-7.0) * CCT_2);
    float v = 0.317398726 + 4.22806245 * pow(10.0,-5.0) * CCT + 4.20481691 * pow(10.0,-8.0) * CCT_2;
    v = v / (1.0 - 2.89741816 * pow(10.0,-5.0) * CCT + 1.61456053 * pow(10.0,-7.0) * CCT_2);
    return float2(u, v);
}

float2 convert_CCT_Duv_to_xy(float CCT, float Duv){
    /*
        :param CCT: correlated color temperature in kelvin, ~[1000-15000] range
        :param Duv: also called "tint" [-0.05-+0.05] range
        -- [2]
    */
    float2 uv0 = convert_CCT_to_uv_Krystek1985(CCT);
    float2 uv1 = convert_CCT_to_uv_Krystek1985(CCT + ohno_deltaT);

    float du = uv0.x - uv1.x;
    float dv = uv0.y - uv1.y;

    float hypothenus = sqrt(powsafe(du,2.0) + powsafe(dv,2.0));
    float sinTheta = dv / hypothenus;
    float cosTheta = du / hypothenus;

    float u = uv0.x - Duv * sinTheta;
    float v = uv0.y + Duv * cosTheta;

    float u_p = u;
    float v_p = 1.5 * v;

    float x = 9.0 * u_p / (6.0 * u_p - 16.0 * v_p + 12.0);
    float y = 2.0 * v_p / (3.0 * u_p - 8.0 * v_p + 6.0);
    return float2(x, y);
}

float3 white_balance(float3 color, float CCT, float tint){
    /*
        Change the white balance of the given color based on the given CCT and tint.

        This is a custom implementation that is probably not the correct way of
        doing white balance. Current issue include that there is no perfect
        set of value to achieve a "no-operation".

        :param color: not sure what is the expected state of the data
        :param CCT: correlated color temperature in kelvin, ~[1000-15000] range
        :param tint: green-magenta shift in [-150-+150] range
    */
    // 3000 is an arbitrary scale for the tint parameter to have a more UI friendly range.
    float2 new_white_xy = convert_CCT_Duv_to_xy(CCT, tint/3000.0);

    // --[4] normalise primary matrix but only with whitepoint
    float Wz = 1.0 - new_white_xy.x - new_white_xy.y;
    float3 W = float3(new_white_xy.x / new_white_xy.y, 1.0, Wz / new_white_xy.y);
    float3x3 whitepoint_matrix = {
        W.x, 0.0, 0.0,
        0.0, W.y, 0.0,
        0.0, 0.0, W.z
    };
    return apply_matrix(color, whitepoint_matrix);
}