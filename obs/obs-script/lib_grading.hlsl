/*
References
----------

- [1] https://github.com/ampas/aces-dev/blob/master/transforms/ctl/lib/ACESlib.Utilities_Color.ctl#L492

*/
// require "lib_math.hlsl"
// require "lib_colorscience.hlsl"

float3 saturation(float3 color, float saturationAmount){
  /*

      Increase color saturation of the given color data.

      :param color: expected sRGB primaries input
      :param saturationAmount: expected 0-1 range with 1=neutral, 0=no saturation.

      -- ref[1]
  */
  float luma = get_luminance(color);
  return lerp(luma, color, saturationAmount);
}