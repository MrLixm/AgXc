/*
RGB Colorspace related objects


References
----------

All data without explicit reference can assumed to be extracted/generated from `colour-science` python library.

- [1] https://github.com/sobotka/AgX-S2O3/blob/main/AgX.py
- [2] https://github.com/colour-science/colour/blob/develop/colour/models/rgb/transfer_functions/srgb.py#L99
- [3] https://github.com/colour-science/colour/blob/develop/colour/models/rgb/transfer_functions/st_2084.py
- [4] https://github.com/ampas/aces-dev/blob/master/transforms/ctl/lib/ACESlib.Utilities_Color.ctl#L492
- [5] https://github.com/ampas/aces-dev/blob/master/transforms/ctl/lib/ACESlib.ODT_Common.ctl#L42
*/

uniform int CAT_METHOD = 0; // See Chromatic Adapatation transform section for availables ids

#include "colorscience/math.hlsl"
#include "colorscience/cctf.hlsl"
#include "colorscience/cctf-auto.hlsl"
#include "colorscience/cat.hlsl"
#include "colorscience/gamut.hlsl"
#include "colorscience/colorspace.hlsl"


float3 convertColorspaceToColorspace(float3 color, int sourceColorspaceId, int targetColorspaceId){

    if (sourceColorspaceId == colorspaceid_Passthrough)
        return color;
    if (targetColorspaceId == colorspaceid_Passthrough)
        return color;
    if (sourceColorspaceId == targetColorspaceId)
        return color;

    Colorspace source_colorspace = getColorspaceFromId(sourceColorspaceId);
    Colorspace target_colorspace = getColorspaceFromId(targetColorspaceId);

    color = apply_cctf_decoding(color, source_colorspace.cctf_id);

    // apply Chromatic adaptation transform if any
    if (source_colorspace.whitepoint_id != target_colorspace.whitepoint_id && (source_colorspace.whitepoint_id != -1) && (target_colorspace.whitepoint_id != -1)){
        color = apply_matrix(
            color,
            get_chromatic_adaptation_transform_matrix(
                CAT_METHOD,
                source_colorspace.whitepoint_id,
                target_colorspace.whitepoint_id
            )
         );
    }

    if (source_colorspace.gamut_id != target_colorspace.gamut_id && (source_colorspace.gamut_id != -1) && (target_colorspace.gamut_id != -1)){
        color = apply_matrix(color, get_gamut_matrix_to_XYZ(source_colorspace.gamut_id));
        color = apply_matrix(color, get_gamut_matrix_from_XYZ(target_colorspace.gamut_id));
    }
    color = apply_cctf_encoding(color, target_colorspace.cctf_id);

    return color;

};
