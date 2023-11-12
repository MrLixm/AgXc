/*
References
----------

- [1] https://github.com/ampas/aces-dev/blob/master/transforms/ctl/lib/ACESlib.Utilities_Color.ctl#L492
*/
#define matrix_identity_3x3 float3x3(\
    1.0, 0.0, 0.0,\
    0.0, 1.0, 0.0,\
    0.0, 0.0, 1.0\
)

#define luma_coefs_bt709 float3(0.2126, 0.7152, 0.0722)

float3 powsafe(float3 color, float power){
  // pow() but safe for NaNs/negatives
  return pow(abs(color), power) * sign(color);
}

float3 apply_matrix(float3 color, float3x3 inputMatrix){
  // seems you can't just use mul() with OBS, and we have to split per component like that :
  float r = dot(color, inputMatrix[0]);
	float g = dot(color, inputMatrix[1]);
	float b = dot(color, inputMatrix[2]);
  return float3(r, g, b);
}

float get_luminance(float3 image){
  // Return approximative perceptive luminance of the image.
  return dot(image, luma_coefs_bt709);
}

float3 saturation(float3 color, float saturationAmount){
  /*

      Increase color saturation of the given color data.

      :param color: expected sRGB primaries input
      :oaram saturationAmount: expected 0-1 range with 1=neutral, 0=no saturation.

      -- ref[1]
  */
  float luma = get_luminance(color);
  return lerp(luma, color, saturationAmount);
}
