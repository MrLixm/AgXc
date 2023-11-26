// require "colorspace.hlsl"
// require "coefficients.hlsl"

float get_luminance(float3 image, int colorspace_id){
  /*
      Return approximative perceptive luminance of the image with
      colorspace encoding awarness.

      :param image: colorspace-encoded imagery in any state
      :param colorspace_id: id of the colorspace the image is encoded in
  */
  float3 luma_coeff = getLumaCoefficientFromId(colorspace_id);
  return dot(image, luma_coeff);
}
