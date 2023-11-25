// require "colorspace.hlsl"

// TODO more flexible system
#define luma_coefs_bt709 float3(0.2126, 0.7152, 0.0722)

float get_luminance(float3 image){
  // Return approximative perceptive luminance of the image with
  // colorspace encoding awarness.
  return dot(image, luma_coefs_bt709);
}
