--[[
Boilerplate code to create the user interface for your lua script.
]]

local _M_ = {}

--- BaseClass representing a parameter editable by the user
--- @class UserParam
_M_.UserParam = {}
--- @param name string must be the same as in the HLSL shader
--- @param defaultValueFunction function one from obs.obs_properties_set_defaultXXXX
--- @param defaultValueFunctionArgs table|nil numerical table of any type, order preserved when passed to function
--- @param propertyFunction function one from obs.properties_addXXXX
--- @param propertyFunctionArgs table|nil numerical table of any type, order preserved when passed to function
function _M_.UserParam:new(
    name,
    defaultValue,
    defaultValueFunction,
    defaultValueFunctionArgs,
    propertyFunction,
    propertyFunctionArgs
)
  local attrs = {
    ["name"] = name,
    ["defaultValue"] = defaultValue,
    ["defaultValueFunction"] = defaultValueFunction,
    ["defaultValueFunctionArgs"] = defaultValueFunctionArgs,
    ["propertyFunction"] = propertyFunction,
    ["propertyFunctionArgs"] = propertyFunctionArgs,
  }
  return attrs
end

--- Base class representing a parameter editable by the user
--- @class BaseProperty
_M_.BaseProperty = {}
--- @param name string must be the same as in the HLSL shader
function _M_.BaseProperty:new(
    name
)
  local attrs = {
    ["name"] = name,
    ["adder"] = false,
    ["defaultSetter"] = false,
    ["getter"] = false,
    ["shaderParam"] = false,
  }

  function attrs:updateShaderParam()
    if not self.shaderParam then
      return
    end

    obs.gs_effect_set_XXX(self.shaderParam)

  end


  return attrs

end

--- Regroup a list of UserParam instance to pass them more easily to the OBS API
--- @class UserParameters
_M_.UserParameters = {}
function _M_.UserParameters:new()

  local attrs = {
    ["params"] = {}
  }

  --- store a new UserParam insternall to apply later
  --- @param userParam UserParam
  function attrs:addUserParam(userParam)
    self.params[#self.params + 1] = userParam
  end

  --- to call in source_info.create
  --- @param dataTable table
  --- @param effect table comming from obs.gs_effect_create_from_file
  function attrs:createParamsOnData(dataTable, effect)
    for _, userParam in pairs(self.params) do
      dataTable[userParam.name] = obs.gs_effect_get_param_by_name(
          effect, userParam.name
      )
    end
  end

  --- to call in source_info.get_defaults
  --- @param settings table
  function attrs:applyDefaultToSettings(settings)
    for _, userParam in pairs(self.params) do
      if userParam.defaultValueFunctionArgs then
        userParam.defaultValueFunction(
            settings,
            userParam.name,
            userParam.defaultValue,
            unpack(userParam.defaultValueFunctionArgs)
        )
      else
        userParam.defaultValueFunction(
            settings,
            userParam.name,
            userParam.defaultValue
        )
      end
    end
  end

  --- to call in source_info.get_properties
  --- @param propertyGroup table
  function attrs:addProperty(propertyGroup)
    for _, userParam in pairs(self.params) do
      if userParam.propertyFunctionArgs then
        userParam.defaultValueFunction(
            settings,
            userParam.name,
            userParam.propertyFunction,
            unpack(userParam.propertyFunctionArgs)
        )
      else
        userParam.defaultValueFunction(
            settings,
            userParam.name,
            userParam.propertyFunction
        )
      end
    end
  end

  return attrs
end

return _M_