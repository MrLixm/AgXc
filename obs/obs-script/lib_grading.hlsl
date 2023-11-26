/*
References
----------

- [1] https://github.com/ampas/aces-dev/blob/master/transforms/ctl/lib/ACESlib.Utilities_Color.ctl#L492

*/
// require "lib_math.hlsl"
// require "lib_colorscience.hlsl"

float3 grade_saturation(float3 color, float saturationAmount, int colorspace_id){
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

float3 grade_gamma(float3 color, float amount){
  /*
      Change color gamma as color**amount
  */
  return powsafe(color, amount);
}

float3 grade_exposure(float3 color, float amount){
  /*
      Change color exposure up or down by the given amount.
  */
  return color * powsafe(2.0, amount);
}