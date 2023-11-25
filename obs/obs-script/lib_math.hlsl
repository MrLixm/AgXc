/*
lowest level module for math operations
*/

#define matrix_identity_3x3 float3x3(\
    1.0, 0.0, 0.0,\
    0.0, 1.0, 0.0,\
    0.0, 0.0, 1.0\
)

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
