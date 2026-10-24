--[[
    FamSwap 1.0 - replaces the opponent (Fam) with your own images.
    UE4SS Lua mod for PUKEY GODDESS SHOT TRICK Demo ("Drunken Goddess Reflux", UE 5.8).

    In the game Fam exists twice; both are flat planes showing a texture:

    1. "bar"  - Fam behind the bar counter in search mode (before the match).
                Actor BP_LookPlayerCamera in sublevel LV_Sandbox_SearchMode_Fam, component "Plane",
                material BaseM_UnLitMasked, texture parameter "Texture" (still image T_FAM_STAND1_I_TYPEA).
                -> image: ue4ss/Mods/FamSwap/bar.png  WITH A TRANSPARENT BACKGROUND (alpha channel),
                   same aspect ratio as the original, 2220x4312 (or e.g. 1110x2156).

    2. "game" - Fam at the table during the drinking game (normally videos).
                Actor BP_BT0000, component "PlaneMovie", chroma-key material MI_Fam_Movie,
                texture parameter "Texture00". Every surface using MI_Fam_Movie is covered.
                -> image: ue4ss/Mods/FamSwap/game.png  16:9, pure green background RGB(0,255,0),
                   character top-center.

    The FamSwap Wizard (FamSwap-Wizard.bat) creates both images from any picture.
    If an image file is missing, the original stays.
    Keys: F8 = toggle replacement on/off,  F9 = reload images
]]

local ModDir = "ue4ss/Mods/FamSwap/"

local Targets = {
    {
        Name = "bar",
        Files = { "bar.png", "bar.jpg" },
        OwnerPattern = "SearchMode_Fam.*LookPlayerCamera",
        Component = "Plane",
        Param = "Texture",
    },
    {
        Name = "game",
        Files = { "game.png", "game.jpg" },
        OwnerPattern = "BP_BT0000",
        Component = "PlaneMovie",
        MaterialPattern = "MI_Fam_Movie",   -- additionally every surface using the Fam video material
        Param = "Texture00",
        -- "always": always show the image (also instead of the videos)
        -- "idle":   only while no Fam video is playing (replace the videos e.g. with MovieSwap)
        Mode = "always",
        HideFlipbooks = true,   -- hide Fam's flipbook layers (puke, win ...) while active
    },
}

local Config = { TickMs = 200, ToggleKey = Key.F8, ReloadKey = Key.F9 }
local Enabled = true

local function Log(msg) print("[FamSwap] " .. tostring(msg) .. "\n") end
local function Valid(o) return type(o) == "userdata" and o:IsValid() end

local function FileExists(path)
    local f = io.open(path, "rb")
    if f then f:close() return true end
    return false
end

local function LoadTexture(t)
    for _, file in ipairs(t.Files) do
        local rel = ModDir .. file
        if FileExists(rel) then
            local lib = StaticFindObject("/Script/Engine.Default__BlueprintPathsLibrary")
            local full = lib:ConvertRelativePathToFull(rel, ""):ToString()
            local krl = StaticFindObject("/Script/Engine.Default__KismetRenderingLibrary")
            local tex = krl:ImportFileAsTexture2D(FindFirstOf("World"), full)
            if Valid(tex) then
                Log(string.format("[%s] image loaded: %s (%dx%d)", t.Name, file, tex:Blueprint_GetSizeX(), tex:Blueprint_GetSizeY()))
                return tex
            end
            Log("[" .. t.Name .. "] could not load image: " .. full)
        end
    end
    return false   -- no replacement for this target
end

local function FamPlayersPlaying()
    for _, n in ipairs({ "MP_MainGame_Fam_00", "MP_MainGame_Fam_01" }) do
        local mp = StaticFindObject("/Game/Bacchus/Gameplay/Character/Fam/" .. n .. "." .. n)
        if Valid(mp) then
            local ok, playing = pcall(function() return mp:IsPlaying() end)
            if ok and playing then return true end
        end
    end
    return false
end

-- All matching components: name/owner match OR the material derives from MaterialPattern
-- (also catches further Fam surfaces the game might only use during the drinking game).
local function MaterialMatches(c, pattern)
    if not pattern then return false end
    local ok, hit = pcall(function()
        local m = c:GetMaterial(0)
        for _ = 1, 4 do                       -- the material and up to 3 parent levels
            if not Valid(m) then return false end
            if m:GetFullName():find(pattern) then return true end
            local okp, parent = pcall(function() return m.Parent end)
            if not okp then return false end
            m = parent
        end
        return false
    end)
    return ok and hit
end

local function FindComponents(t)
    local found = {}
    for _, c in ipairs(FindAllOf("StaticMeshComponent") or {}) do
        if Valid(c) then
            local owner = c:GetOwner()
            if Valid(owner) then
                local byName = c:GetFName():ToString():find("^" .. t.Component)
                    and owner:GetFullName():find(t.OwnerPattern)
                if byName or MaterialMatches(c, t.MaterialPattern) then
                    found[#found + 1] = { comp = c, owner = owner }
                end
            end
        end
    end
    return found
end

local function GetMID(comp)
    local mat = comp:GetMaterial(0)
    if not Valid(mat) then return nil end
    if mat:GetClass():GetFName():ToString() == "MaterialInstanceDynamic" then return mat end
    return comp:CreateDynamicMaterialInstance(0, mat, FName("FamSwapMID"))
end

-- Import the texture only right before it is assigned. An imported texture that no material
-- references yet gets garbage-collected, and the Lua handle then points at an unrelated object
-- (that once showed a ghost sprite instead of the image). Hence the name check.
local function EnsureTexture(t)
    if Valid(t.Texture) and t.TexName and t.Texture:GetFullName() == t.TexName then return true end
    t.Texture, t.TexName = nil, nil
    local tex = LoadTexture(t)
    if not tex then return false end
    t.Texture, t.TexName = tex, tex:GetFullName()
    return true
end

local function HasFile(t)
    for _, file in ipairs(t.Files) do
        if FileExists(ModDir .. file) then return true end
    end
    return false
end

local function ApplyOne(t, comp, owner)
    local mid = GetMID(comp)
    if not Valid(mid) then return end

    t.ParamFName = t.ParamFName or FName(t.Param)
    local current = mid:K2_GetTextureParameterValue(t.ParamFName)
    local currentName = Valid(current) and current:GetFullName() or ""
    local isOurs = t.TexName ~= nil and currentName == t.TexName
    local key = mid:GetFullName()

    -- Remember the original per material instance so F8 can restore it
    t.Originals = t.Originals or {}
    if Valid(current) and not isOurs then
        t.Originals[key] = current
        if not t.LoggedOriginal then
            t.LoggedOriginal = true
            pcall(function()
                Log(string.format("[%s] original: %s (%dx%d)", t.Name, currentName,
                    current:Blueprint_GetSizeX(), current:Blueprint_GetSizeY()))
            end)
        end
    end

    local want = Enabled and (t.Mode ~= "idle" or not FamPlayersPlaying())
    if want and not isOurs then
        if EnsureTexture(t) then
            mid:SetTextureParameterValue(t.ParamFName, t.Texture)
            t.SetCount = (t.SetCount or 0) + 1
            if t.SetCount <= 5 or t.SetCount % 50 == 0 then
                Log(string.format("[%s] replacement applied (%s, was: %s) #%d", t.Name,
                    comp:GetFName():ToString(), currentName:match("[^/.]+$") or currentName, t.SetCount))
            end
        end
    elseif not want and isOurs and Valid(t.Originals[key]) then
        mid:SetTextureParameterValue(t.ParamFName, t.Originals[key])
    end

    if want and t.HideFlipbooks then
        for _, fb in ipairs(FindAllOf("PaperFlipbookComponent") or {}) do
            if Valid(fb) and fb:GetOwner():GetFullName() == owner:GetFullName() and fb:IsVisible() then
                fb:SetVisibility(false, false)
            end
        end
    end
end

local function ApplyTarget(t)
    if t.HasFile == nil then t.HasFile = HasFile(t) end
    if not t.HasFile then return end
    -- Full search only every 10th tick (2 s); otherwise re-check the cached list
    t.Tick = (t.Tick or 0) + 1
    local list = t.Cache
    local stale = list == nil or t.Tick % 10 == 0
    if not stale then
        for _, e in ipairs(list) do
            if not (Valid(e.comp) and Valid(e.owner)) then stale = true break end
        end
    end
    if stale then
        list = FindComponents(t)
        t.Cache = list
    end
    -- Log changes in the set of matched surfaces (diagnostics)
    local sig = {}
    for _, e in ipairs(list) do sig[#sig + 1] = e.owner:GetFName():ToString() .. "." .. e.comp:GetFName():ToString() end
    local sigStr = table.concat(sig, ", ")
    if sigStr ~= t.LastSig then
        t.LastSig = sigStr
        Log(string.format("[%s] %d surface(s): %s", t.Name, #list, sigStr ~= "" and sigStr or "-"))
    end
    for _, e in ipairs(list) do ApplyOne(t, e.comp, e.owner) end
end

LoopAsync(Config.TickMs, function()
    ExecuteInGameThread(function()
        for _, t in ipairs(Targets) do
            local ok, err = pcall(ApplyTarget, t)
            if not ok and t.LastError ~= tostring(err) then
                t.LastError = tostring(err)
                Log("[" .. t.Name .. "] error: " .. t.LastError)
            end
        end
    end)
    return false
end)

RegisterKeyBind(Config.ToggleKey, function()
    Enabled = not Enabled
    Log("replacement " .. (Enabled and "ON" or "OFF"))
end)

RegisterKeyBind(Config.ReloadKey, function()
    ExecuteInGameThread(function()
        for _, t in ipairs(Targets) do t.Texture, t.TexName, t.HasFile = nil, nil, nil end
        Log("reloading images ...")
    end)
end)

Log("loaded - bar.png (bar counter, transparent) / game.png (table, green screen); F8 on/off, F9 reload")
