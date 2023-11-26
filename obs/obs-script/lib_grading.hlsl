/*
References
----------

- [1] https://github.com/ampas/aces-dev/blob/master/transforms/ctl/lib/ACESlib.Utilities_Color.ctl#L492

*/
// require "lib_math.hlsl"
// require "lib_colorscience.hlsl"

float3 saturation(float3 color, float saturationAmount, int colorspace_id){
  /*

      Increase color saturation of the given color data.

      :param color: colorspace-encoded imagery in any state
      :param saturationAmount: expected 0-1 range with 1=neutral, 0=no saturation.
      :param colorspace_id: id of the colorspace the color is encoded in

      -- ref[1]
  */
  float luma = get_luminance(color, colorspace_id);
  return lerp(luma, color, saturationAmount);
}