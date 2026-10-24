--[[
    UsmapDump - writes Mappings.usmap (class/property layout) once, 20 s after the game starts.
    FModel/CUE4Parse needs this file to read this UE5 game's assets (unversioned properties).
    Output: ue4ss/Mappings.usmap (next to UE4SS.dll). Disable the mod (delete enabled.txt) afterwards.
]]
ExecuteWithDelay(20000, function()
    print("[UsmapDump] dumping mappings ...\n")
    local ok, err = pcall(DumpUSMAP)
    print("[UsmapDump] " .. (ok and "done" or ("error: " .. tostring(err))) .. "\n")
end)
print("[UsmapDump] loaded - dump in 20 s\n")
