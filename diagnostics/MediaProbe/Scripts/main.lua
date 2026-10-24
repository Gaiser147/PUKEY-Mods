--[[
    MediaProbe – Diagnose: protokolliert alle 2 s, welche Datei jeder MediaPlayer abspielt.
    Läuft automatisch 300 s lang nach dem Laden (keine Taste nötig). Ausgabe im UE4SS.log.
]]
local last = {}
local ticks = 0

local function Probe()
    local players = FindAllOf("MediaPlayer") or {}
    for _, mp in ipairs(players) do
        if mp:IsValid() then
            local name = mp:GetFName():ToString()
            local url, playing = "?", "?"
            pcall(function() url = mp:GetUrl():ToString() end)
            pcall(function() playing = tostring(mp:IsPlaying()) end)
            local line = name .. " playing=" .. playing .. " url=" .. url
            if last[name] ~= line then
                print("[MediaProbe] " .. line .. "\n")
                last[name] = line
            end
        end
    end
end

LoopAsync(2000, function()
    ticks = ticks + 1
    if ticks > 150 then
        print("[MediaProbe] Ende\n")
        return true
    end
    ExecuteInGameThread(function() pcall(Probe) end)
    return false
end)

print("[MediaProbe] geladen\n")

-- Prüft über das Engine-Dateisystem (pak-fähig), ob Dateien aus Mod-Paketen sichtbar sind
local PathsToCheck = {
    "../../../PUKEY_GODDESS_SHOT_TRICK/Content/ModTest/hello.txt",
    "../../../PUKEY_GODDESS_SHOT_TRICK/Content/Bacchus/Movie/Event/T_PRERENDER_TITLE.mp4",
    "../../../PUKEY_GODDESS_SHOT_TRICK/Content/Bacchus/Movie/Logo/AllianceArts_logo_VI_short.mp4",
}
ExecuteWithDelay(8000, function()
    ExecuteInGameThread(function()
        local lib = StaticFindObject("/Script/Engine.Default__BlueprintPathsLibrary")
        if not (lib and lib:IsValid()) then print("[MediaProbe] BlueprintPathsLibrary fehlt\n") return end
        for _, p in ipairs(PathsToCheck) do
            local ok, r = pcall(function() return lib:FileExists(p) end)
            print("[MediaProbe] FileExists " .. p .. " -> " .. tostring(ok and r or ("FEHLER " .. tostring(r))) .. "\n")
        end
    end)
end)

-- Listet alle FileMediaSource-Objekte mit ihrem FilePath (alle 10 s, nur neue)
local seenSources = {}
local srcTicks = 0
LoopAsync(10000, function()
    srcTicks = srcTicks + 1
    if srcTicks > 30 then return true end
    ExecuteInGameThread(function()
        pcall(function()
            local list = FindAllOf("FileMediaSource") or {}
            local new = 0
            for _, s in ipairs(list) do
                if s:IsValid() then
                    local full = s:GetFullName()
                    if not seenSources[full] then
                        seenSources[full] = true
                        new = new + 1
                        local fp = "?"
                        pcall(function() fp = s.FilePath:ToString() end)
                        print("[MediaProbe] SRC " .. full .. " | FilePath=" .. fp .. "\n")
                    end
                end
            end
            if new > 0 then print("[MediaProbe] FileMediaSource gesamt: " .. #list .. "\n") end
        end)
    end)
    return false
end)
