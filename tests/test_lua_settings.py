import json
from pathlib import Path
import unittest

try:
    from lupa import LuaRuntime
except ImportError:
    LuaRuntime = None

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(LuaRuntime is None, "Lupa is required to execute Lua configuration tests")
class LuaSettingsTests(unittest.TestCase):
    def load_mod(self, mod, settings=None, broken=False):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
            Key = setmetatable({}, {__index=function(t, k)
                local n = 1000; for _ in pairs(t) do n = n + 1 end
                rawset(t, k, n); return n
            end})
            ModifierKey = {CONTROL=1}
            package.preload.UEHelpers = function() return {} end
            bindings = {}; loops = {}; read_paths = {}
            function RegisterKeyBind(key, ...) table.insert(bindings, {key=key,args={...}}) end
            function LoopAsync(ms, cb) table.insert(loops, {ms=ms,cb=cb}) end
            function ExecuteInGameThread(cb) cb() end
            io.open = function() return nil end
            print = function() end
        ''')
        lua.globals().override = lua.table_from(settings) if isinstance(settings, dict) else settings
        lua.globals().missing = settings is None
        lua.globals().broken = broken
        lua.execute('''function dofile(path)
            table.insert(read_paths, path)
            if missing or broken then error("unreadable settings") end
            return override
        end''')
        source = (ROOT / "Mods" / mod / "Scripts" / "main.lua").read_text(encoding="utf-8-sig")
        config, targets, state = lua.execute(source + "\nreturn Config, Targets, State")
        return lua, config, targets, state

    def test_missing_and_invalid_settings_keep_default_bindings_and_intervals(self):
        for mod, key, default, interval in (("FreeCam", "ToggleKey", "F5", 8), ("LightTools", "FloodKey", "F1", 16), ("FamSwap", "ToggleKey", "F8", 200), ("MovieSwap", "ReloadKey", "F11", 2000)):
            for settings, broken in ((None, False), ({key: "F12"}, True), ({key: 32, "TickMs": -1, "ScanIntervalMs": -1}, False)):
                with self.subTest(mod=mod, settings=settings, broken=broken):
                    lua, config, _, _ = self.load_mod(mod, settings, broken)
                    self.assertEqual(config[key], lua.globals().Key[default])
                    self.assertEqual(config["ScanIntervalMs" if mod == "MovieSwap" else "TickMs"], interval)
                    self.assertEqual(lua.globals().bindings[1].key, lua.globals().Key[default])

    def test_override_keys_and_loop_intervals_activate(self):
        for mod, field in (("FreeCam", "ToggleKey"), ("LightTools", "FloodKey"), ("FamSwap", "ToggleKey"), ("MovieSwap", "ReloadKey")):
            with self.subTest(mod=mod):
                timing = "ScanIntervalMs" if mod == "MovieSwap" else "TickMs"
                lua, config, _, _ = self.load_mod(mod, {field: "F12", timing: 500})
                self.assertEqual(lua.globals().read_paths[1], "ue4ss/Mods/" + mod + "/settings.lua")
                self.assertEqual(lua.globals().bindings[1].key, lua.globals().Key.F12)
                self.assertEqual(config[timing], 500)
                if mod in ("FamSwap", "MovieSwap"):
                    self.assertEqual(lua.globals().loops[1].ms, 500)

    def test_freecam_initial_speed_and_reset_follow_configuration(self):
        lua, config, _, state = self.load_mod("FreeCam", {"DefaultSpeed": 1234, "Mode": "viewtarget", "SpeedResetKey": "F12"})
        self.assertEqual(state.Speed, 1234)
        self.assertEqual(config.Mode, "viewtarget")
        state.Speed = 42
        for binding in lua.globals().bindings.values():
            if binding.key == lua.globals().Key.F12:
                binding.args[1]()
        self.assertEqual(state.Speed, 1234)

    def test_famswap_game_mode_and_flipbook_overrides_reach_target(self):
        _, config, targets, _ = self.load_mod("FamSwap", {"GameMode": "idle", "HideFlipbooks": False})
        self.assertEqual(config.GameMode, "idle")
        self.assertEqual(targets[2].Mode, "idle")
        self.assertFalse(targets[2].HideFlipbooks)

    def test_invalid_scalar_values_are_ignored(self):
        _, config, _, state = self.load_mod("FreeCam", {"DefaultSpeed": float("nan"), "BoostFactor": float("inf"), "Mode": "bad", "MouseSens": "oops", "PositionsFile": "elsewhere", "Unknown": True})
        self.assertEqual(state.Speed, 400)
        self.assertEqual(config.BoostFactor, 4)
        self.assertEqual(config.Mode, "possess")
        self.assertEqual(config.MouseSens, 0.15)
        self.assertEqual(config.PositionsFile, "ue4ss/Mods/FreeCam/positions.txt")
        self.assertIsNone(config.Unknown)

    def test_non_table_settings_and_unsupported_key_names_keep_defaults(self):
        for settings in ("invalid", False, 1, {"ToggleKey": "ADD"}, {"ToggleKey": "NotAKey"}):
            with self.subTest(settings=settings):
                lua, config, _, _ = self.load_mod("FamSwap", settings)
                self.assertEqual(config.ToggleKey, lua.globals().Key.F8)

    def test_every_catalog_setting_matches_defaults_and_can_activate(self):
        catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
        for mod in catalog["mods"]:
            lua, defaults, _, _ = self.load_mod(mod["id"])
            overrides = {}
            for entry in mod["settings"]:
                with self.subTest(mod=mod["id"], setting=entry["key"]):
                    expected = lua.globals().Key[entry["default"]] if entry["type"] == "key" else entry["default"]
                    self.assertEqual(defaults[entry["key"]], expected)
                if entry["type"] == "key":
                    value = "F12"
                elif entry["type"] == "boolean":
                    value = not entry["default"]
                elif entry["type"] == "enum":
                    value = entry["options"][-1]
                else:
                    value = entry["max"]
                overrides[entry["key"]] = value
            lua, configured, _, _ = self.load_mod(mod["id"], overrides)
            for entry in mod["settings"]:
                with self.subTest(mod=mod["id"], configured=entry["key"]):
                    value = overrides[entry["key"]]
                    self.assertEqual(configured[entry["key"]], lua.globals().Key[value] if entry["type"] == "key" else value)


if __name__ == "__main__":
    unittest.main()
