--[[
    MovieSwap – ersetzt Spielvideos (Fam-Animationen, Titel, Events …) durch eigene MP4-Dateien.
    Kein Pak nötig: Die Mod biegt zur Laufzeit den FilePath der FileMediaSource-Objekte
    auf Ersatzdateien im Mod-Ordner um.

    Benutzung:
      Ersatzvideo unter demselben relativen Pfad ablegen wie im Spiel, z. B.
        ue4ss/Mods/MovieSwap/Movies/Bacchus/Movie/Fam/T_FAM_BOW_A.mp4
      ersetzt
        /Game/Bacchus/Movie/Fam/T_FAM_BOW_A.mp4
      Fehlt eine Datei, bleibt das Original.

    Anforderungen an Fam-Videos (wie die Originale):
      H.264 (avc1) in MP4, 2560x1440, 24 fps, Hintergrund reines Grün RGB(0,255,0)
      (das Spiel stanzt Grün aus), Figur oben mittig, möglichst gleiche Länge wie das Original.

    F11: Ersatzdateien neu einlesen (z. B. nach dem Hinzufügen neuer Videos).
]]

local ModRoot = "ue4ss/Mods/MovieSwap/Movies/"   -- relativ zu Binaries/Win64
local Config = { ScanIntervalMs = 2000, ReloadKey = Key.F11 }

-- The manager writes this optional table separately from the versioned mod files.
-- Keep this loader local so manually copied mods work without manager components.
do
    local Rules = {
        ScanIntervalMs = { Kind = "number", Min = 100, Max = 60000 },
        ReloadKey = { Kind = "key" },
    }
    local AllowedKeys = {
        HOME = true, END = true, PAGE_UP = true, PAGE_DOWN = true,
        INSERT = true, DELETE = true, SPACE = true, ZERO = true,
        ONE = true, TWO = true, THREE = true, FOUR = true, FIVE = true,
        SIX = true, SEVEN = true, EIGHT = true, NINE = true,
    }
    for i = 1, 12 do AllowedKeys["F" .. i] = true end
    for i = string.byte("A"), string.byte("Z") do AllowedKeys[string.char(i)] = true end
    local Ok, Settings = pcall(dofile, "ue4ss/Mods/MovieSwap/settings.lua")
    if Ok and type(Settings) == "table" then
        for Name, Rule in pairs(Rules) do
            local Value = Settings[Name]
            if Rule.Kind == "key" then
                if type(Value) == "string" and AllowedKeys[Value] and Key[Value] ~= nil then
                    Config[Name] = Key[Value]
                end
            elseif Rule.Kind == "number" then
                if type(Value) == "number" and Value == Value and Value >= Rule.Min and Value <= Rule.Max then
                    Config[Name] = Value
                end
            elseif Rule.Kind == "boolean" then
                if type(Value) == "boolean" then Config[Name] = Value end
            elseif Rule.Kind == "enum" then
                if type(Value) == "string" and Rule.Values[Value] then Config[Name] = Value end
            end
        end
    end
end
local ScanCount = 0

local Swapped = {}      -- [FullName des FileMediaSource] = neuer Pfad
local AbsRoot = nil

local function Log(msg) print("[MovieSwap] " .. tostring(msg) .. "\n") end

local function FileExistsOnDisk(path)
    local f = io.open(path, "rb")
    if f then f:close() return true end
    return false
end

local function GetAbsRoot()
    if AbsRoot then return AbsRoot end
    local ok, full = pcall(function()
        local lib = StaticFindObject("/Script/Engine.Default__BlueprintPathsLibrary")
        return lib:ConvertRelativePathToFull(ModRoot, ""):ToString()
    end)
    if ok and full and full ~= "" then
        AbsRoot = full:gsub("\\", "/")
        if not AbsRoot:find("/$") then AbsRoot = AbsRoot .. "/" end
        Log("Ersatzordner: " .. AbsRoot)
    end
    return AbsRoot
end

local function Scan(verbose)
    local root = GetAbsRoot()
    if not root then return end
    local sources = FindAllOf("FileMediaSource") or {}
    local changed = 0
    for _, src in ipairs(sources) do
        if src:IsValid() then
            local full = src:GetFullName()
            if not Swapped[full] then
                local fp = src.FilePath:ToString()
                -- Originalpfade sind relativ zum Content-Ordner: "./Bacchus/Movie/..."
                local rel = fp:match("^%./(.+)$")
                if rel then
                    local candidate = ModRoot .. rel
                    if FileExistsOnDisk(candidate) then
                        local newPath = root .. rel
                        src.FilePath = newPath
                        Swapped[full] = newPath
                        changed = changed + 1
                        Log("ersetzt: " .. rel)
                    elseif verbose then
                        Log("kein Ersatz für " .. rel)
                    end
                end
            end
        end
    end
    if changed > 0 then Log(changed .. " Video(s) umgeleitet, insgesamt " .. (function()
        local n = 0 for _ in pairs(Swapped) do n = n + 1 end return n end)()) end
end

-- Die Media-Source-Assets werden zu unterschiedlichen Zeitpunkten geladen, daher regelmäßig prüfen.
LoopAsync(Config.ScanIntervalMs, function()
    ScanCount = ScanCount + 1
    ExecuteInGameThread(function()
        local ok, err = pcall(Scan, false)
        if not ok then Log("Fehler: " .. tostring(err)) end
    end)
    return false
end)

RegisterKeyBind(Config.ReloadKey, function()
    ExecuteInGameThread(function()
        Swapped = {}
        local ok, err = pcall(Scan, true)
        if not ok then Log("Fehler: " .. tostring(err)) end
    end)
end)

Log("geladen - Ersatzvideos unter " .. ModRoot .. " (F11 = neu einlesen)")
