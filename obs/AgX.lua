obs = obslua

local __version__ = "0.1.1"

-- dependencies :
local hlsl_shader_file_path = script_path() .. 'AgX.hlsl'


function script_description()
  return ([[
  <p>
  AgX is a display rendering transform to improve image formation.
  </p>
  <p>
  Visit <a href=https://github.com/MrLixm/AgXc >https://github.com/MrLixm/AgXc</a>
  for more information.
  </p>
  <p>version <code>%s</code></p>
  ]]):format(__version__)
end

-- Definition of the global variable containing the source_info structure
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
  obs.obs_data_set_default_double(settings, "INPUT_EXPOSURE", 0.0)
  obs.obs_data_set_default_double(settings, "INPUT_GAMMA", 1.0)
  obs.obs_data_set_default_double(settings, "INPUT_SATURATION", 1.0)
  obs.obs_data_set_default_double(settings, "INPUT_HIGHLIGHT_GAIN", 0.0)
  obs.obs_data_set_default_double(settings, "INPUT_HIGHLIGHT_GAIN_GAMMA", 1.0)
  obs.obs_data_set_default_double(settings, "PUNCH_EXPOSURE", 0.0)
  obs.obs_data_set_default_double(settings, "PUNCH_SATURATION", 1.0)
  obs.obs_data_set_default_double(settings, "PUNCH_GAMMA", 1.0)
  obs.obs_data_set_default_bool(settings, "USE_OCIO_LOG", false)
  obs.obs_data_set_default_bool(settings, "APPLY_OUTSET", true)
end
source_info.update = function(data, settings)
  data.INPUT_COLORSPACE = obs.obs_data_get_int(settings, "INPUT_COLORSPACE")
  data.INPUT_EXPOSURE = obs.obs_data_get_double(settings, "INPUT_EXPOSURE")
  data.INPUT_GAMMA = obs.obs_data_get_double(settings, "INPUT_GAMMA")
  data.INPUT_SATURATION = obs.obs_data_get_double(settings, "INPUT_SATURATION")
  data.INPUT_HIGHLIGHT_GAIN = obs.obs_data_get_double(settings, "INPUT_HIGHLIGHT_GAIN")
  data.INPUT_HIGHLIGHT_GAIN_GAMMA = obs.obs_data_get_double(settings, "INPUT_HIGHLIGHT_GAIN_GAMMA")
  data.PUNCH_EXPOSURE = obs.obs_data_get_double(settings, "PUNCH_EXPOSURE")
  data.PUNCH_SATURATION = obs.obs_data_get_double(settings, "PUNCH_SATURATION")
  data.PUNCH_GAMMA = obs.obs_data_get_double(settings, "PUNCH_GAMMA")
  data.USE_OCIO_LOG = obs.obs_data_get_bool(settings, "USE_OCIO_LOG")
  data.APPLY_OUTSET = obs.obs_data_get_bool(settings, "APPLY_OUTSET")
end
source_info.get_properties = function(data)
  local masterProperty = obs.obs_properties_create()
  local propInputColorspace = obs.obs_properties_add_list(masterProperty, "INPUT_COLORSPACE", "Input Colorspace", obslua.OBS_COMBO_TYPE_LIST, obslua.OBS_COMBO_FORMAT_INT) -- In which colorspace is encoded the input.
  obs.obs_property_list_add_int(propInputColorspace, "Passthrough", 0)
  obs.obs_property_list_add_int(propInputColorspace, "sRGB Display (EOTF)", 1)
  obs.obs_property_list_add_int(propInputColorspace, "sRGB Display (2.2)", 2)
  obs.obs_properties_add_float_slider(masterProperty, "INPUT_EXPOSURE", "INPUT EXPOSURE", -5, 5.0, 0.01)
  obs.obs_properties_add_float_slider(masterProperty, "INPUT_GAMMA", "INPUT GAMMA", 0.001, 5.0, 0.01)
  obs.obs_properties_add_float_slider(masterProperty, "INPUT_SATURATION", "INPUT SATURATION", 0.0, 5.0, 0.01)
  obs.obs_properties_add_float_slider(masterProperty, "INPUT_HIGHLIGHT_GAIN", "INPUT HIGHLIGHT GAIN", 0.0, 5.0, 0.01)
  obs.obs_properties_add_float_slider(masterProperty, "INPUT_HIGHLIGHT_GAIN_GAMMA", "INPUT HIGHLIGHT GAIN GAMMA", 0.0, 4.0, 0.01)
  obs.obs_properties_add_float_slider(masterProperty, "PUNCH_EXPOSURE", "PUNCH EXPOSURE", -5.0, 5.0, 0.01)
  obs.obs_properties_add_float_slider(masterProperty, "PUNCH_SATURATION", "PUNCH SATURATION", 0.0, 3.0, 0.01)
  obs.obs_properties_add_float_slider(masterProperty, "PUNCH_GAMMA", "PUNCH GAMMA", 0.001, 2.0, 0.01)
  obs.obs_properties_add_bool(masterProperty, "USE_OCIO_LOG", "Use OCIO Log Transform") -- Use a transform similar to OCIO for the log operation. No difference should be observed.
  obs.obs_properties_add_bool(masterProperty, "APPLY_OUTSET", "Apply Outset") -- Apply the inverse of the inset matrix applied before the log transform. Restore chroma.
  return masterProperty
end
--- Creates the implementation data for the source
source_info.create = function(settings, source)

  local data = {}
  data.source = source  -- Keeps a reference to this filter as a source object
  data.width = 1  -- Dummy value during initialization phase
  data.height = 1  -- Dummy value during initialization phase

  -- Compile HLSL shader
  obs.obs_enter_graphics()
  data.effect = obs.gs_effect_create_from_file(hlsl_shader_file_path, nil)
  obs.blog(obs.LOG_INFO, "[source_info.create] Loaded effect "..hlsl_shader_file_path)
  obs.obs_leave_graphics()

  if data.effect == nil then
    obs.blog(obs.LOG_ERROR, "Effect compilation failed for " .. hlsl_shader_file_path)
    source_info.destroy(data)
    return nil
  end

  -- Access HLSL variables
  data.params = {}
  data.params.INPUT_COLORSPACE = obs.gs_effect_get_param_by_name(data.effect, "INPUT_COLORSPACE")
  data.params.INPUT_EXPOSURE = obs.gs_effect_get_param_by_name(data.effect, "INPUT_EXPOSURE")
  data.params.INPUT_GAMMA = obs.gs_effect_get_param_by_name(data.effect, "INPUT_GAMMA")
  data.params.INPUT_SATURATION = obs.gs_effect_get_param_by_name(data.effect, "INPUT_SATURATION")
  data.params.INPUT_HIGHLIGHT_GAIN = obs.gs_effect_get_param_by_name(data.effect, "INPUT_HIGHLIGHT_GAIN")
  data.params.INPUT_HIGHLIGHT_GAIN_GAMMA = obs.gs_effect_get_param_by_name(data.effect, "INPUT_HIGHLIGHT_GAIN_GAMMA")
  data.params.PUNCH_EXPOSURE = obs.gs_effect_get_param_by_name(data.effect, "PUNCH_EXPOSURE")
  data.params.PUNCH_SATURATION = obs.gs_effect_get_param_by_name(data.effect, "PUNCH_SATURATION")
  data.params.PUNCH_GAMMA = obs.gs_effect_get_param_by_name(data.effect, "PUNCH_GAMMA")
  data.params.USE_OCIO_LOG = obs.gs_effect_get_param_by_name(data.effect, "USE_OCIO_LOG")
  data.params.APPLY_OUTSET = obs.gs_effect_get_param_by_name(data.effect, "APPLY_OUTSET")

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

  obs.gs_effect_set_int(data.params.INPUT_COLORSPACE, data.INPUT_COLORSPACE)
  obs.gs_effect_set_float(data.params.INPUT_EXPOSURE, data.INPUT_EXPOSURE)
  obs.gs_effect_set_float(data.params.INPUT_GAMMA, data.INPUT_GAMMA)
  obs.gs_effect_set_float(data.params.INPUT_SATURATION, data.INPUT_SATURATION)
  obs.gs_effect_set_float(data.params.INPUT_HIGHLIGHT_GAIN, data.INPUT_HIGHLIGHT_GAIN)
  obs.gs_effect_set_float(data.params.INPUT_HIGHLIGHT_GAIN_GAMMA, data.INPUT_HIGHLIGHT_GAIN_GAMMA)
  obs.gs_effect_set_float(data.params.PUNCH_EXPOSURE, data.PUNCH_EXPOSURE)
  obs.gs_effect_set_float(data.params.PUNCH_SATURATION, data.PUNCH_SATURATION)
  obs.gs_effect_set_float(data.params.PUNCH_GAMMA, data.PUNCH_GAMMA)
  obs.gs_effect_set_bool(data.params.USE_OCIO_LOG, data.USE_OCIO_LOG)
  obs.gs_effect_set_bool(data.params.APPLY_OUTSET, data.APPLY_OUTSET)

  obs.obs_source_process_filter_end(data.source, data.effect, data.width, data.height)
end

--- Called on script startup
function script_load(settings)
  obs.obs_register_source(source_info)
end
