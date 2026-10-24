--[[
    FreeCam / Spectator-Mod für PUKEY GODDESS SHOT TRICK Demo (UE 5.8, UE4SS-Lua)

    Tasten:
      F5        FreeCam an/aus
      W/A/S/D   bewegen,  Maus = umsehen
      E / Space hoch,  Q / Strg = runter
      Shift     gedrückt halten = schneller
      Bild ↑/↓  Grundgeschwindigkeit erhöhen/verringern
      Pos1      Geschwindigkeit zurücksetzen
      F6        Modus wechseln (nur wenn FreeCam aus ist)

    Teleport:
      T             Spielfigur an die FreeCam-Position teleportieren (beendet die FreeCam)
      Strg+1 … 5    aktuelle Kameraposition in Platz 1–5 speichern (pro Map, bleibt nach Neustart)
      1 … 5         zu gespeicherter Position springen (schaltet die FreeCam bei Bedarf ein)
      Die Plätze stehen in ue4ss/Mods/FreeCam/positions.txt.

    Modi:
      "possess"    – spawnt einen SpectatorPawn ohne Kollision und übernimmt ihn
                     (Engine-Bewegung, flüssigste Variante).
      "viewtarget" – lässt die Spielfigur in Ruhe, spawnt nur eine Kamera und
                     bewegt sie selbst (Fallback, falls "possess" das Spiel stört).
]]

local UEHelpers = require("UEHelpers")

local Config = {
    Mode          = "possess",   -- "possess" oder "viewtarget"
    ToggleKey     = Key.F5,
    ModeKey       = Key.F6,
    SpeedUpKey    = Key.PAGE_UP,
    SpeedDownKey  = Key.PAGE_DOWN,
    SpeedResetKey = Key.HOME,
    TeleportKey   = Key.T,
    SlotKeys      = { Key.ONE, Key.TWO, Key.THREE, Key.FOUR, Key.FIVE },
    PositionsFile = "ue4ss/Mods/FreeCam/positions.txt",
    DefaultSpeed  = 400.0,       -- cm/s
    BoostFactor   = 4.0,
    MouseSens     = 0.15,        -- nur "viewtarget"
    TickMs        = 8,
}

local State = {
    Active        = false,
    Busy          = false,
    Camera        = nil,   -- gespawnter SpectatorPawn bzw. CameraActor
    OriginalPawn  = nil,
    OriginalView  = nil,
    CursorWasShown = false,
    Speed         = Config.DefaultSpeed,
    Pos           = nil,   -- {X,Y,Z}       ("viewtarget")
    Rot           = nil,   -- {Pitch,Yaw}   ("viewtarget")
    LastTime      = 0,
    LoopRunning   = false,
}

local function Log(msg) print("[FreeCam] " .. tostring(msg) .. "\n") end

local function Valid(o) return o ~= nil and o:IsValid() end

local KeyCache = {}
local function K(name)
    if not KeyCache[name] then KeyCache[name] = { KeyName = FName(name) } end
    return KeyCache[name]
end

local function Down(pc, name) return pc:IsInputKeyDown(K(name)) end

local function GetPC()
    local pc = UEHelpers.GetPlayerController()
    if Valid(pc) then return pc end
    return nil
end

local function GetWorld(pc)
    local ok, w = pcall(function() return UEHelpers.GetWorld() end)
    if ok and Valid(w) then return w end
    return pc:GetWorld()
end

local function SpawnActor(pc, classPath, loc)
    local cls = StaticFindObject(classPath)
    if not Valid(cls) then error("Klasse nicht gefunden: " .. classPath) end
    local statics = UEHelpers.GetGameplayStatics()
    local xf = {
        Rotation    = { X = 0.0, Y = 0.0, Z = 0.0, W = 1.0 },
        Translation = { X = loc.X, Y = loc.Y, Z = loc.Z },
        Scale3D     = { X = 1.0, Y = 1.0, Z = 1.0 },
    }
    -- 1 = ESpawnActorCollisionHandlingMethod::AlwaysSpawn, 1 = ESpawnActorScaleMethod::MultiplyWithRoot
    local actor = statics:BeginDeferredActorSpawnFromClass(GetWorld(pc), cls, xf, 1, pc, 1)
    if not Valid(actor) then error("Spawn fehlgeschlagen: " .. classPath) end
    statics:FinishSpawningActor(actor, xf, 1)
    return actor
end

local function SetGameOnlyInput(pc)
    State.CursorWasShown = pc.bShowMouseCursor
    pc.bShowMouseCursor = false
    pcall(function()
        local wbl = StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary")
        wbl:SetInputMode_GameOnly(pc, false)
    end)
end

local function RestoreInput(pc)
    if State.CursorWasShown then
        pc.bShowMouseCursor = true
        pcall(function()
            local wbl = StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary")
            -- 0 = EMouseLockMode::DoNotLock
            wbl:SetInputMode_GameAndUIEx(pc, nil, 0, false, false)
        end)
    end
end

local function CurrentSpeed(pc)
    local s = State.Speed
    if Down(pc, "LeftShift") or Down(pc, "RightShift") then s = s * Config.BoostFactor end
    return s
end

---------------------------------------------------------------------------
-- Modus "possess"
---------------------------------------------------------------------------
local function EnablePossess(pc, loc, rot)
    local spec = SpawnActor(pc, "/Script/Engine.SpectatorPawn", loc)
    spec:SetActorEnableCollision(false)
    pc:Possess(spec)
    pc:SetControlRotation({ Pitch = rot.Pitch, Yaw = rot.Yaw, Roll = 0.0 })
    State.Camera = spec
end

local function TickPossess(pc)
    local spec = State.Camera
    local move = spec.MovementComponent
    if Valid(move) then move.MaxSpeed = CurrentSpeed(pc) end
end

local function DisablePossess(pc)
    if Valid(State.OriginalPawn) then pc:Possess(State.OriginalPawn) end
end

---------------------------------------------------------------------------
-- Modus "viewtarget"
---------------------------------------------------------------------------
local function EnableViewTarget(pc, loc, rot)
    local cam = SpawnActor(pc, "/Script/Engine.CameraActor", loc)
    cam:SetActorEnableCollision(false)
    State.Pos = { X = loc.X, Y = loc.Y, Z = loc.Z }
    State.Rot = { Pitch = rot.Pitch, Yaw = rot.Yaw }
    pc:SetIgnoreMoveInput(true)
    pc:SetIgnoreLookInput(true)
    pc:SetViewTargetWithBlend(cam, 0.0, 0, 0.0, false)
    State.Camera = cam
end

local function TickViewTarget(pc, dt)
    local r = State.Rot
    r.Yaw   = r.Yaw   + pc:GetInputAnalogKeyState(K("MouseX")) * Config.MouseSens * 10.0
    r.Pitch = math.max(-89.0, math.min(89.0,
              r.Pitch + pc:GetInputAnalogKeyState(K("MouseY")) * Config.MouseSens * 10.0))

    local f, ri, u = 0.0, 0.0, 0.0
    if Down(pc, "W") then f = f + 1 end
    if Down(pc, "S") then f = f - 1 end
    if Down(pc, "D") then ri = ri + 1 end
    if Down(pc, "A") then ri = ri - 1 end
    if Down(pc, "E") or Down(pc, "SpaceBar") then u = u + 1 end
    if Down(pc, "Q") or Down(pc, "LeftControl") then u = u - 1 end

    local p, y = math.rad(r.Pitch), math.rad(r.Yaw)
    local step = CurrentSpeed(pc) * dt
    local fx, fy, fz = math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)
    local rx, ry     = -math.sin(y), math.cos(y)
    local pos = State.Pos
    pos.X = pos.X + (fx * f + rx * ri) * step
    pos.Y = pos.Y + (fy * f + ry * ri) * step
    pos.Z = pos.Z + (fz * f + u) * step

    State.Camera:K2_SetActorLocationAndRotation(
        { X = pos.X, Y = pos.Y, Z = pos.Z },
        { Pitch = r.Pitch, Yaw = r.Yaw, Roll = 0.0 },
        false, {}, true)
end

local function DisableViewTarget(pc)
    pc:SetIgnoreMoveInput(false)
    pc:SetIgnoreLookInput(false)
    local target = State.OriginalView
    if not Valid(target) then target = State.OriginalPawn end
    if Valid(target) then pc:SetViewTargetWithBlend(target, 0.0, 0, 0.0, false) end
end

---------------------------------------------------------------------------
-- Steuerung
---------------------------------------------------------------------------
local function Tick()
    if not State.Active then return end
    local pc = GetPC()
    if not pc or not Valid(State.Camera) then
        Log("Kamera oder PlayerController verloren (Levelwechsel?) - FreeCam aus.")
        State.Active = false
        return
    end
    local now = os.clock()
    local dt = math.min(now - State.LastTime, 0.1)
    State.LastTime = now
    if Config.Mode == "possess" then TickPossess(pc) else TickViewTarget(pc, dt) end
end

local function StartLoop()
    if State.LoopRunning then return end
    State.LoopRunning = true
    LoopAsync(Config.TickMs, function()
        if not State.Active then
            State.LoopRunning = false
            return true
        end
        ExecuteInGameThread(function()
            local ok, err = pcall(Tick)
            if not ok then Log("Tick-Fehler: " .. tostring(err)); State.Active = false end
        end)
        return false
    end)
end

local function Enable()
    local pc = GetPC()
    if not pc then Log("Kein PlayerController gefunden.") return end
    local camMgr = pc.PlayerCameraManager
    local loc = camMgr:GetCameraLocation()
    local rot = camMgr:GetCameraRotation()

    State.OriginalPawn = pc.Pawn
    State.OriginalView = pc:GetViewTarget()
    if Config.Mode == "possess" then EnablePossess(pc, loc, rot) else EnableViewTarget(pc, loc, rot) end
    SetGameOnlyInput(pc)

    State.Active = true
    State.LastTime = os.clock()
    StartLoop()
    Log(string.format("AN (Modus %s) bei X=%.0f Y=%.0f Z=%.0f", Config.Mode, loc.X, loc.Y, loc.Z))
end

local function Disable()
    State.Active = false
    local pc = GetPC()
    if pc then
        if Config.Mode == "possess" then DisablePossess(pc) else DisableViewTarget(pc) end
        RestoreInput(pc)
    end
    if Valid(State.Camera) then State.Camera:K2_DestroyActor() end
    State.Camera, State.OriginalPawn, State.OriginalView = nil, nil, nil
    Log("AUS")
end

---------------------------------------------------------------------------
-- Teleport & gespeicherte Positionen
---------------------------------------------------------------------------
-- Aktuelle FreeCam-Position und -Blickrichtung
local function CamTransform(pc)
    if Config.Mode == "possess" then
        local loc = State.Camera:K2_GetActorLocation()
        -- GetControlRotation() liefert hier keine lesbaren Felder, der Kamera-Manager schon
        local rot = pc.PlayerCameraManager:GetCameraRotation()
        return { X = loc.X, Y = loc.Y, Z = loc.Z }, { Pitch = rot.Pitch, Yaw = rot.Yaw }
    end
    return { X = State.Pos.X, Y = State.Pos.Y, Z = State.Pos.Z }, { Pitch = State.Rot.Pitch, Yaw = State.Rot.Yaw }
end

local function MoveCamTo(pc, loc, rot)
    if Config.Mode == "possess" then
        State.Camera:K2_SetActorLocation({ X = loc.X, Y = loc.Y, Z = loc.Z }, false, {}, true)
        pc:SetControlRotation({ Pitch = rot.Pitch, Yaw = rot.Yaw, Roll = 0.0 })
    else
        State.Pos = { X = loc.X, Y = loc.Y, Z = loc.Z }
        State.Rot = { Pitch = rot.Pitch, Yaw = rot.Yaw }
    end
end

local function TeleportPlayer()
    if not State.Active then Log("Teleport: erst FreeCam einschalten (F5) und hinfliegen.") return end
    local pc = GetPC()
    local pawn = State.OriginalPawn
    if not pc or not Valid(pawn) then Log("Teleport: keine Spielfigur gefunden.") return end
    local loc, rot = CamTransform(pc)
    -- Die Kamera sitzt auf Augenhöhe, der Pawn-Ursprung tiefer
    local eye = 0.0
    pcall(function() eye = pawn.BaseEyeHeight end)
    local dest = { X = loc.X, Y = loc.Y, Z = loc.Z - eye }

    Disable()   -- Spielfigur zurück übernehmen, Spectator entfernen
    local ok = false
    pcall(function() ok = pawn:K2_TeleportTo(dest, { Pitch = 0.0, Yaw = rot.Yaw, Roll = 0.0 }) end)
    if not ok then
        -- Ziel blockiert (z. B. in einer Wand): ohne Kollisionsprüfung setzen
        pawn:K2_SetActorLocation(dest, false, {}, true)
        Log("Teleport: Ziel war blockiert, Position wurde erzwungen (evtl. steckst du fest).")
    end
    pc:SetControlRotation({ Pitch = rot.Pitch, Yaw = rot.Yaw, Roll = 0.0 })
    Log(string.format("Spielfigur teleportiert nach X=%.0f Y=%.0f Z=%.0f", dest.X, dest.Y, dest.Z))
end

local Slots = {}   -- [map] = { [n] = {X,Y,Z,Pitch,Yaw} }

local function MapName()
    local ok, name = pcall(function()
        return UEHelpers.GetGameplayStatics():GetCurrentLevelName(GetWorld(GetPC()), true):ToString()
    end)
    return ok and name or "unbekannt"
end

local function LoadSlots()
    Slots = {}
    local f = io.open(Config.PositionsFile, "r")
    if not f then return end
    for line in f:lines() do
        local map, n, x, y, z, pitch, yaw = line:match("^([^|]+)|(%d+)|([^|]+)|([^|]+)|([^|]+)|([^|]+)|([^|]+)$")
        if map then
            Slots[map] = Slots[map] or {}
            Slots[map][tonumber(n)] = { X = tonumber(x), Y = tonumber(y), Z = tonumber(z),
                                        Pitch = tonumber(pitch), Yaw = tonumber(yaw) }
        end
    end
    f:close()
end

local function SaveSlots()
    local f = io.open(Config.PositionsFile, "w")
    if not f then Log("Konnte " .. Config.PositionsFile .. " nicht schreiben.") return end
    for map, list in pairs(Slots) do
        for n, p in pairs(list) do
            f:write(string.format("%s|%d|%.2f|%.2f|%.2f|%.2f|%.2f\n", map, n, p.X, p.Y, p.Z, p.Pitch or 0.0, p.Yaw or 0.0))
        end
    end
    f:close()
end

local function StoreSlot(n)
    local pc = GetPC()
    if not pc then return end
    local loc, rot
    if State.Active then
        loc, rot = CamTransform(pc)
    else
        local cm = pc.PlayerCameraManager
        local l, r = cm:GetCameraLocation(), cm:GetCameraRotation()
        loc, rot = { X = l.X, Y = l.Y, Z = l.Z }, { Pitch = r.Pitch, Yaw = r.Yaw }
    end
    local map = MapName()
    Slots[map] = Slots[map] or {}
    Slots[map][n] = { X = loc.X, Y = loc.Y, Z = loc.Z, Pitch = rot.Pitch, Yaw = rot.Yaw }
    SaveSlots()
    Log(string.format("Platz %d gespeichert (%s: X=%.0f Y=%.0f Z=%.0f)", n, map, loc.X, loc.Y, loc.Z))
end

local function GotoSlot(n)
    local map = MapName()
    local p = Slots[map] and Slots[map][n]
    if not p then Log(string.format("Platz %d ist für %s leer (Strg+%d zum Speichern).", n, map, n)) return end
    if not State.Active then Enable() end
    local pc = GetPC()
    if not (State.Active and pc) then return end
    MoveCamTo(pc, p, p)
    Log(string.format("Zu Platz %d gesprungen", n))
end

local function Guarded(fn)
    return function()
        if State.Busy then return end
        State.Busy = true
        ExecuteInGameThread(function()
            local ok, err = pcall(fn)
            if not ok then Log("Fehler: " .. tostring(err)) end
            State.Busy = false
        end)
    end
end

RegisterKeyBind(Config.ToggleKey, Guarded(function()
    if State.Active then Disable() else Enable() end
end))

RegisterKeyBind(Config.ModeKey, Guarded(function()
    if State.Active then Log("Erst FreeCam ausschalten (F5), dann Modus wechseln.") return end
    Config.Mode = (Config.Mode == "possess") and "viewtarget" or "possess"
    Log("Modus: " .. Config.Mode)
end))

RegisterKeyBind(Config.TeleportKey, Guarded(TeleportPlayer))

for i, k in ipairs(Config.SlotKeys) do
    RegisterKeyBind(k, Guarded(function() GotoSlot(i) end))
    RegisterKeyBind(k, { ModifierKey.CONTROL }, Guarded(function() StoreSlot(i) end))
end

LoadSlots()

RegisterKeyBind(Config.SpeedUpKey, function()
    State.Speed = math.min(State.Speed * 1.5, 20000.0); Log(string.format("Speed %.0f", State.Speed))
end)
RegisterKeyBind(Config.SpeedDownKey, function()
    State.Speed = math.max(State.Speed / 1.5, 10.0); Log(string.format("Speed %.0f", State.Speed))
end)
RegisterKeyBind(Config.SpeedResetKey, function()
    State.Speed = Config.DefaultSpeed; Log(string.format("Speed %.0f", State.Speed))
end)

Log("geladen - F5 = FreeCam an/aus, F6 = Modus, T = Spieler teleportieren, Strg+1-5 speichern, 1-5 springen")
