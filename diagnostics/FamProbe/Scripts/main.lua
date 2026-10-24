--[[
    FamProbe – Diagnose: Wie wird Fam in der Bar dargestellt?
    Läuft automatisch alle 15 s (max. 20 Durchläufe) und schreibt bei Änderungen nach
    ue4ss/Mods/FamProbe/fam_out.txt:
      - alle PrimitiveComponents, deren Owner BP_BT0000 ist (Klasse, Sichtbarkeit, Position,
        Mesh/Sprite/Flipbook, Materialien inkl. Parent und Texturparameter)
      - alle MediaPlayer mit URL/Status
]]

local OutPath = "ue4ss/Mods/FamProbe/fam_out.txt"
local Out = io.open(OutPath, "w")
local function W(s)
    if Out then Out:write(s .. "\n"); Out:flush() end
end

local function N(o)
    if o == nil then return "nil" end
    local ok, s = pcall(function() return o:GetFullName() end)
    return ok and s or "?"
end

local function DumpMaterial(m, indent)
    W(indent .. "material = " .. N(m))
    pcall(function()
        local p = m.Parent
        if p and p:IsValid() then W(indent .. "  parent = " .. N(p)) end
    end)
    pcall(function()
        m.TextureParameterValues:ForEach(function(_, e)
            local v = e:get()
            W(indent .. "  tex " .. v.ParameterInfo.Name:ToString() .. " = " .. N(v.ParameterValue))
        end)
    end)
end

local function DumpComponent(c)
    local cls = c:GetClass():GetFName():ToString()
    local vis, loc = "?", "?"
    pcall(function() vis = tostring(c:IsVisible()) end)
    pcall(function()
        local l = c:K2_GetComponentLocation()
        loc = string.format("%.0f/%.0f/%.0f", l.X, l.Y, l.Z)
    end)
    W("  " .. cls .. "  " .. c:GetFName():ToString() .. "  visible=" .. vis .. "  pos=" .. loc)
    pcall(function() W("    mesh = " .. N(c.StaticMesh)) end)
    if cls:find("Flipbook") then pcall(function() W("    flipbook = " .. N(c:GetFlipbook())) end) end
    if cls:find("Sprite") then pcall(function() W("    sprite = " .. N(c:GetSprite())) end) end
    local nm = 0
    pcall(function() nm = c:GetNumMaterials() end)
    for i = 0, nm - 1 do
        pcall(function() DumpMaterial(c:GetMaterial(i), "    [" .. i .. "] ") end)
    end
end

local lastSig = ""

local function Probe()
    local prims = FindAllOf("PrimitiveComponent") or {}
    local mine = {}
    for _, c in ipairs(prims) do
        if c:IsValid() then
            local ok, owner = pcall(function() return N(c:GetOwner()) end)
            if ok and (owner:find("BP_BT0000") or owner:find("SearchMode_Fam") or owner:find("LookPlayerCamera")) then mine[#mine + 1] = c end
        end
    end
    local players = FindAllOf("MediaPlayer") or {}

    local sig = tostring(#mine)
    for _, c in ipairs(mine) do
        local v = "?"
        pcall(function() v = tostring(c:IsVisible()) end)
        sig = sig .. c:GetFName():ToString() .. v
    end
    for _, mp in ipairs(players) do
        pcall(function() sig = sig .. mp:GetUrl():ToString() .. tostring(mp:IsPlaying()) end)
    end
    if sig == lastSig then return end
    lastSig = sig

    W("===== " .. os.date("%H:%M:%S") .. "  BP_BT0000-Komponenten: " .. #mine)
    for _, c in ipairs(mine) do pcall(DumpComponent, c) end
    W("--- MediaPlayer")
    for _, mp in ipairs(players) do
        pcall(function()
            W("  " .. N(mp) .. "  playing=" .. tostring(mp:IsPlaying()) .. "  url=" .. mp:GetUrl():ToString())
        end)
    end
end

local runs = 0
LoopAsync(15000, function()
    runs = runs + 1
    if runs > 20 then
        W("ENDE")
        if Out then Out:close(); Out = nil end
        return true
    end
    ExecuteInGameThread(function()
        local ok, err = pcall(Probe)
        if not ok then W("FEHLER " .. tostring(err)) end
    end)
    return false
end)

print("[FamProbe] geladen\n")
