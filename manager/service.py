"""Transactional installation service. All mutations target the selected fake or real game root."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from .catalog import download, is_redirect, lua_settings, parse_json, read_archive, safe_path, validate_settings
from .platforms import WIN64_PART, game_directory, game_running

CRASH_PRONE = ("CheatManagerEnablerMod", "ConsoleEnablerMod", "ConsoleCommandsMod")
LOADER_RELEASE = "https://api.github.com/repos/UE4SS-RE/RE-UE4SS/releases/tags/experimental-latest"


def _json(data):
    return (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest(data):
    return hashlib.sha256(data).hexdigest()


class Manager:
    def __init__(self, game_root, snapshot=None):
        self.game_root = game_directory(game_root)
        self.win64 = self.game_root / WIN64_PART
        self.mods_dir = self.win64 / "ue4ss/Mods"
        self.state_dir = self.win64 / "ue4ss/.pukey-manager"
        self.state_file = self.state_dir / "manifest.json"
        self.snapshot = snapshot

    def _guard(self):
        if game_running(): raise RuntimeError("Close the game before changing mods. Process detection must be available.")

    def _safe(self, path):
        path = Path(path).absolute()
        try: path.relative_to(self.win64)
        except ValueError as exc: raise ValueError("Write escapes the selected installation") from exc
        for part in [path] + list(path.parents):
            if is_redirect(part):
                raise ValueError("Refusing symbolic link or junction: " + str(part))
            if part == self.game_root: break
        return path

    def _read(self, path):
        path = self._safe(path)
        if not path.exists(): return None
        if not path.is_file(): raise ValueError("Expected a file: " + str(path))
        return path.read_bytes()

    def _state(self):
        raw = self._read(self.state_file)
        if raw is None: return {"schema_version": 1, "mods": {}, "loader": {"files": {}}}
        state = parse_json(raw)
        if not isinstance(state, dict) or state.get("schema_version") != 1 or not isinstance(state.get("mods"), dict):
            raise ValueError("Invalid manager manifest")
        for key, entry in list(state["mods"].items()) + [("loader", state.get("loader", {"files": {}}))]:
            if key != "loader" and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", key): raise ValueError("Invalid managed mod ID")
            if not isinstance(entry, dict) or not isinstance(entry.get("files"), dict): raise ValueError("Invalid ownership manifest")
            for name, digest in entry["files"].items():
                safe_path(name)
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest): raise ValueError("Invalid file hash")
        return state

    def _mod(self, mod):
        if isinstance(mod, str):
            if self.snapshot is None: raise ValueError("Load a catalogue first")
            matches = [entry for entry in self.snapshot.mods if entry["id"] == mod]
        elif isinstance(mod, dict):
            matches = [entry for entry in self.snapshot.mods if entry["id"] == mod.get("id")] if self.snapshot else []
        else: matches = []
        if len(matches) != 1: raise ValueError("Mod is not in the current validated catalogue")
        return matches[0]

    def _transaction(self, changes):
        """Stage complete files; preserve durable originals and roll back changed paths on failure."""
        self._guard()
        previous = {}
        for path, data in changes.items():
            self._safe(path)
            if data is not None and not isinstance(data, bytes): raise TypeError("Transaction payload must be bytes")
            previous[path] = self._read(path)
        changes = {p: data for p, data in changes.items() if data != previous[p]}
        if not changes: return
        backup_root = self._safe(self.state_dir / "backups" / uuid.uuid4().hex)
        staged = {}; changed = []; created_dirs = []
        def mkdir(path):
            missing = []; cursor = path
            while not cursor.exists(): missing.append(cursor); cursor = cursor.parent
            for item in reversed(missing):
                self._safe(item); item.mkdir(); created_dirs.append(item)
        try:
            for path in changes:
                if previous[path] is not None:
                    backup = backup_root / path.relative_to(self.win64)
                    mkdir(backup.parent); backup.write_bytes(previous[path])
            for path, data in changes.items():
                if data is None: continue
                mkdir(path.parent)
                fd, temp = tempfile.mkstemp(prefix=".pukey-stage-", dir=path.parent)
                staged[path] = Path(temp)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data); stream.flush(); os.fsync(stream.fileno())
            self._guard()
            for path, data in changes.items():
                self._safe(path)
                if data is None:
                    if path.exists(): path.unlink()
                else: os.replace(staged[path], path)
                changed.append(path)
        except BaseException:
            failures = []
            for path in reversed(changed):
                try:
                    old = previous[path]
                    if old is None:
                        if path.exists(): path.unlink()
                    else:
                        fd, temp = tempfile.mkstemp(prefix=".pukey-restore-", dir=path.parent)
                        try:
                            with os.fdopen(fd, "wb") as stream: stream.write(old)
                            os.replace(temp, path)
                        finally:
                            if os.path.exists(temp): os.unlink(temp)
                except OSError as exc: failures.append(str(exc))
            if failures: raise RuntimeError("Rollback incomplete; originals are retained in %s: %s" % (backup_root, "; ".join(failures)))
            raise
        finally:
            for temp in staged.values():
                if temp.exists(): temp.unlink()
            # Empty staging directories are harmless but avoid leaving failed installations behind.
            for path in reversed(created_dirs):
                try: path.rmdir()
                except OSError: pass

    def _activation(self, mod_id, enabled, additions=None):
        changes = {}
        states = {name: False for name in CRASH_PRONE}
        if mod_id: states[mod_id] = bool(enabled)
        lower = {key.casefold(): (key, value) for key, value in states.items()}
        txt_path = self.mods_dir / "mods.txt"
        source = self._read(txt_path)
        if additions and txt_path in additions: source = additions[txt_path]
        try: lines = (source or b"").decode("utf-8-sig").splitlines()
        except UnicodeError as exc: raise ValueError("mods.txt must be UTF-8") from exc
        found = set(); updated = []
        for line in lines:
            match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*:\s*([01])\s*(?:;.*|#.*)?$", line)
            if match and match.group(1).casefold() in lower:
                name, active = lower[match.group(1).casefold()]
                updated.append("%s : %d" % (name, active)); found.add(name)
            else: updated.append(line)
        updated.extend("%s : %d" % (name, active) for name, active in states.items() if name not in found)
        changes[txt_path] = ("\n".join(updated) + "\n").encode("utf-8")
        json_path = self.mods_dir / "mods.json"
        raw = self._read(json_path)
        if additions and json_path in additions: raw = additions[json_path]
        if raw is not None:
            entries = parse_json(raw)
            if not isinstance(entries, list): raise ValueError("mods.json must contain an array")
            seen = set()
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("mod_name"), str) or type(entry.get("mod_enabled")) is not bool:
                    raise ValueError("Invalid mods.json entry")
                name = entry["mod_name"].casefold()
                if name in lower:
                    canonical, active = lower[name]; entry["mod_enabled"] = active; seen.add(canonical)
            entries.extend({"mod_name": name, "mod_enabled": active} for name, active in states.items() if name not in seen)
            changes[json_path] = _json(entries)
        for name, active in states.items():
            changes[self.mods_dir / name / "enabled.txt"] = b"" if active else None
        return changes

    def status(self, mod):
        mod = self._mod(mod); folder = self.mods_dir / mod["id"]
        installed = self._read(folder / "Scripts/main.lua") is not None
        entry = self._state()["mods"].get(mod["id"])
        has_marker = self._read(folder / "enabled.txt") is not None
        active_sources = []
        # UE4SS activation markers bypass the mods.txt list. Preserve that state on adoption.
        txt = self._read(self.mods_dir / "mods.txt")
        if txt:
            text = txt.decode("utf-8-sig")
            matches = re.findall(r"^\s*" + re.escape(mod["id"]) + r"\s*:\s*([01])\b", text, re.M | re.I)
            active_sources.extend(value == "1" for value in matches)
        # The tested UE4SS build does not use mods.json for activation. Explicit
        # manager mutations still keep that compatibility file consistent.
        enabled = installed and (has_marker or (bool(active_sources) and all(active_sources)))
        update = False
        if installed:
            update = entry is None or entry.get("version") != mod["version"]
            for relative in mod["files"]:
                expected = self.snapshot.files["Mods/%s/%s" % (mod["id"], relative)]
                if self._read(folder / relative) != expected: update = True
        return {"installed": installed, "enabled": bool(enabled), "update": update,
                "version": entry.get("version", "unknown") if entry else "unknown" if installed else "",
                "managed": bool(entry)}

    def install(self, mod, progress=None):
        self._guard(); mod = self._mod(mod); state = self._state()
        if progress: progress("Installing " + mod["name"] + "…")
        folder = self.mods_dir / mod["id"]; changes = {}; hashes = {}
        for relative in mod["files"]:
            data = self.snapshot.files["Mods/%s/%s" % (mod["id"], relative)]
            changes[folder / relative] = data; hashes[relative] = _digest(data)
        # Delete obsolete owned files only if they still match the last installed content.
        for relative, digest in state["mods"].get(mod["id"], {}).get("files", {}).items():
            if relative not in hashes:
                old = self._read(folder / relative)
                if old is not None and _digest(old) == digest: changes[folder / relative] = None
        was_installed = self._read(folder / "Scripts/main.lua") is not None
        enabled = self.status(mod)["enabled"] if was_installed else True
        changes.update(self._activation(mod["id"], enabled))
        state["mods"][mod["id"]] = {"version": mod["version"], "revision": self.snapshot.revision, "files": hashes}
        changes[self.state_file] = _json(state)
        self._transaction(changes)

    def set_enabled(self, mod, enabled):
        self._guard(); mod = self._mod(mod)
        if type(enabled) is not bool: raise ValueError("Enabled must be boolean")
        if self._read(self.mods_dir / mod["id"] / "Scripts/main.lua") is None: raise ValueError("Install the mod first")
        self._transaction(self._activation(mod["id"], enabled))

    def remove(self, mod):
        self._guard(); mod = self._mod(mod); state = self._state(); changes = self._activation(mod["id"], False)
        entry = state["mods"].pop(mod["id"], None)
        if entry:
            for relative, digest in entry["files"].items():
                path = self.mods_dir / mod["id"] / relative; data = self._read(path)
                if data is not None and _digest(data) == digest: changes[path] = None
        changes[self.state_file] = _json(state)
        self._transaction(changes)

    def settings(self, mod):
        mod = self._mod(mod); raw = self._read(self.mods_dir / mod["id"] / "settings.json")
        return validate_settings(mod, parse_json(raw) if raw is not None else {})

    def save_settings(self, mod, values):
        self._guard(); mod = self._mod(mod)
        # Read and validate existing settings before replacement, even for a full reset.
        self.settings(mod)
        values = validate_settings(mod, values); folder = self.mods_dir / mod["id"]
        self._transaction({folder / "settings.json": _json(values), folder / "settings.lua": lua_settings(values)})

    def _media_path(self, mod, relative_path):
        mod = self._mod(mod); safe_path(relative_path)
        allowed = {image["file"] for image in mod.get("images", [])}
        if "video_list" in mod:
            source = self.snapshot.files.get("Mods/%s/%s" % (mod["id"], mod["video_list"]))
            if source is not None:
                for line in source.decode("utf-8-sig").splitlines():
                    candidate = line.strip()
                    if candidate.startswith("./"): candidate = candidate[2:]
                    if not candidate.lower().endswith(".mp4") or any(c.isspace() for c in candidate): continue
                    safe_path(candidate); allowed.add(mod["video_folder"] + "/" + candidate)
        if relative_path not in allowed: raise ValueError("Media path is not declared by this mod's catalogue")
        return self.mods_dir / mod["id"] / relative_path

    def write_user_file(self, mod, relative_path, data):
        self._guard()
        if not isinstance(data, bytes): raise ValueError("Media data must be bytes")
        self._transaction({self._media_path(mod, relative_path): data})

    def remove_user_file(self, mod, relative_path):
        self._guard()
        self._transaction({self._media_path(mod, relative_path): None})

    def install_loader(self, progress=None):
        self._guard()
        if progress: progress("Looking up the official UE4SS experimental release…")
        release = parse_json(download(LOADER_RELEASE, 4 * 1024 * 1024))
        if not isinstance(release, dict) or not isinstance(release.get("assets"), list): raise ValueError("Invalid UE4SS release response")
        assets = [a for a in release["assets"] if isinstance(a, dict) and re.fullmatch(r"UE4SS_v[^/\\]+\.zip", a.get("name", ""))]
        if not assets: raise ValueError("The official experimental release has no supported UE4SS ZIP")
        asset = assets[0]; url = asset.get("browser_download_url", "")
        if not re.fullmatch(r"https://github\.com/UE4SS-RE/RE-UE4SS/releases/download/experimental-latest/UE4SS_v[^/\\]+\.zip", url):
            raise ValueError("UE4SS download did not point to the official experimental release")
        if progress: progress("Downloading UE4SS…")
        files = read_archive(download(url), strip_root=False)
        if "ue4ss/UE4SS.dll" not in files or "dwmapi.dll" not in files: raise ValueError("UE4SS ZIP is missing UE4SS.dll or dwmapi.dll")
        state = self._state(); owned = state.get("loader", {}).get("files", {}); changes = {}; hashes = dict(owned)
        for relative, data in files.items():
            path = self.win64 / relative; existing = self._read(path)
            # Example mod config and code already present belong to the user until explicitly adopted.
            if existing is not None and relative not in owned: continue
            if existing is not None and _digest(existing) != owned.get(relative): continue
            changes[path] = data; hashes[relative] = _digest(data)
        changes.update(self._activation(None, False, additions=changes))
        # Activation files are separately maintained and must not later be treated as loader-owned code.
        hashes = {name: digest for name, digest in hashes.items() if not name.startswith("ue4ss/Mods/")}
        state["loader"] = {"files": hashes}; changes[self.state_file] = _json(state)
        self._transaction(changes)
