--[[
    EditionProbe – Analyse-Mod (UE4SS-Lua)
    F9: sucht alle Bacchus-Klassen mit Demo/Edition-Bezug, liest die Default-Werte
        (CDO) dieser Properties aus, ruft die parameterlosen Funktionen der
        BCS_DemoBuildLibrary auf und schreibt alles nach probe_out.txt.
]]

local OutPath = "ue4ss/Mods/EditionProbe/probe_out.txt"
local Lines = {}
local Quiet = false
local function Out(s) Lines[#Lines + 1] = s; if not Quiet then print("[EditionProbe] " .. s .. "\n") end end

local function PropType(p) return p:GetClass():GetFName():ToString() end
local function PName(p) return p:GetFName():ToString() end

local Value
Value = function(val, prop, depth)
    depth = depth or 0
    if depth > 6 then return "..." end
    if type(val) ~= "userdata" then return tostring(val) end
    local pt = prop and PropType(prop) or "?"
    local ok, res = pcall(function()
        if pt == "StrProperty" or pt == "NameProperty" or pt == "TextProperty" then
            return '"' .. val:ToString() .. '"'
        elseif pt == "ArrayProperty" then
            local inner, items = prop:GetInner(), {}
            val:ForEach(function(_, e) items[#items + 1] = Value(e:get(), inner, depth + 1) end)
            return "[" .. table.concat(items, ", ") .. "]"
        elseif pt == "StructProperty" then
            local fields = {}
            prop:GetStruct():ForEachProperty(function(p)
                local n = PName(p)
                local ok2, r = pcall(function() return Value(val[n], p, depth + 1) end)
                fields[#fields + 1] = n .. "=" .. (ok2 and r or "?")
            end)
            return "{" .. table.concat(fields, ", ") .. "}"
        elseif pt == "ObjectProperty" or pt == "ClassProperty" or pt == "WeakObjectProperty" then
            return val:IsValid() and val:GetFullName() or "None"
        end
        if val.ToString then return val:ToString() end
        return tostring(val)
    end)
    return ok and res or ("<" .. pt .. ">")
end

local function Interesting(name)
    local l = name:lower()
    return l:find("demo") or l:find("edition") or l:find("exclud") or l:find("unreachable")
end

local function Probe()
    Lines = {}
    local classCls = StaticFindObject("/Script/CoreUObject.Class")
    local found = {}
    ForEachUObject(function(obj)
        if obj:IsA(classCls) then
            local full = obj:GetFullName()
            if full:find("/Script/Bacchus%.") then found[#found + 1] = obj end
        end
    end)
    Out(string.format("%d native Bacchus-Klassen gefunden", #found))

    for _, cls in ipairs(found) do
        local cname = cls:GetFullName()
        local props, funcs = {}, {}
        cls:ForEachProperty(function(p) if Interesting(PName(p)) then props[#props + 1] = p end end)
        cls:ForEachFunction(function(f)
            if Interesting(f:GetFName():ToString()) then funcs[#funcs + 1] = f end
        end)
        if #props > 0 or #funcs > 0 then
            Out("")
            Out("== " .. cname)
            local cdo = cls:GetCDO()
            for _, p in ipairs(props) do
                local v = "?"
                if cdo and cdo:IsValid() then
                    local ok, r = pcall(function() return Value(cdo[PName(p)], p) end)
                    v = ok and r or ("ERR " .. tostring(r))
                end
                Out(string.format("  PROP %s (%s) = %s", PName(p), PropType(p), v))
            end
            for _, f in ipairs(funcs) do
                local params = {}
                f:ForEachProperty(function(p) params[#params + 1] = PName(p) .. ":" .. PropType(p) end)
                Out(string.format("  FUNC %s(%s)", f:GetFName():ToString(), table.concat(params, ", ")))
            end
        end
    end

    -- Laufzeitwerte der Demo-Bibliothek
    Out("")
    Out("== Aufrufe BCS_DemoBuildLibrary")
    local lib = StaticFindObject("/Script/Bacchus.Default__BCS_DemoBuildLibrary")
    if lib and lib:IsValid() then
        local pc = FindFirstOf("PlayerController")
        for _, fn in ipairs({ "IsDemoBuild", "GetGameEdition", "GetDemoTitleSuffix" }) do
            local ok, r = pcall(function() return lib[fn](lib) end)
            if not ok and pc then ok, r = pcall(function() return lib[fn](lib, pc) end) end
            if type(r) == "userdata" and r.ToString then r = r:ToString() end
            Out(string.format("  %s() -> %s %s", fn, ok and "" or "FEHLER", tostring(r)))
        end
    else
        Out("  Default__BCS_DemoBuildLibrary nicht gefunden")
    end

    local f = io.open(OutPath, "w")
    if f then f:write(table.concat(Lines, "\n")); f:close(); Out("geschrieben: " .. OutPath) end
end

-- F8: Schlüssel aller Lokalisierungstabellen auflisten
local TextTables = { "Event", "Battle", "UI", "System", "Help", "Bar_Femme", "Bar_Souls", "DEMO", "Drink",
    "FamRule", "Item", "SoulsSkill", "Trick", "Trophy", "Past", "EndingCall" }

local function KeyString(k)
    if type(k) ~= "userdata" then return tostring(k) end
    local ok, s = pcall(function() return k:ToString() end)
    return ok and s or tostring(k)
end

local TextLog
local function TOut(s)
    if TextLog then TextLog:write(s .. "\n"); TextLog:flush() end
end

local function ProbeTexts()
    TextLog = io.open("ue4ss/Mods/EditionProbe/texts_out.txt", "w")
    for _, t in ipairs(TextTables) do
        local name = "DA_LocalizeTextData_" .. t
        local path = "/Game/Bacchus/Text/" .. name .. "." .. name
        local asset = StaticFindObject(path)
        if not (asset and asset:IsValid()) then
            local ok, a = pcall(LoadAsset, path)
            asset = ok and a or nil
        end
        if not (asset and asset:IsValid()) then
            TOut("## " .. name .. ": nicht vorhanden")
        else
            TOut("## " .. name .. " (" .. asset:GetClass():GetFullName() .. ")")
            asset:GetClass():ForEachProperty(function(p)
                local pt, n = PropType(p), PName(p)
                local info = ""
                if pt == "MapProperty" then
                    info = string.format(" key=%s value=%s", PropType(p:GetKeyProp()), PropType(p:GetValueProp()))
                    if PropType(p:GetValueProp()) == "StructProperty" then
                        info = info .. " struct=" .. p:GetValueProp():GetStruct():GetFullName()
                    end
                elseif pt == "ArrayProperty" then
                    local inner = p:GetInner()
                    info = " inner=" .. PropType(inner)
                    if PropType(inner) == "StructProperty" then info = info .. " struct=" .. inner:GetStruct():GetFullName() end
                    local ok, num = pcall(function() return asset[n]:GetArrayNum() end)
                    info = info .. " num=" .. tostring(ok and num or "?")
                end
                TOut(string.format("  %s (%s)%s", n, pt, info))
            end)
        end
    end
    TOut("ENDE")
    TextLog:close(); TextLog = nil
    print("[EditionProbe] Struktur geschrieben\n")
end

RegisterKeyBind(Key.F8, function()
    ExecuteInGameThread(function()
        local ok, err = pcall(ProbeTexts)
        if TextLog then TextLog:close(); TextLog = nil end
        if not ok then print("[EditionProbe] Fehler: " .. tostring(err) .. "\n") end
    end)
end)

RegisterKeyBind(Key.F9, function()
    ExecuteInGameThread(function()
        local ok, err = pcall(Probe)
        if not ok then print("[EditionProbe] Fehler: " .. tostring(err) .. "\n") end
    end)
end)

print("[EditionProbe] geladen - F9 = Analyse starten\n")

-- Schlüssel-Dump: nur Name/String-Felder der LocalizeText-Structs (schrittweise, mit flush)
local function ProbeKeys()
    TextLog = io.open("ue4ss/Mods/EditionProbe/keys_out.txt", "w")
    local st = StaticFindObject("/Script/LocalizeSystem.LocalizeText")
    local fields = {}
    st:ForEachProperty(function(p)
        local info = PropType(p)
        if info == "ArrayProperty" then info = info .. "<" .. PropType(p:GetInner()) .. ">" end
        TOut("FIELD " .. PName(p) .. " : " .. info)
        if PropType(p) == "NameProperty" or PropType(p) == "StrProperty" then fields[#fields + 1] = PName(p) end
    end)
    for _, t in ipairs(TextTables) do
        local name = "DA_LocalizeTextData_" .. t
        local asset = StaticFindObject("/Game/Bacchus/Text/" .. name .. "." .. name)
        if asset and asset:IsValid() then
            TOut("## " .. name)
            asset.LocalizeTexts:ForEach(function(_, e)
                local row, parts = e:get(), {}
                for _, f in ipairs(fields) do
                    local ok, v = pcall(function() return row[f]:ToString() end)
                    parts[#parts + 1] = ok and v or "?"
                end
                TOut("  " .. table.concat(parts, " | "))
            end)
        end
    end
    TOut("ENDE")
    TextLog:close(); TextLog = nil
    print("[EditionProbe] Keys geschrieben\n")
end

-- Automatischer Lauf (kein Tastendruck nötig): 20 s nach dem Laden
ExecuteWithDelay(20000, function()
    ExecuteInGameThread(function()
        local ok, err = pcall(ProbeTexts)
        if TextLog then TextLog:close(); TextLog = nil end
        if not ok then print("[EditionProbe] Fehler: " .. tostring(err) .. "\n") return end
        ok, err = pcall(ProbeKeys)
        if TextLog then TextLog:close(); TextLog = nil end
        if not ok then print("[EditionProbe] Fehler: " .. tostring(err) .. "\n") end
    end)
end)
