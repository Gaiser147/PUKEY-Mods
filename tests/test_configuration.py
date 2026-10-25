"""Pure configuration proposals: no disk writes and no Lua execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from manager.configuration import validate_configuration, read_configuration, write_configuration


def definition(fmt="json"):
    specs = [
        {"key": "Speed", "label": "Speed", "type": "number", "default": 2, "min": 1, "max": 10},
        {"key": "Visible", "label": "Visible", "type": "boolean", "default": True},
        {"key": "Mode", "label": "Mode", "type": "enum", "default": "a", "options": ["a", "b"]},
        {"key": "ToggleKey", "label": "Toggle", "type": "key", "default": "F5"},
    ]
    def binding(key):
        return {"path": ["Camera", key]} if fmt == "json" else {"section": "Camera", "key": key} if fmt == "ini" else {"key": key}
    return {"id": "Demo", "files": ["Scripts/main.lua"], "settings": specs,
            "configuration": [{"file": "config." + fmt, "format": fmt, "bindings": {s["key"]: binding(s["key"]) for s in specs}}]}


class ConfigurationTests(unittest.TestCase):
    def test_absent_files_read_defaults_and_generate_valid_files(self):
        for fmt in ("json", "ini", "lua"):
            with self.subTest(fmt=fmt):
                mod = definition(fmt)
                self.assertEqual(read_configuration(mod, {}.get), {"Speed": 2, "Visible": True, "Mode": "a", "ToggleKey": "F5"})
                files = write_configuration(mod, {"Speed": 3}, {}.get)
                self.assertEqual(set(files), {"config." + fmt})
                self.assertEqual(read_configuration(mod, files.get)["Speed"], 3)

    def test_json_keeps_unknown_nested_values_and_uses_defaults_for_missing_keys(self):
        mod = definition()
        original = b'{"Camera":{"Speed":4,"foreign":[1,{"x":null}]},"Other":42}'
        files = {"config.json": original}
        self.assertEqual(read_configuration(mod, files.get)["Speed"], 4)
        changed = write_configuration(mod, {"Speed": 8}, files.get)
        self.assertEqual(json.loads(changed["config.json"]), {"Camera": {"Speed": 8, "Visible": True, "Mode": "a", "ToggleKey": "F5", "foreign": [1, {"x": None}]}, "Other": 42})
        self.assertEqual(files["config.json"], original)

    def test_writes_merge_existing_values_and_omit_unchanged_files(self):
        mod = definition()
        initial = write_configuration(mod, {"Speed": 4}, {}.get)
        self.assertEqual(write_configuration(mod, {}, initial.get), {})
        self.assertEqual(read_configuration(mod, write_configuration(mod, {"Mode": "b"}, initial.get).get)["Speed"], 4)

    def test_json_rejects_duplicate_keys_scalar_crossings_and_nonfinite(self):
        for content in (b'{"Camera":1}', b'{"Camera":{"Speed":2,"Speed":3}}', b'{"x":NaN}', b'{"x":1e999}', b'[]'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                write_configuration(definition(), {"Speed": 3}, {"config.json": content}.get)

    def test_invalid_existing_value_cannot_be_overwritten(self):
        for fmt, content in (("json", b'{"Camera":{"Speed":"bad"}}'), ("ini", b'[Camera]\nSpeed=bad\n'), ("lua", b'return {Speed="bad"}')):
            files = {"config." + fmt: content}
            with self.subTest(fmt=fmt), self.assertRaises(ValueError):
                write_configuration(definition(fmt), {"Speed": 3}, files.get)
            self.assertEqual(files["config." + fmt], content)

    def test_ini_targeted_updates_preserve_comments_spelling_and_other_values(self):
        mod = definition("ini")
        content = b'; personal settings\r\n[cAmErA]\r\n  sPeEd = 4 ; movement\r\nVisible=FALSE\r\nMode=b\r\nToggleKey=F8\r\nForeign = %(Speed)s\r\n\r\n[Other]\r\nValue = untouched\r\n'
        files = {"config.ini": content}
        self.assertFalse(read_configuration(mod, files.get)["Visible"])
        changed = write_configuration(mod, {"Speed": 5}, files.get)["config.ini"]
        self.assertEqual(changed, content.replace(b'4 ; movement', b'5 ; movement'))

    def test_ini_rejects_ambiguous_multiline_and_unsupported_syntax(self):
        for content in (b'[Camera]\nSpeed=2\nSPEED=3\n', b'[Camera]\nSpeed=2\n[camera]\nVisible=true\n', b'[Camera]\nMode=a\n continuation\n', b'[Camera]\nSpeed:2\n', b'[DEFAULT]\nSpeed=2\n', b'Speed=2\n'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                read_configuration(definition("ini"), {"config.ini": content}.get)

    def test_lua_literals_comments_escapes_and_unknown_fields_roundtrip(self):
        mod = definition("lua")
        content = b'-- personal\nreturn { Speed=4, Visible=false; ["Mode"]="b", ToggleKey="F8", ["foreign\\032key"]="hello\\010world", } -- end\n'
        files = {"config.lua": content}
        self.assertEqual(read_configuration(mod, files.get)["Speed"], 4)
        changed = write_configuration(mod, {"Speed": 5}, files.get)
        self.assertIn(b'foreign key', changed["config.lua"])
        self.assertIn(b'hello\\010world', changed["config.lua"])
        self.assertEqual(read_configuration(mod, changed.get)["Speed"], 5)

    def test_lua_never_executes_arbitrary_expressions(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "executed"
            source = ('return {Speed=(function() io.open(%s,"w"):write("bad"); return 3 end)()}' % json.dumps(str(marker))).encode()
            for content in (source, b'return {Speed=1+2}', b'local x=3; return {Speed=x}', b'return {Speed=2, foreign={nested=true}}', b'return {Speed=2, Speed=3}', b'return {Speed=2}; os.execute("bad")'):
                with self.subTest(content=content), self.assertRaisesRegex(ValueError, "Lua|literal"):
                    write_configuration(definition("lua"), {"Speed": 3}, {"config.lua": content}.get)
            self.assertFalse(marker.exists())

    def test_multiple_targets_and_validation_before_any_proposal(self):
        mod = definition()
        first = mod["configuration"][0]
        first["bindings"] = {"Speed": {"path": ["Camera", "Speed"]}}
        mod["configuration"].append({"file": "options.lua", "format": "lua", "bindings": {key: {"key": key} for key in ("Visible", "Mode", "ToggleKey")}})
        files = write_configuration(mod, {"Visible": False}, {}.get)
        self.assertEqual(set(files), {"config.json", "options.lua"})
        self.assertFalse(read_configuration(mod, files.get)["Visible"])
        files["options.lua"] = b'print("unsafe")'
        with self.assertRaises(ValueError):
            write_configuration(mod, {"Speed": 5}, files.get)

    def test_string_roundtrip_is_literal_and_ini_injection_is_rejected(self):
        for fmt in ("json", "ini", "lua"):
            mod = definition(fmt)
            mod["settings"].append({"key": "Text", "label": "Text", "type": "string", "default": ""})
            binding = {"path": ["Camera", "Text"]} if fmt == "json" else {"section": "Camera", "key": "Text"} if fmt == "ini" else {"key": "Text"}
            mod["configuration"][0]["bindings"]["Text"] = binding
            text = 'quotes " ; # \\ ä %value%'
            with self.subTest(fmt=fmt):
                files = write_configuration(mod, {"Text": text}, {}.get)
                self.assertEqual(read_configuration(mod, files.get)["Text"], text)
                for bad in ('one\n[Injected]\nSpeed=9', 'one\rnext', 'nul\x00', 'x' * 4097):
                    with self.assertRaises(ValueError):
                        write_configuration(mod, {"Text": bad}, {}.get)

    def test_manifest_rejects_unsafe_duplicate_missing_and_overlapping_bindings(self):
        cases = []
        mod = definition(); mod["configuration"][0]["file"] = "../config.json"; cases.append(mod)
        mod = definition(); mod["configuration"][0]["file"] = "Scripts/main.lua"; mod["configuration"][0]["format"] = "lua"; cases.append(mod)
        mod = definition(); mod["files"].append("config.json"); cases.append(mod)
        mod = definition(); mod["configuration"].append(copy.deepcopy(mod["configuration"][0])); cases.append(mod)
        mod = definition(); mod["configuration"][0]["bindings"].pop("Speed"); cases.append(mod)
        mod = definition(); mod["configuration"][0]["bindings"]["Missing"] = {"path": ["x"]}; cases.append(mod)
        mod = definition(); mod["configuration"][0]["bindings"]["Speed"] = {"path": []}; cases.append(mod)
        mod = definition(); mod["configuration"][0]["bindings"]["Speed"] = {"path": ["Camera"]}; cases.append(mod)
        mod = definition(); mod["configuration"][0]["bindings"]["Speed"] = {"path": ["Camera", "Visible"]}; cases.append(mod)
        mod = definition("ini"); mod["configuration"][0]["bindings"]["Speed"]["section"] = "bad\n[Injected]"; cases.append(mod)
        mod = definition("lua"); mod["configuration"][0]["bindings"]["Speed"]["key"] = ""; cases.append(mod)
        for mod in cases:
            with self.subTest(mod=mod), self.assertRaises(ValueError):
                validate_configuration(mod)

    def test_config_targets_may_be_declared_separate_defaults(self):
        mod = definition()
        mod["default_files"] = ["config.json"]
        validate_configuration(mod)


class ConfigurationBoundaryTests(unittest.TestCase):
    def test_numeric_overflow_is_an_actionable_error(self):
        huge = b'9' * 400
        for fmt, content in (("json", b'{"Camera":{"Speed":' + huge + b'}}'), ("ini", b'[Camera]\nSpeed=' + huge + b'\n'), ("lua", b'return {Speed=' + huge + b'}')):
            with self.subTest(fmt=fmt), self.assertRaises(ValueError):
                write_configuration(definition(fmt), {"Speed": 3}, {"config." + fmt: content}.get)

    def test_entrypoint_cannot_be_a_personal_configuration_target(self):
        mod = definition("lua")
        mod["entrypoints"] = [{"type": "lua", "path": "config.lua"}]
        with self.assertRaises(ValueError):
            validate_configuration(mod)

    def test_ini_rejects_nonstandard_line_separators_before_rewriting(self):
        data = '[Camera]\nSpeed=2\u2028Visible=false\n'.encode()
        with self.assertRaises(ValueError):
            write_configuration(definition("ini"), {"Speed": 3}, {"config.ini": data}.get)

    def test_ini_update_preserves_utf8_bom(self):
        data = b'\xef\xbb\xbf; retained\r\n[Camera]\r\nSpeed=2\r\nVisible=true\r\nMode=a\r\nToggleKey=F5\r\n'
        files = {'config.ini': data}
        self.assertEqual(write_configuration(definition('ini'), {}, files.get), {})
        self.assertEqual(write_configuration(definition('ini'), {'Speed': 3}, files.get)['config.ini'], data.replace(b'Speed=2', b'Speed=3'))

    def test_ini_binding_rejects_unicode_line_separator_injection(self):
        mod = definition('ini')
        mod['configuration'][0]['bindings']['Speed']['section'] = 'Camera\u2028Other'
        with self.assertRaises(ValueError):
            validate_configuration(mod)


if __name__ == "__main__":
    unittest.main()
