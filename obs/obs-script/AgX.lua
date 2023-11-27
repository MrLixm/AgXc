--[[
Lua layer to read the HLSL AgX shader in OBS.

author = "Liam Collod"
repository = "https://github.com/MrLixm/AgXc"

Credits to the awesome https://obsproject.com/wiki/Scripting-Tutorial-Halftone-Filter
tutorial for learning the basics.
]]
obs = obslua

local __version__ = "1.3.0"

-- dependencies :
local hlsl_shader_file_path = script_path() .. 'AgX.hlsl'
local agx_lut_file_path = script_path() .. 'AgX-default_contrast.lut.png'

function script_description()
  return ([[
  <p>
  AgX is a display rendering transform to improve imagery rendering.
  </p>
  <p>
  Visit <a href=https://github.com/MrLixm/AgXc >https://github.com/MrLixm/AgXc</a>
  for more information.
  </p>
  <p>version <code>%s</code></p>
  ]]):format(__version__)
end

--- Load a pixel data file from disk and return it.
function load_texture(path)

  if string.len(path) < 0 then
    obs.blog(obs.LOG_ERROR, "Cannot load texture: no path given.")
    return
  end

  obs.obs_enter_graphics()

  local new_texture = obs.gs_image_file()
  obs.gs_image_file_init(new_texture, path)
  if new_texture.loaded then
    obs.gs_image_file_init_texture(new_texture)
  else
    obs.blog(obs.LOG_ERROR, "Cannot load texture " .. path)
    new_texture = nil
  end

  obs.obs_leave_graphics()
  return new_texture

end

--- store a texture2d object to be used in the HLSL shader
local AgXLUT


source_info = {}
source_info.id = 'filter-agx'  -- Unique string identifier of the source type
source_info.type = obs.OBS_SOURCE_TYPE_FILTER  -- INPUT or FILTER or TRANSITION
source_info.output_flags = obs.OBS_SOURCE_VIDEO  -- Combination of VIDEO/AUDIO/ASYNC/etc
--- Returns the name displayed in the list of filters
source_info.get_name = function()
  return "AgX"
end
--- Returns the width of the source
source_info.get_width = function(data)
  return data.width
end
--- Returns the height of the source
source_info.get_height = function(data)
  return data.height
end

source_info.get_defaults = function(settings)
  obs.obs_data_set_default_int(settings, "INPUT_COLORSPACE", 1)
  obs.obs_data_set_default_int(settings, "DRT", 1)
  obs.obs_data_set_default_double(settings, "INPUT_EXPOSURE", 0.5)
  obs.obs_data_set_default_double(settings, "INPUT_GAMMA", 1.0)
  obs.obs_data_set_default_double(settings, "INPUT_SATURATION", 1.0)
  obs.obs_data_set_default_double(settings, "INPUT_HIGHLIGHT_GAIN", 1.5)
  obs.obs_data_set_default_double(settings, "INPUT_HIGHLIGHT_GAIN_GAMMA", 1.0)
  obs.obs_data_set_default_double(settings, "INPUT_WHITE_BALANCE_TEMPERATURE", 5600)
  obs.obs_data_set_default_double(settings, "INPUT_WHITE_BALANCE_TINT", -15.5)
  obs.obs_data_set_default_double(settings, "INPUT_WHITE_BALANCE_INTENSITY", 0.0)
  obs.obs_data_set_default_double(settings, "PUNCH_EXPOSURE", 0.0)
  obs.obs_data_set_default_double(settings, "PUNCH_SATURATION", 1.0)
  obs.obs_data_set_default_double(settings, "PUNCH_GAMMA", 1.0)
  obs.obs_data_set_default_double(settings, "PUNCH_WHITE_BALANCE_TEMPERATURE", 5600)
  obs.obs_data_set_default_double(settings, "PUNCH_WHITE_BALANCE_TINT", -15.5)
  obs.obs_data_set_default_double(settings, "PUNCH_WHITE_BALANCE_INTENSITY", 0.0)
  obs.obs_data_set_default_int(settings, "OUTPUT_COLORSPACE", 1)
  obs.obs_data_set_default_int(settings, "CAT_METHOD", 1)
end
source_info.update = function(data, settings)
  data.INPUT_COLORSPACE = obs.obs_data_get_int(settings, "INPUT_COLORSPACE")
  data.DRT = obs.obs_data_get_int(settings, "DRT")
  data.INPUT_EXPOSURE = obs.obs_data_get_double(settings, "INPUT_EXPOSURE")
  data.INPUT_GAMMA = obs.obs_data_get_double(settings, "INPUT_GAMMA")
  data.INPUT_SATURATION = obs.obs_data_get_double(settings, "INPUT_SATURATION")
  data.INPUT_HIGHLIGHT_GAIN = obs.obs_data_get_double(settings, "INPUT_HIGHLIGHT_GAIN")
  data.INPUT_HIGHLIGHT_GAIN_GAMMA = obs.obs_data_get_double(settings, "INPUT_HIGHLIGHT_GAIN_GAMMA")
  data.INPUT_WHITE_BALANCE_TEMPERATURE = obs.obs_data_get_double(settings, "INPUT_WHITE_BALANCE_TEMPERATURE")
  data.INPUT_WHITE_BALANCE_TINT = obs.obs_data_get_double(settings, "INPUT_WHITE_BALANCE_TINT")
  data.INPUT_WHITE_BALANCE_INTENSITY = obs.obs_data_get_double(settings, "INPUT_WHITE_BALANCE_INTENSITY")
  data.PUNCH_EXPOSURE = obs.obs_data_get_double(settings, "PUNCH_EXPOSURE")
  data.PUNCH_SATURATION = obs.obs_data_get_double(settings, "PUNCH_SATURATION")
  data.PUNCH_GAMMA = obs.obs_data_get_double(settings, "PUNCH_GAMMA")
  data.PUNCH_WHITE_BALANCE_TEMPERATURE = obs.obs_data_get_double(settings, "PUNCH_WHITE_BALANCE_TEMPERATURE")
  data.PUNCH_WHITE_BALANCE_TINT = obs.obs_data_get_double(settings, "PUNCH_WHITE_BALANCE_TINT")
  data.PUNCH_WHITE_BALANCE_INTENSITY = obs.obs_data_get_double(settings, "PUNCH_WHITE_BALANCE_INTENSITY")
  data.OUTPUT_COLORSPACE = obs.obs_data_get_int(settings, "OUTPUT_COLORSPACE")
  data.CAT_METHOD = obs.obs_data_get_int(settings, "CAT_METHOD")
end
source_info.get_properties = function(data)
  local masterProperty = obs.obs_properties_create()

  local groupGrading = obs.obs_properties_create()
  local groupPunchy = obs.obs_properties_create()
  local groupDebug = obs.obs_properties_create()
  local groupInputWhiteBalance = obs.obs_properties_create()
  local groupPostWhiteBalance = obs.obs_properties_create()

  local propInputColorspace = obs.obs_properties_add_list(masterProperty, "INPUT_COLORSPACE", "Input Colorspace", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT) -- In which colorspace is encoded the input.
  obs.obs_property_list_add_int(propInputColorspace, "Passthrough", 0)
  obs.obs_property_list_add_int(propInputColorspace, "sRGB Display (EOTF)", 1)
  obs.obs_property_list_add_int(propInputColorspace, "sRGB Display (2.2)", 2)
  obs.obs_property_list_add_int(propInputColorspace, "sRGB Linear", 3)
  obs.obs_property_list_add_int(propInputColorspace, "BT.709 Display (2.4)", 4)
  obs.obs_property_list_add_int(propInputColorspace, "DCI-P3 Display (2.6)", 5)
  obs.obs_property_list_add_int(propInputColorspace, "DCI-P3 D65 Display (2.6)", 6)
  obs.obs_property_list_add_int(propInputColorspace, "DCI-P3 D60 Display (2.6)", 7)
  obs.obs_property_list_add_int(propInputColorspace, "Apple Display P3", 8)
  obs.obs_property_list_add_int(propInputColorspace, "Adobe RGB 1998 Display", 9)
  obs.obs_property_list_add_int(propInputColorspace, "BT.2020 Display (OETF)", 10)
  obs.obs_property_list_add_int(propInputColorspace, "BT.2020 Linear", 11)
  obs.obs_property_list_add_int(propInputColorspace, "DCI-P3 Linear", 12)
  obs.obs_property_list_add_int(propInputColorspace, "Cinema Gamut (Canon)", 13)
  obs.obs_property_list_add_int(propInputColorspace, "F-Gamut FLog (Fujifilm)", 14)
  obs.obs_property_list_add_int(propInputColorspace, "F-Gamut FLog2 (Fujifilm)", 15)
  obs.obs_property_list_add_int(propInputColorspace, "N-Gamut (Nikon)", 16)
  obs.obs_property_list_add_int(propInputColorspace, "S-Gamut (Sony)", 17)
  obs.obs_property_list_add_int(propInputColorspace, "S-Gamut2 (Sony)", 18)
  obs.obs_property_list_add_int(propInputColorspace, "S-Gamut3 (Sony)", 19)
  obs.obs_property_list_add_int(propInputColorspace, "S-Gamut3.Cine (Sony)", 20)
  obs.obs_property_list_add_int(propInputColorspace, "V-Gamut (Panasonic)", 21)

  local propOutputColorspace = obs.obs_properties_add_list(masterProperty, "OUTPUT_COLORSPACE", "Output Colorspace", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT) -- In which colorspace is encoded the input.
  obs.obs_property_list_add_int(propOutputColorspace, "Passthrough", 0)
  obs.obs_property_list_add_int(propOutputColorspace, "sRGB Display (EOTF)", 1)
  obs.obs_property_list_add_int(propOutputColorspace, "sRGB Display (2.2)", 2)
  obs.obs_property_list_add_int(propOutputColorspace, "sRGB Linear", 3)
  obs.obs_property_list_add_int(propOutputColorspace, "BT.709 Display (2.4)", 4)
  obs.obs_property_list_add_int(propOutputColorspace, "DCI-P3 Display (2.6)", 5)
  obs.obs_property_list_add_int(propOutputColorspace, "DCI-P3 D65 Display (2.6)", 6)
  obs.obs_property_list_add_int(propOutputColorspace, "DCI-P3 D60 Display (2.6)", 7)
  obs.obs_property_list_add_int(propOutputColorspace, "Apple Display P3", 8)
  obs.obs_property_list_add_int(propOutputColorspace, "Adobe RGB 1998 Display", 9)
  obs.obs_property_list_add_int(propOutputColorspace, "BT.2020 Display (OETF)", 10)
  obs.obs_property_list_add_int(propOutputColorspace, "BT.2020 Linear", 11)
  obs.obs_property_list_add_int(propOutputColorspace, "DCI-P3 Linear", 12)
  obs.obs_property_list_add_int(propOutputColorspace, "Cinema Gamut (Canon)", 13)
  obs.obs_property_list_add_int(propOutputColorspace, "F-Gamut FLog (Fujifilm)", 14)
  obs.obs_property_list_add_int(propOutputColorspace, "F-Gamut FLog2 (Fujifilm)", 15)
  obs.obs_property_list_add_int(propOutputColorspace, "N-Gamut (Nikon)", 16)
  obs.obs_property_list_add_int(propOutputColorspace, "S-Gamut (Sony)", 17)
  obs.obs_property_list_add_int(propOutputColorspace, "S-Gamut2 (Sony)", 18)
  obs.obs_property_list_add_int(propOutputColorspace, "S-Gamut3 (Sony)", 19)
  obs.obs_property_list_add_int(propOutputColorspace, "S-Gamut3.Cine (Sony)", 20)
  obs.obs_property_list_add_int(propOutputColorspace, "V-Gamut (Panasonic)", 21)

  local propDrt = obs.obs_properties_add_list(masterProperty, "DRT", "DRT", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
  obs.obs_property_list_add_int(propDrt, "None", 0)
  obs.obs_property_list_add_int(propDrt, "AgX", 1)
  obs.obs_property_list_add_int(propDrt, "AgX w/Outset", 2)

  obs.obs_properties_add_group(masterProperty, "GRADING", "Pre-Grading (Linear)", obs.OBS_GROUP_NORMAL, groupGrading)
  obs.obs_properties_add_group(masterProperty, "PUNCHY", "Post-Grading (Display)", obs.OBS_GROUP_NORMAL, groupPunchy)
  obs.obs_properties_add_group(masterProperty, "DEBUG", "Debug", obs.OBS_GROUP_NORMAL, groupDebug)

  obs.obs_properties_add_float_slider(groupGrading, "INPUT_EXPOSURE", "Exposure", -5, 5.0, 0.01)
  obs.obs_properties_add_float_slider(groupGrading, "INPUT_GAMMA", "Gamma", 0.001, 5.0, 0.01)
  obs.obs_properties_add_float_slider(groupGrading, "INPUT_SATURATION", "Saturation", 0.0, 5.0, 0.01)
  obs.obs_properties_add_float_slider(groupGrading, "INPUT_HIGHLIGHT_GAIN", "Highlight Gain", 0.0, 5.0, 0.01)
  obs.obs_properties_add_float_slider(groupGrading, "INPUT_HIGHLIGHT_GAIN_GAMMA", "Highlight Gain Threshold", 0.0, 4.0, 0.01)
  obs.obs_properties_add_group(groupGrading, "GRP_WHITE_BALANCE", "White Balance", obs.OBS_GROUP_NORMAL, groupInputWhiteBalance)
  obs.obs_properties_add_float_slider(groupInputWhiteBalance, "INPUT_WHITE_BALANCE_TEMPERATURE", "Temperature", 1000.0, 15000.0, 10.0)
  obs.obs_properties_add_float_slider(groupInputWhiteBalance, "INPUT_WHITE_BALANCE_TINT", "Tint", -150.0, 150.0, 2.0)
  obs.obs_properties_add_float_slider(groupInputWhiteBalance, "INPUT_WHITE_BALANCE_INTENSITY", "Intensity", 0.0, 5.0, 0.1)
  obs.obs_properties_add_text(groupPunchy, "PUNCH_INFO", "Not recommended for use. Tweak values softly.", obs.OBS_TEXT_INFO )
  obs.obs_properties_add_float_slider(groupPunchy, "PUNCH_EXPOSURE", "Exposure", -3.0, 3.0, 0.01)
  obs.obs_properties_add_float_slider(groupPunchy, "PUNCH_SATURATION", "Saturation", 0.0, 2.0, 0.01)
  obs.obs_properties_add_float_slider(groupPunchy, "PUNCH_GAMMA", "Gamma", 0.001, 2.0, 0.01)
  obs.obs_properties_add_group(groupPunchy, "GRP_POST_WHITE_BALANCE", "White Balance", obs.OBS_GROUP_NORMAL, groupPostWhiteBalance)
  obs.obs_properties_add_float_slider(groupPostWhiteBalance, "PUNCH_WHITE_BALANCE_TEMPERATURE", "Temperature", 1000.0, 15000.0, 10.0)
  obs.obs_properties_add_float_slider(groupPostWhiteBalance, "PUNCH_WHITE_BALANCE_TINT", "Tint", -150.0, 150.0, 2.0)
  obs.obs_properties_add_float_slider(groupPostWhiteBalance, "PUNCH_WHITE_BALANCE_INTENSITY", "Intensity", 0.0, 5.0, 0.1)
  local propCatMethod = obs.obs_properties_add_list(groupDebug, "CAT_METHOD", "CAT Method", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
  obs.obs_property_list_add_int(propCatMethod, "XYZ Scaling", 0)
  obs.obs_property_list_add_int(propCatMethod, "Bradford", 1)
  obs.obs_property_list_add_int(propCatMethod, "CAT02", 2)
  obs.obs_property_list_add_int(propCatMethod, "Von Kries", 3)

  return masterProperty
end
--- Creates the implementation data for the source
source_info.create = function(settings, source)

  local data = {}
  data.source = source  -- Keeps a reference to this filter as a source object
  data.width = 1  -- Dummy value during initialization phase
  data.height = 1  -- Dummy value during initialization phase

  AgXLUT = load_texture(agx_lut_file_path)

  -- Compile HLSL shader
  obs.obs_enter_graphics()
  local error = ""
  data.effect = obs.gs_effect_create_from_file(hlsl_shader_file_path, nil)
  obs.blog(obs.LOG_INFO, "[source_info.create] Loaded effect " .. hlsl_shader_file_path)
  obs.obs_leave_graphics()

  if data.effect == nil then
    obs.blog(obs.LOG_ERROR, "Effect compilation failed for " .. hlsl_shader_file_path .. "\n" .. error)
    source_info.destroy(data)
    error = nil
    return nil
  end

  -- Access HLSL variables
  data.params = {}

  data.params.AgXLUT = obs.gs_effect_get_param_by_name(data.effect, "AgXLUT")
  data.params.INPUT_COLORSPACE = obs.gs_effect_get_param_by_name(data.effect, "INPUT_COLORSPACE")
  data.params.OUTPUT_COLORSPACE = obs.gs_effect_get_param_by_name(data.effect, "OUTPUT_COLORSPACE")
  data.params.DRT = obs.gs_effect_get_param_by_name(data.effect, "DRT")
  data.params.INPUT_EXPOSURE = obs.gs_effect_get_param_by_name(data.effect, "INPUT_EXPOSURE")
  data.params.INPUT_GAMMA = obs.gs_effect_get_param_by_name(data.effect, "INPUT_GAMMA")
  data.params.INPUT_SATURATION = obs.gs_effect_get_param_by_name(data.effect, "INPUT_SATURATION")
  data.params.INPUT_HIGHLIGHT_GAIN = obs.gs_effect_get_param_by_name(data.effect, "INPUT_HIGHLIGHT_GAIN")
  data.params.INPUT_HIGHLIGHT_GAIN_GAMMA = obs.gs_effect_get_param_by_name(data.effect, "INPUT_HIGHLIGHT_GAIN_GAMMA")
  data.params.INPUT_WHITE_BALANCE_TEMPERATURE = obs.gs_effect_get_param_by_name(data.effect, "INPUT_WHITE_BALANCE_TEMPERATURE")
  data.params.INPUT_WHITE_BALANCE_TINT = obs.gs_effect_get_param_by_name(data.effect, "INPUT_WHITE_BALANCE_TINT")
  data.params.INPUT_WHITE_BALANCE_INTENSITY = obs.gs_effect_get_param_by_name(data.effect, "INPUT_WHITE_BALANCE_INTENSITY")
  data.params.PUNCH_EXPOSURE = obs.gs_effect_get_param_by_name(data.effect, "PUNCH_EXPOSURE")
  data.params.PUNCH_SATURATION = obs.gs_effect_get_param_by_name(data.effect, "PUNCH_SATURATION")
  data.params.PUNCH_GAMMA = obs.gs_effect_get_param_by_name(data.effect, "PUNCH_GAMMA")
  data.params.PUNCH_WHITE_BALANCE_TEMPERATURE = obs.gs_effect_get_param_by_name(data.effect, "PUNCH_WHITE_BALANCE_TEMPERATURE")
  data.params.PUNCH_WHITE_BALANCE_TINT = obs.gs_effect_get_param_by_name(data.effect, "PUNCH_WHITE_BALANCE_TINT")
  data.params.PUNCH_WHITE_BALANCE_INTENSITY = obs.gs_effect_get_param_by_name(data.effect, "PUNCH_WHITE_BALANCE_INTENSITY")
  data.params.CAT_METHOD = obs.gs_effect_get_param_by_name(data.effect, "CAT_METHOD")

  source_info.update(data, settings)

  return data
end
--- Destroys and release resources linked to the custom data
source_info.destroy = function(data)
  if data.effect == nil then
    return
  end
  obs.obs_enter_graphics()
  obs.gs_effect_destroy(data.effect)
  data.effect = nil
  obs.obs_leave_graphics()
end
--- Called when rendering the source with the graphics subsystem
source_info.video_render = function(data)
  local parent = obs.obs_filter_get_parent(data.source)
  data.width = obs.obs_source_get_base_width(parent)
  data.height = obs.obs_source_get_base_height(parent)

  obs.obs_source_process_filter_begin(data.source, obs.GS_RGBA, obs.OBS_NO_DIRECT_RENDERING)

  if AgXLUT then
    obs.gs_effect_set_texture(data.params.AgXLUT, AgXLUT.texture)
  end

  obs.gs_effect_set_int(data.params.INPUT_COLORSPACE, data.INPUT_COLORSPACE)
  obs.gs_effect_set_int(data.params.DRT, data.DRT)
  obs.gs_effect_set_float(data.params.INPUT_EXPOSURE, data.INPUT_EXPOSURE)
  obs.gs_effect_set_float(data.params.INPUT_GAMMA, data.INPUT_GAMMA)
  obs.gs_effect_set_float(data.params.INPUT_SATURATION, data.INPUT_SATURATION)
  obs.gs_effect_set_float(data.params.INPUT_HIGHLIGHT_GAIN, data.INPUT_HIGHLIGHT_GAIN)
  obs.gs_effect_set_float(data.params.INPUT_HIGHLIGHT_GAIN_GAMMA, data.INPUT_HIGHLIGHT_GAIN_GAMMA)
  obs.gs_effect_set_float(data.params.INPUT_WHITE_BALANCE_TEMPERATURE, data.INPUT_WHITE_BALANCE_TEMPERATURE)
  obs.gs_effect_set_float(data.params.INPUT_WHITE_BALANCE_TINT, data.INPUT_WHITE_BALANCE_TINT)
  obs.gs_effect_set_float(data.params.INPUT_WHITE_BALANCE_INTENSITY, data.INPUT_WHITE_BALANCE_INTENSITY)
  obs.gs_effect_set_float(data.params.PUNCH_EXPOSURE, data.PUNCH_EXPOSURE)
  obs.gs_effect_set_float(data.params.PUNCH_SATURATION, data.PUNCH_SATURATION)
  obs.gs_effect_set_float(data.params.PUNCH_GAMMA, data.PUNCH_GAMMA)
  obs.gs_effect_set_float(data.params.PUNCH_WHITE_BALANCE_TEMPERATURE, data.PUNCH_WHITE_BALANCE_TEMPERATURE)
  obs.gs_effect_set_float(data.params.PUNCH_WHITE_BALANCE_TINT, data.PUNCH_WHITE_BALANCE_TINT)
  obs.gs_effect_set_float(data.params.PUNCH_WHITE_BALANCE_INTENSITY, data.PUNCH_WHITE_BALANCE_INTENSITY)
  obs.gs_effect_set_int(data.params.OUTPUT_COLORSPACE, data.OUTPUT_COLORSPACE)
  obs.gs_effect_set_int(data.params.CAT_METHOD, data.CAT_METHOD)

  obs.obs_source_process_filter_end(data.source, data.effect, data.width, data.height)
end

--- Called on script startup
function script_load(settings)
  obs.obs_register_source(source_info)
end
