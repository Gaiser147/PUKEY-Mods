--[[
    LightTools – Licht-/Shader-Werkzeuge für PUKEY GODDESS SHOT TRICK Demo (UE 5.8, UE4SS-Lua)
    Gedacht als Ergänzung zur FreeCam, um dunkle Bereiche sichtbar zu machen.

    Tasten:
      F1          Flutlicht ("Fullbright": 6 schattenlose Richtungslichter beleuchten alles)
      F2          Kopflicht (Punktlicht folgt der Kamera)
      F3          Nebel aus/an
      F4          Post-Processing aus/an (Outline-/Cel-Shader, Drunk-Effekt, Vignette, Abdunklung …)
      F7          Schatten aus/an
      + / -       Helligkeit heller/dunkler (Faktor 2 pro Stufe; Haupttastatur oder Ziffernblock)
      Strg + / -  Flutlicht und Kopflicht heller/dunkler
      Num0 / Ende Alles zurücksetzen

    Hinweise (getestet):
      - Die echte Unlit-Ansicht ("viewmode unlit") ist im Shipping-Build gesperrt,
        daher simuliert F1 sie mit Lichtern.
      - AutoExposureBias und r.ExposureOffset wirken in diesem Spiel nicht,
        daher regelt +/- die Helligkeit per Color Grading (ColorGain/ColorGamma).
      - F3 findet in der Bar-Szene keine Nebel-Komponenten; wirkt nur, wo es welche gibt.
]]

local UEHelpers = require("UEHelpers")

local Config = {
    FloodKey        = Key.F1,
    HeadlightKey    = Key.F2,
    FogKey          = Key.F3,
    PostProcessKey  = Key.F4,
    ShadowKey       = Key.F7,
    ExposureUpKeys   = { Key.ADD, Key.OEM_PLUS },
    ExposureDownKeys = { Key.SUBTRACT, Key.OEM_MINUS },
    ResetKeys        = { Key.NUM_ZERO, Key.END },

    FloodIntensity     = 6.0,      -- Lux pro Richtungslicht
    HeadlightIntensity = 2000.0,   -- Candela
    HeadlightRadius    = 4000.0,   -- cm
    ExposureStep       = 1.0,
    TickMs             = 16,
}

local State = {
    Flood = false, FloodLights = {},
    Headlight = false, Light = nil, LightScale = 1.0,
    FogOff = false, HiddenFog = {},
    PPOff = false, DisabledPP = {},
    ShadowsOff = false, OldShadowQuality = nil,
    Exposure = 0.0, Volume = nil,
    LoopRunning = false, TickCount = 0,
}

local function Log(msg) print("[LightTools] " .. tostring(msg) .. "\n") end
local function Valid(o) return o ~= nil and o:IsValid() end

local function GetPC()
    local pc = UEHelpers.GetPlayerController()
    if Valid(pc) then return pc end
    return nil
end

local function Console(cmd)
    local pc = GetPC()
    local ok, err = pcall(function()
        UEHelpers.GetKismetSystemLibrary():ExecuteConsoleCommand(UEHelpers.GetWorld(), cmd, pc)
    end)
    if not ok then Log("Konsolenbefehl fehlgeschlagen: " .. cmd .. " (" .. tostring(err) .. ")") end
end

local function CVarInt(name)
    local ok, v = pcall(function() return UEHelpers.GetKismetSystemLibrary():GetConsoleVariableIntValue(name) end)
    return ok and v or nil
end

local function SpawnActor(classPath, loc)
    local pc = GetPC()
    local cls = StaticFindObject(classPath)
    if not Valid(cls) then error("Klasse nicht gefunden: " .. classPath) end
    local statics = UEHelpers.GetGameplayStatics()
    local xf = {
        Rotation    = { X = 0.0, Y = 0.0, Z = 0.0, W = 1.0 },
        Translation = { X = loc.X, Y = loc.Y, Z = loc.Z },
        Scale3D     = { X = 1.0, Y = 1.0, Z = 1.0 },
    }
    local actor = statics:BeginDeferredActorSpawnFromClass(UEHelpers.GetWorld(), cls, xf, 1, pc, 1)
    if not Valid(actor) then error("Spawn fehlgeschlagen: " .. classPath) end
    statics:FinishSpawningActor(actor, xf, 1)
    return actor
end

local function CameraLocation()
    local pc = GetPC()
    if not pc then return { X = 0, Y = 0, Z = 0 } end
    return pc.PlayerCameraManager:GetCameraLocation()
end

local function ObjKey(o)
    local ok, a = pcall(function() return o:GetAddress() end)
    return ok and tostring(a) or o:GetFullName()
end

---------------------------------------------------------------------------
-- Eigenes Post-Process-Volume (Belichtung, Effekte neutralisieren)
---------------------------------------------------------------------------
local function EnsureVolume()
    if Valid(State.Volume) then return State.Volume end
    local v = SpawnActor("/Script/Engine.PostProcessVolume", CameraLocation())
    v.bUnbound = true
    v.Priority = 100000.0
    v.BlendWeight = 1.0
    v.bEnabled = true
    State.Volume = v
    return v
end

local function ApplyVolumeSettings()
    local needed = State.Exposure ~= 0.0 or State.PPOff
    if not needed then
        if Valid(State.Volume) then State.Volume.bEnabled = false end
        return
    end
    local v = EnsureVolume()
    v.bEnabled = true
    local s = v.Settings
    s.bOverride_AutoExposureBias = true
    s.AutoExposureBias = State.Exposure
    s.bOverride_VignetteIntensity = State.PPOff
    s.VignetteIntensity = 0.0
    s.bOverride_GrainIntensity = State.PPOff
    s.GrainIntensity = 0.0
    s.bOverride_SceneFringeIntensity = State.PPOff
    s.SceneFringeIntensity = 0.0
    s.bOverride_FilmGrainIntensity = State.PPOff
    s.FilmGrainIntensity = 0.0
    -- AutoExposureBias wird vom Spiel ignoriert (feste Belichtung) -> Helligkeit per Color Grading
    local gain = 2.0 ^ State.Exposure
    s.bOverride_ColorGain = State.Exposure ~= 0.0
    s.ColorGain = { X = 1.0, Y = 1.0, Z = 1.0, W = gain }
    s.bOverride_ColorGamma = State.Exposure > 0.0
    s.ColorGamma = { X = 1.0, Y = 1.0, Z = 1.0, W = 1.0 + 0.1 * math.max(State.Exposure, 0.0) }
end

---------------------------------------------------------------------------
-- F1 Flutlicht
---------------------------------------------------------------------------
local FloodDirections = {
    { Pitch = -90.0, Yaw = 0.0 }, { Pitch = 90.0, Yaw = 0.0 },
    { Pitch = -10.0, Yaw = 0.0 }, { Pitch = -10.0, Yaw = 90.0 },
    { Pitch = -10.0, Yaw = 180.0 }, { Pitch = -10.0, Yaw = 270.0 },
}

local function ApplyFloodIntensity()
    for _, a in ipairs(State.FloodLights) do
        if Valid(a) then a.LightComponent:SetIntensity(Config.FloodIntensity * State.LightScale) end
    end
end

local function SetFlood(on)
    for _, a in ipairs(State.FloodLights) do
        if Valid(a) then a:K2_DestroyActor() end
    end
    State.FloodLights = {}
    if on then
        for _, d in ipairs(FloodDirections) do
            local a = SpawnActor("/Script/Engine.DirectionalLight", CameraLocation())
            local c = a.LightComponent
            c:SetMobility(2)
            c:SetCastShadows(false)
            pcall(function() c.bAtmosphereSunLight = false end)
            a:K2_SetActorRotation({ Pitch = d.Pitch, Yaw = d.Yaw, Roll = 0.0 }, false)
            State.FloodLights[#State.FloodLights + 1] = a
        end
        ApplyFloodIntensity()
    end
    State.Flood = on
    Log("Flutlicht " .. (on and "AN" or "AUS"))
end

---------------------------------------------------------------------------
-- F2 Kopflicht
---------------------------------------------------------------------------
local function ApplyLightIntensity()
    if not Valid(State.Light) then return end
    local c = State.Light.PointLightComponent
    c:SetIntensity(Config.HeadlightIntensity * State.LightScale)
end

local function SetHeadlight(on)
    if on then
        local a = SpawnActor("/Script/Engine.PointLight", CameraLocation())
        local c = a.PointLightComponent
        c:SetMobility(2)               -- Movable
        pcall(function() c:SetIntensityUnits(1) end)   -- Candela
        c:SetAttenuationRadius(Config.HeadlightRadius)
        c:SetCastShadows(false)
        a:SetActorEnableCollision(false)
        State.Light = a
        ApplyLightIntensity()
    elseif Valid(State.Light) then
        State.Light:K2_DestroyActor()
        State.Light = nil
    end
    State.Headlight = on
    Log("Kopflicht " .. (on and "AN" or "AUS"))
end

---------------------------------------------------------------------------
-- F3 Nebel
---------------------------------------------------------------------------
local FogClasses = { "ExponentialHeightFogComponent", "LocalFogVolumeComponent", "VolumetricCloudComponent", "SkyAtmosphereComponent" }

local function HideFogNow()
    local n = 0
    for _, cls in ipairs(FogClasses) do
        local list = FindAllOf(cls) or {}
        for _, c in ipairs(list) do
            local k = ObjKey(c)
            if Valid(c) and not State.HiddenFog[k] then
                local vis = true
                pcall(function() vis = c:IsVisible() end)
                if vis then
                    c:SetVisibility(false, false)
                    State.HiddenFog[k] = c
                    n = n + 1
                end
            end
        end
    end
    return n
end

local function SetFog(off)
    if off then
        local n = HideFogNow()
        Log("Nebel AUS (" .. n .. " Komponenten)")
    else
        for _, c in pairs(State.HiddenFog) do
            if Valid(c) then c:SetVisibility(true, false) end
        end
        State.HiddenFog = {}
        Log("Nebel AN")
    end
    State.FogOff = off
end

---------------------------------------------------------------------------
-- F4 Post-Processing
---------------------------------------------------------------------------
local function DisablePPNow()
    local n = 0
    for _, cls in ipairs({ "PostProcessVolume", "PostProcessComponent" }) do
        local list = FindAllOf(cls) or {}
        for _, o in ipairs(list) do
            local k = ObjKey(o)
            local isOurs = Valid(State.Volume) and k == ObjKey(State.Volume)
            if Valid(o) and not isOurs and not State.DisabledPP[k] then
                local en = false
                pcall(function() en = o.bEnabled end)
                if en then
                    o.bEnabled = false
                    State.DisabledPP[k] = o
                    n = n + 1
                end
            end
        end
    end
    return n
end

local function SetPostProcess(off)
    State.PPOff = off
    if off then
        local n = DisablePPNow()
        Log("Post-Processing AUS (" .. n .. " Volumes/Komponenten)")
    else
        for _, o in pairs(State.DisabledPP) do
            if Valid(o) then o.bEnabled = true end
        end
        State.DisabledPP = {}
        Log("Post-Processing AN")
    end
    ApplyVolumeSettings()
end

---------------------------------------------------------------------------
-- F7 Schatten
---------------------------------------------------------------------------
local function SetShadows(off)
    if off then
        State.OldShadowQuality = CVarInt("r.ShadowQuality") or 3
        Console("r.ShadowQuality 0")
    else
        Console("r.ShadowQuality " .. tostring(State.OldShadowQuality or 3))
    end
    State.ShadowsOff = off
    Log("Schatten " .. (off and "AUS" or "AN") .. " (r.ShadowQuality=" .. tostring(CVarInt("r.ShadowQuality")) .. ")")
end

---------------------------------------------------------------------------
-- Tick: Kopflicht folgt der Kamera, neu gestreamte Level nachbehandeln
---------------------------------------------------------------------------
local function AnythingActive()
    return State.Headlight or State.FogOff or State.PPOff
end

local function Tick()
    State.TickCount = State.TickCount + 1
    if State.Headlight then
        if not Valid(State.Light) then SetHeadlight(true) end
        local loc = CameraLocation()
        State.Light:K2_SetActorLocation({ X = loc.X, Y = loc.Y, Z = loc.Z }, false, {}, true)
    end
    if State.TickCount % 60 == 0 then
        if State.FogOff then HideFogNow() end
        if State.PPOff then DisablePPNow() end
    end
end

local function StartLoop()
    if State.LoopRunning then return end
    State.LoopRunning = true
    LoopAsync(Config.TickMs, function()
        if not AnythingActive() then
            State.LoopRunning = false
            return true
        end
        ExecuteInGameThread(function()
            local ok, err = pcall(Tick)
            if not ok then Log("Tick-Fehler: " .. tostring(err)) end
        end)
        return false
    end)
end

---------------------------------------------------------------------------
-- Tasten
---------------------------------------------------------------------------
local function Bind(key, mods, fn)
    local cb = function()
        ExecuteInGameThread(function()
            local ok, err = pcall(fn)
            if not ok then Log("Fehler: " .. tostring(err)) end
            if AnythingActive() then StartLoop() end
        end)
    end
    if mods then RegisterKeyBind(key, mods, cb) else RegisterKeyBind(key, cb) end
end

Bind(Config.FloodKey, nil, function() SetFlood(not State.Flood) end)
Bind(Config.HeadlightKey, nil, function() SetHeadlight(not State.Headlight) end)
Bind(Config.FogKey, nil, function() SetFog(not State.FogOff) end)
Bind(Config.PostProcessKey, nil, function() SetPostProcess(not State.PPOff) end)
Bind(Config.ShadowKey, nil, function() SetShadows(not State.ShadowsOff) end)

local function ChangeExposure(delta)
    State.Exposure = math.max(-15.0, math.min(15.0, State.Exposure + delta))
    ApplyVolumeSettings(); Log(string.format("Helligkeit %+.0f", State.Exposure))
end

local function ChangeLight(factor)
    State.LightScale = math.max(0.01, math.min(1000.0, State.LightScale * factor))
    ApplyLightIntensity(); ApplyFloodIntensity()
    Log(string.format("Lichtstaerke x%.2f", State.LightScale))
end

for _, k in ipairs(Config.ExposureUpKeys) do
    Bind(k, nil, function() ChangeExposure(Config.ExposureStep) end)
    Bind(k, { ModifierKey.CONTROL }, function() ChangeLight(2.0) end)
end
for _, k in ipairs(Config.ExposureDownKeys) do
    Bind(k, nil, function() ChangeExposure(-Config.ExposureStep) end)
    Bind(k, { ModifierKey.CONTROL }, function() ChangeLight(0.5) end)
end

for _, k in ipairs(Config.ResetKeys) do
    Bind(k, nil, function()
        if State.Flood then SetFlood(false) end
        if State.Headlight then SetHeadlight(false) end
        if State.FogOff then SetFog(false) end
        if State.ShadowsOff then SetShadows(false) end
        State.Exposure = 0.0
        State.LightScale = 1.0
        if State.PPOff then SetPostProcess(false) else ApplyVolumeSettings() end
        Log("alles zurueckgesetzt")
    end)
end

Log("geladen - F1 Flutlicht, F2 Kopflicht, F3 Nebel, F4 Post-Processing, F7 Schatten, +/- Helligkeit, Strg +/- Lichtstaerke, Num0/Ende Reset")
