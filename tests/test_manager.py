"""Safety and lifecycle checks run against disposable game installations only."""
import io
import json
import os
import subprocess
import sys
import stat
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
import warnings
from unittest.mock import Mock, patch
import zipfile

from manager.catalog import Snapshot, read_archive, validate_settings, lua_settings, load_cached, fetch_latest
from manager.platforms import game_directory, games_from_steam_roots, game_running, WIN64_PART
from manager.service import Manager


def definition():
    return {"id": "Demo", "name": "Demo", "version": "1.0", "description": "Example",
            "controls": "F5", "files": ["Scripts/main.lua", "README.md"],
            "settings": [{"key": "Mode", "label": "Mode", "type": "enum", "default": "a", "options": ["a", "b"]},
                         {"key": "Speed", "label": "Speed", "type": "number", "default": 2, "min": 1, "max": 10},
                         {"key": "ToggleKey", "label": "Key", "type": "key", "default": "F5"},
                         {"key": "Visible", "label": "Visible", "type": "boolean", "default": True}],
            "images": [{"file": "bar.png", "label": "Image", "width": 2, "height": 3, "background": "transparent", "scale": 100, "top": 0}],
            "video_list": "VIDEOS.txt", "video_folder": "Movies"}


def snapshot(mod=None, code=b"first", revision="a" * 40):
    mod = mod or definition()
    return Snapshot(revision, {"catalog.json": json.dumps({"schema_version": 1, "mods": [mod]}).encode(),
                               "Mods/Demo/Scripts/main.lua": code, "Mods/Demo/README.md": b"Read me"})


def archive(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        for name, data in entries:
            info = zipfile.ZipInfo("placeholder")
            info.filename = name
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr(info, data)
    return output.getvalue()


class CatalogTests(unittest.TestCase):
    def test_snapshot_has_validated_mods(self):
        self.assertEqual(snapshot().mods[0]["id"], "Demo")

    def test_rejects_unsafe_catalogue(self):
        for key, value in [("id", "../Demo"), ("files", ["../main.lua"]),
                           ("files", ["Scripts/main.lua", "settings.lua"]),
                           ("files", ["Scripts/main.lua", "README.md", "readme.md"]),
                           ("video_folder", "../Movies")]:
            with self.subTest(key=key, value=value):
                mod = definition(); mod[key] = value
                with self.assertRaises(ValueError): snapshot(mod)

    def test_missing_payload_and_schema_rejected(self):
        with self.assertRaises(ValueError): Snapshot("a", {"catalog.json": b'{"schema_version":2,"mods":[]}'})
        with self.assertRaises(ValueError): Snapshot("a", {"catalog.json": json.dumps({"schema_version": 1, "mods": [definition()]}).encode()})

    def test_archive_rejects_paths_collisions_and_symlinks(self):
        for entries in [[("repo/../bad", b"x")], [("/bad", b"x")], [("C:/bad", b"x")],
                        [("repo\\bad", b"x")], [("repo/A", b"x"), ("repo/a", b"y")],
                        [("repo/x", b"x"), ("repo/x", b"y")]]:
            with self.subTest(entries=entries), self.assertRaises(ValueError): read_archive(archive(entries))
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as z:
            entry = zipfile.ZipInfo("repo/link"); entry.create_system = 3; entry.external_attr = 0o120777 << 16
            z.writestr(entry, "outside")
        with self.assertRaises(ValueError): read_archive(output.getvalue())

    def test_archive_strips_single_root(self):
        self.assertEqual(read_archive(archive([("repo/a", b"x")])), {"a": b"x"})

    def test_archive_rejects_directory_alias_and_expansion_limits(self):
        with self.assertRaises(ValueError): read_archive(archive([("repo/A/x", b"x"), ("repo/a/y", b"y")]))
        with patch("manager.catalog.MAX_EXPANDED", 1), self.assertRaises(ValueError): read_archive(archive([("repo/x", b"xx")]))

    def test_from_directory_loads_only_declared_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, data in snapshot().files.items():
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            (root / "research.bin").write_bytes(b"private")
            found = Snapshot.from_directory(root)
            self.assertNotIn("research.bin", found.files)

    def test_directory_snapshot_rejects_reparse_attributes_without_path_junction_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, data in snapshot().files.items():
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            real_lstat = os.lstat
            def reparse_lstat(path, *args, **kwargs):
                actual = real_lstat(path, *args, **kwargs)
                if Path(path) == root / "Mods/Demo":
                    return SimpleNamespace(st_mode=actual.st_mode, st_file_attributes=0x400)
                return actual
            with patch("manager.catalog.os.lstat", side_effect=reparse_lstat), patch.object(Path, "is_junction", None, create=True):
                with self.assertRaises(ValueError): Snapshot.from_directory(root)

    def test_settings_are_typed_and_lua_is_escaped(self):
        mod = definition()
        self.assertEqual(validate_settings(mod, {})["Speed"], 2)
        for values in [{"Speed": True}, {"Speed": float("nan")}, {"Speed": 100}, {"Mode": "c"},
                       {"ToggleKey": "ESCAPE"}, {"Visible": 1}, {"Unknown": 2}]:
            with self.subTest(values=values), self.assertRaises(ValueError): validate_settings(mod, values)
        rendered = lua_settings({"Text": '\"\\\n\x00', "Flag": True, "Value": 2}).decode()
        self.assertIn('\\000', rendered)
        self.assertIn('["Flag"] = true', rendered)
        with self.assertRaises(ValueError): lua_settings({"Value": float("inf")})

    def test_fetch_pins_archive_to_commit_and_revalidates_cache(self):
        snap = snapshot()
        data = archive([("repo/" + name, payload) for name, payload in snap.files.items()])
        with tempfile.TemporaryDirectory() as tmp, patch("manager.catalog.download", side_effect=[b'{"sha":"' + b"a" * 40 + b'"}', data]) as fetch:
            cached = fetch_latest(Path(tmp))
            self.assertEqual(cached.files, snap.files)
            self.assertTrue(fetch.call_args_list[1].args[0].endswith("/" + "a" * 40))
            self.assertEqual(load_cached(Path(tmp)).revision, "a" * 40)
            (Path(tmp) / "snapshot.json").write_text('{"revision":"bad","archive":"00"}')
            with self.assertRaises(ValueError): load_cached(Path(tmp))

    def test_rejects_unknown_features_and_protected_media_targets(self):
        for change in [lambda m: m.update(features=["execute_script"]),
                       lambda m: m["images"][0].update(file="settings.lua"),
                       lambda m: m.update(video_folder="Scripts")]:
            mod = definition(); change(mod)
            with self.assertRaises(ValueError): snapshot(mod)

    def test_snapshot_payloads_cannot_be_mutated_after_validation(self):
        snap = snapshot()
        with self.assertRaises(TypeError): snap.files["Mods/Demo/Scripts/main.lua"] = b"changed"
        snap.mods[0]["id"] = "Changed"
        self.assertEqual(snap.mods[0]["id"], "Demo")


class PlatformTests(unittest.TestCase):
    def test_failed_process_detection_fails_closed(self):
        class ProcessError(Exception): pass
        module = SimpleNamespace(Error=ProcessError, AccessDenied=ProcessError, NoSuchProcess=ProcessError,
                                 process_iter=Mock(side_effect=ProcessError("Cannot enumerate processes")))
        with patch.dict(sys.modules, {"psutil": module}):
            self.assertTrue(game_running())

    def test_game_root_normalizes_supported_folder_choices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); win = root / WIN64_PART; win.mkdir(parents=True)
            with self.assertRaises(ValueError): game_directory(root)
            (win / "PUKEY_GODDESS_SHOT_TRICK-Win64-Shipping.exe").touch()
            for path in [root, root / "PUKEY_GODDESS_SHOT_TRICK", win]:
                self.assertEqual(game_directory(path), root.resolve())

    def test_steam_manifest_and_library_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "steam"; lib = Path(tmp) / "library"
            (root / "steamapps").mkdir(parents=True); (lib / "steamapps").mkdir(parents=True)
            (root / "steamapps/libraryfolders.vdf").write_text('"libraryfolders" { "1" { "path" "' + str(lib).replace('\\', '\\\\') + '" } }')
            (lib / "steamapps/appmanifest_5253020.acf").write_text('"AppState" { "installdir" "Game" }')
            game = lib / "steamapps/common/Game"; win = game / WIN64_PART; win.mkdir(parents=True)
            (win / "PUKEY_GODDESS_SHOT_TRICK-Win64-Shipping.exe").touch()
            self.assertEqual(games_from_steam_roots([root]), [game.resolve()])


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.win = self.root / WIN64_PART; self.win.mkdir(parents=True)
        (self.win / "PUKEY_GODDESS_SHOT_TRICK-Win64-Shipping.exe").touch()
        self.guard = patch("manager.service.game_running", return_value=False); self.guard.start(); self.addCleanup(self.guard.stop)
        self.manager = Manager(self.root, snapshot()); self.mod = self.manager.snapshot.mods[0]
        self.folder = self.manager.mods_dir / "Demo"

    def test_install_update_remove_preserves_personal_data(self):
        self.manager.install(self.mod)
        self.assertTrue(self.manager.status(self.mod)["enabled"])
        self.manager.write_user_file(self.mod, "bar.png", b"personal")
        (self.folder / "bookmarks.json").write_text("{}")
        self.manager.save_settings(self.mod, {"Speed": 5})
        self.manager.snapshot = snapshot(code=b"second", revision="b" * 40)
        self.assertTrue(self.manager.status(self.mod)["update"])
        self.manager.install(self.mod)
        self.assertEqual((self.folder / "Scripts/main.lua").read_bytes(), b"second")
        self.assertEqual((self.folder / "bar.png").read_bytes(), b"personal")
        self.manager.remove(self.mod)
        self.assertFalse(self.manager.status(self.mod)["installed"])
        for name in ["bar.png", "settings.json", "settings.lua", "bookmarks.json"]:
            self.assertTrue((self.folder / name).exists(), name)

    def test_manual_install_adoption_keeps_unknown_files(self):
        (self.folder / "Scripts").mkdir(parents=True)
        (self.folder / "Scripts/main.lua").write_bytes(b"manual")
        (self.folder / "Scripts/custom.lua").write_bytes(b"custom")
        self.assertTrue(self.manager.status(self.mod)["installed"])
        self.assertFalse(self.manager.status(self.mod)["managed"])
        self.manager.install(self.mod); self.manager.remove(self.mod)
        self.assertEqual((self.folder / "Scripts/custom.lua").read_bytes(), b"custom")
        self.assertTrue(any(p.read_bytes() == b"manual" for p in (self.win / "ue4ss/.pukey-manager/backups").rglob("*") if p.is_file()))

    def test_json_alone_does_not_activate_manual_mod(self):
        (self.folder / "Scripts").mkdir(parents=True)
        (self.folder / "Scripts/main.lua").write_bytes(b"manual")
        (self.manager.mods_dir / "mods.json").write_text('[{"mod_name":"Demo","mod_enabled":true}]')
        self.assertFalse(self.manager.status(self.mod)["enabled"])
        self.manager.install(self.mod)
        self.assertFalse(self.manager.status(self.mod)["enabled"])

    def test_txt_activation_takes_precedence_over_json_without_marker(self):
        (self.folder / "Scripts").mkdir(parents=True)
        (self.folder / "Scripts/main.lua").write_bytes(b"manual")
        for text_enabled, json_enabled in [(True, False), (False, True)]:
            with self.subTest(text_enabled=text_enabled, json_enabled=json_enabled):
                (self.manager.mods_dir / "mods.txt").write_text("Demo : %d\n" % text_enabled)
                (self.manager.mods_dir / "mods.json").write_text(json.dumps([{"mod_name": "Demo", "mod_enabled": json_enabled}]))
                self.assertEqual(self.manager.status(self.mod)["enabled"], text_enabled)

    def test_manual_marker_activation_overrides_disabled_configuration_on_adoption(self):
        (self.folder / "Scripts").mkdir(parents=True)
        (self.folder / "Scripts/main.lua").write_bytes(b"manual")
        (self.folder / "enabled.txt").touch()
        (self.manager.mods_dir / "mods.txt").write_text("Demo : 0\n")
        (self.manager.mods_dir / "mods.json").write_text('[{"mod_name":"Demo","mod_enabled":false}]')
        self.assertTrue(self.manager.status(self.mod)["enabled"])
        self.manager.install(self.mod)
        self.assertTrue(self.manager.status(self.mod)["enabled"])
        self.assertTrue((self.folder / "enabled.txt").exists())
        self.assertIn("Demo : 1", (self.manager.mods_dir / "mods.txt").read_text())

    def test_activation_updates_txt_json_and_markers(self):
        mods = self.manager.mods_dir; mods.mkdir(parents=True)
        (mods / "mods.txt").write_text("Demo : 1\nConsoleEnablerMod : 1\nOther : 1\n")
        (mods / "mods.json").write_text('[{"mod_name":"Demo","mod_enabled":true}]')
        bad = mods / "ConsoleEnablerMod"; bad.mkdir(); (bad / "enabled.txt").touch()
        self.manager.install(self.mod); self.manager.set_enabled(self.mod, False)
        self.assertFalse((self.folder / "enabled.txt").exists())
        self.assertFalse((bad / "enabled.txt").exists())
        self.assertIn("Demo : 0", (mods / "mods.txt").read_text())
        self.assertIn("ConsoleEnablerMod : 0", (mods / "mods.txt").read_text())
        entries = json.loads((mods / "mods.json").read_text())
        self.assertIsInstance(entries, list)
        self.assertFalse(next(e for e in entries if e["mod_name"] == "Demo")["mod_enabled"])

    def test_empty_json_remains_array_and_malformed_aborts(self):
        self.manager.mods_dir.mkdir(parents=True)
        path = self.manager.mods_dir / "mods.json"; path.write_text("[]")
        self.manager.install(self.mod)
        self.assertIsInstance(json.loads(path.read_text()), list)
        path.write_text('{broken')
        with self.assertRaises(ValueError): self.manager.set_enabled(self.mod, False)
        self.assertTrue((self.folder / "enabled.txt").exists())

    def test_failed_transaction_restores_previous_files(self):
        self.manager.install(self.mod)
        self.manager.snapshot = snapshot(code=b"second")
        import manager.service as service
        replace = service.os.replace
        attempts = [0]
        def fail_once(source, dest):
            attempts[0] += 1
            if attempts[0] == 2: raise OSError("disk failure")
            return replace(source, dest)
        with patch("manager.service.os.replace", side_effect=fail_once), self.assertRaises(OSError):
            self.manager.install(self.mod)
        self.assertEqual((self.folder / "Scripts/main.lua").read_bytes(), b"first")

    def test_running_game_blocks_every_write(self):
        with patch("manager.service.game_running", return_value=True):
            for action in [lambda: self.manager.install(self.mod), lambda: self.manager.set_enabled(self.mod, True),
                           lambda: self.manager.remove(self.mod), lambda: self.manager.save_settings(self.mod, {}),
                           lambda: self.manager.write_user_file(self.mod, "bar.png", b"x"), lambda: self.manager.install_loader()]:
                with self.assertRaises(RuntimeError): action()

    def test_media_cannot_overwrite_code_and_replacements_keep_backups(self):
        self.manager.install(self.mod)
        for name in ["../outside", "Scripts/main.lua", "Movies/../Scripts/main.lua", "Movies/unknown.mp4"]:
            with self.subTest(name=name), self.assertRaises(ValueError): self.manager.write_user_file(self.mod, name, b"bad")
        self.manager.write_user_file(self.mod, "bar.png", b"one")
        self.manager.write_user_file(self.mod, "bar.png", b"two")
        self.assertTrue(any(p.read_bytes() == b"one" for p in (self.win / "ue4ss/.pukey-manager/backups").rglob("*") if p.is_file()))

    def test_restore_original_backs_up_media_and_rejects_code(self):
        self.manager.install(self.mod)
        self.manager.write_user_file(self.mod, "bar.png", b"personal")
        with self.assertRaises(ValueError): self.manager.remove_user_file(self.mod, "Scripts/main.lua")
        self.manager.remove_user_file(self.mod, "bar.png")
        self.assertFalse((self.folder / "bar.png").exists())
        self.assertTrue(any(p.read_bytes() == b"personal" for p in (self.win / "ue4ss/.pukey-manager/backups").rglob("*") if p.is_file()))

    def test_disabled_update_and_modified_owned_file_preservation(self):
        self.manager.install(self.mod); self.manager.set_enabled(self.mod, False)
        self.manager.snapshot = snapshot(code=b"second")
        self.manager.install(self.mod)
        self.assertFalse(self.manager.status(self.mod)["enabled"])
        (self.folder / "README.md").write_bytes(b"personal edits")
        self.manager.remove(self.mod)
        self.assertEqual((self.folder / "README.md").read_bytes(), b"personal edits")

    @unittest.skipUnless(os.name == "nt", "Windows junction fixture")
    def test_windows_junction_redirect_refused(self):
        target = self.root / "outside"; target.mkdir()
        self.manager.mods_dir.mkdir(parents=True)
        script = 'New-Item -ItemType Junction -Path $env:PUKEY_TEST_LINK -Target $env:PUKEY_TEST_TARGET | Out-Null'
        environment = dict(os.environ, PUKEY_TEST_LINK=str(self.folder), PUKEY_TEST_TARGET=str(target))
        subprocess.run(["powershell", "-NoProfile", "-Command", script], env=environment, check=True, capture_output=True)
        self.addCleanup(lambda: self.folder.rmdir() if self.folder.exists() else None)
        with self.assertRaises(ValueError): self.manager.install(self.mod)
        self.assertEqual(list(target.iterdir()), [])

    def test_reparse_write_refused_without_path_junction_api(self):
        (self.folder / "Scripts").mkdir(parents=True)
        real_lstat = os.lstat
        def reparse_lstat(path, *args, **kwargs):
            actual = real_lstat(path, *args, **kwargs)
            if Path(path) == self.folder:
                return SimpleNamespace(st_mode=actual.st_mode, st_file_attributes=0x400)
            return actual
        with patch("manager.catalog.os.lstat", side_effect=reparse_lstat), patch.object(Path, "is_junction", None, create=True):
            with self.assertRaises(ValueError): self.manager.install(self.mod)
        self.assertFalse((self.folder / "Scripts/main.lua").exists())

    def test_symlink_redirect_refused(self):
        target = self.root / "outside"; target.mkdir()
        self.manager.mods_dir.mkdir(parents=True)
        try: os.symlink(target, self.folder, target_is_directory=True)
        except OSError: self.skipTest("symlink creation not permitted")
        with self.assertRaises(ValueError): self.manager.install(self.mod)
        self.assertEqual(list(target.iterdir()), [])

    def test_malformed_settings_are_not_overwritten(self):
        self.manager.install(self.mod)
        path = self.folder / "settings.json"; path.write_text("[]")
        with self.assertRaises(ValueError): self.manager.save_settings(self.mod, {})
        self.assertEqual(path.read_text(), "[]")

    def test_loader_only_uses_official_validated_archive(self):
        release = {"assets": [{"name": "UE4SS_v3.0.zip", "browser_download_url": "https://github.com/UE4SS-RE/RE-UE4SS/releases/download/experimental-latest/UE4SS_v3.0.zip"}]}
        data = archive([("ue4ss/UE4SS.dll", b"loader"), ("dwmapi.dll", b"proxy"),
                        ("ue4ss/Mods/ConsoleEnablerMod/enabled.txt", b""), ("ue4ss/settings.ini", b"stock")])
        config = self.win / "ue4ss/settings.ini"; config.parent.mkdir(); config.write_bytes(b"custom")
        with patch("manager.service.download", side_effect=[json.dumps(release).encode(), data]): self.manager.install_loader()
        self.assertEqual((self.win / "ue4ss/UE4SS.dll").read_bytes(), b"loader")
        self.assertEqual(config.read_bytes(), b"custom")
        self.assertFalse((self.manager.mods_dir / "ConsoleEnablerMod/enabled.txt").exists())
        release["assets"][0]["browser_download_url"] = "https://example.com/evil.zip"
        with patch("manager.service.download", return_value=json.dumps(release).encode()), self.assertRaises(ValueError): self.manager.install_loader()

    def test_loader_missing_proxy_aborts_without_writes(self):
        release = {"assets": [{"name": "UE4SS_v3.zip", "browser_download_url": "https://github.com/UE4SS-RE/RE-UE4SS/releases/download/experimental-latest/UE4SS_v3.zip"}]}
        with patch("manager.service.download", side_effect=[json.dumps(release).encode(), archive([("ue4ss/UE4SS.dll", b"x")])]), self.assertRaises(ValueError):
            self.manager.install_loader()
        self.assertFalse((self.win / "ue4ss/UE4SS.dll").exists())


if __name__ == "__main__": unittest.main()
