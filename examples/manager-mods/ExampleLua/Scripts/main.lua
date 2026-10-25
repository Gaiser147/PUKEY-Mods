-- Synthetic template only. The manager reads this file as bytes; it never runs it.
-- UE4SS executes it after the user installs and enables the mod.
local greeting = "Hello from ExampleLua"
local visible = true
local ok, values = pcall(dofile, "ue4ss/Mods/ExampleLua/settings.lua")
if ok and type(values) == "table" then
    if type(values.Greeting) == "string" and #values.Greeting <= 4096
        and not values.Greeting:find("[\r\n]") then
        greeting = values.Greeting
    end
    if type(values.Visible) == "boolean" then visible = values.Visible end
end
if visible then print("[ExampleLua] " .. greeting .. "\n") end
