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
local ScanIntervalMs = 2000
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
LoopAsync(ScanIntervalMs, function()
    ScanCount = ScanCount + 1
    ExecuteInGameThread(function()
        local ok, err = pcall(Scan, false)
        if not ok then Log("Fehler: " .. tostring(err)) end
    end)
    return false
end)

RegisterKeyBind(Key.F11, function()
    ExecuteInGameThread(function()
        Swapped = {}
        local ok, err = pcall(Scan, true)
        if not ok then Log("Fehler: " .. tostring(err)) end
    end)
end)

Log("geladen - Ersatzvideos unter " .. ModRoot .. " (F11 = neu einlesen)")
