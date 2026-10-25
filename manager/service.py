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
        if raw is None: return {"schema_version": 2, "mods": {}, "loader": {"files": {}}}
        state = parse_json(raw)
        if not isinstance(state, dict) or type(state.get("schema_version")) is not int or state['schema_version'] not in (1, 2) or not isinstance(state.get("mods"), dict):
            raise ValueError("Invalid manager manifest")
        legacy = state['schema_version'] == 1
        seen = set()
        for key, entry in list(state["mods"].items()) + [("loader", state.get("loader", {"files": {}}))]:
            if key != "loader" and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", key): raise ValueError("Invalid managed mod ID")
            if not isinstance(entry, dict) or not isinstance(entry.get("files"), dict): raise ValueError("Invalid ownership manifest")
            if key != 'loader':
                if key.casefold() in seen: raise ValueError('Case-colliding ownership folders')
                seen.add(key.casefold())
                if legacy:
                    entry['source_id'] = 'official'
                    entry['mod_id'] = key
                    entry['personal_files'] = ['settings.json', 'settings.lua']
                    if key == 'FamSwap': entry['personal_files'] += ['bar.png', 'bar.jpg', 'game.png', 'game.jpg']
                    if key == 'MovieSwap': entry['personal_files'] += ['Movies']
                if not isinstance(entry.get('source_id'), str) or not entry['source_id'] or entry.get('mod_id', key) != key:
                    raise ValueError('Invalid source ownership')
                if not isinstance(entry.get('personal_files', []), list): raise ValueError('Invalid personal file ownership')
                for name in entry.get('personal_files', []): safe_path(name)
            for name, digest in entry["files"].items():
                safe_path(name)
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest): raise ValueError("Invalid file hash")
        state['schema_version'] = 2
        history = state.setdefault('personal_files', {})
        if not isinstance(history, dict): raise ValueError('Invalid personal file history')
        for folder, names in history.items():
            safe_path(folder)
            if '/' in folder or not isinstance(names, list): raise ValueError('Invalid personal file history')
            for name in names: safe_path(name)
        return state

    @staticmethod
    def _is_personal(path, names):
        folded = path.casefold()
        return any(folded == name.casefold() or folded.startswith(name.casefold() + '/')
                   or name.casefold().startswith(folded + '/') for name in names)

    @staticmethod
    def _remember_personal(state, mod, names):
        history = state.setdefault('personal_files', {})
        old = next((key for key in history if key.casefold() == mod['id'].casefold()), mod['id'])
        history[old] = sorted(set(history.get(old, [])) | set(names))

    @property
    def source_id(self):
        return getattr(self.snapshot, 'source_id', 'official')

    @staticmethod
    def _entrypoints(mod):
        points = mod.get('entrypoints', [{'type': 'lua', 'path': 'Scripts/main.lua'}])
        if not isinstance(points, list) or not points: raise ValueError('Invalid installed entrypoints')
        return [safe_path(item['path']) for item in points]

    def _ownership(self, mod, state=None):
        state = self._state() if state is None else state
        for name, entry in state['mods'].items():
            if name.casefold() == mod['id'].casefold():
                if name != mod['id'] or entry['source_id'] != self.source_id:
                    raise ValueError('Folder conflict: this mod folder is owned by another source or spelling.')
                return entry
        if self.mods_dir.exists():
            self._safe(self.mods_dir)
            for folder in self.mods_dir.iterdir():
                if folder.name.casefold() == mod['id'].casefold() and folder.name != mod['id']:
                    raise ValueError('Folder conflict: existing folder uses different case.')
        return None

    def _mod(self, mod):
        if isinstance(mod, dict) and mod.get('_source_id', self.source_id) != self.source_id:
            raise ValueError('Mod reference belongs to another source')
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
        # Read-only status never migrates; every successful mutation can do so
        # in the same transaction as its actual change.
        if self.state_file not in changes:
            raw = self._read(self.state_file)
            if raw is not None and parse_json(raw).get('schema_version') == 1:
                changes = dict(changes)
                changes[self.state_file] = _json(self._state())
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
        try:
            entry = self._ownership(mod)
        except ValueError as error:
            if not str(error).startswith('Folder conflict:'): raise
            return {'installed': False, 'enabled': False, 'update': False, 'version': '', 'managed': False,
                    'conflict': str(error)}
        installed_definition = (entry or {}).get('definition', mod)
        installed = all(self._read(folder / path) is not None for path in self._entrypoints(installed_definition))
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
        enabled = installed and (has_marker or any(active_sources))
        update = False
        if installed:
            update = entry is None or entry.get("version") != mod["version"]
            for relative in mod["files"]:
                if self._is_personal(relative, (entry or {}).get('personal_files', [])): continue
                expected = self.snapshot.files["Mods/%s/%s" % (mod["id"], relative)]
                if self._read(folder / relative) != expected: update = True
        return {"installed": installed, "enabled": bool(enabled), "update": update,
                "version": entry.get("version", "unknown") if entry else "unknown" if installed else "",
                "managed": bool(entry), 'conflict': ''}

    def install(self, mod, progress=None, enabled=None):
        self._guard(); mod = self._mod(mod); state = self._state()
        if mod.get('available') is False: raise ValueError('This package is no longer available from its source.')
        if mod['id'].casefold() in {name.casefold() for name in (*CRASH_PRONE, 'shared', 'Keybinds')}:
            raise ValueError('This reserved UE4SS mod cannot be installed from a catalogue.')
        previous_entry = self._ownership(mod, state) or {}
        if enabled is not None and type(enabled) is not bool: raise ValueError('Enabled must be boolean')
        if progress: progress("Installing " + mod["name"] + "…")
        folder = self.mods_dir / mod["id"]; changes = {}; hashes = {}
        personal = set(previous_entry.get('personal_files', [])) | set(mod.get('default_files', []))
        for name, paths in state.get('personal_files', {}).items():
            if name.casefold() == mod['id'].casefold(): personal.update(paths)
        personal.update(target['file'] for target in mod.get('configuration', []))
        personal.update(image['file'] for image in mod.get('images', []))
        if mod.get('video_folder'): personal.add(mod['video_folder'])
        if self.source_id == 'official': personal.update(('settings.lua', 'settings.json'))
        def protected(path):
            return self._is_personal(path, personal)
        for relative in mod["files"]:
            if protected(relative): continue
            data = self.snapshot.files["Mods/%s/%s" % (mod["id"], relative)]
            changes[folder / relative] = data; hashes[relative] = _digest(data)
        for relative in mod.get('default_files', []):
            if self._read(folder / relative) is None:
                changes[folder / relative] = self.snapshot.files['Mods/%s/%s' % (mod['id'], relative)]
        # Delete obsolete owned files only if they still match the last installed content.
        for relative, digest in state["mods"].get(mod["id"], {}).get("files", {}).items():
            if relative not in hashes and not protected(relative):
                old = self._read(folder / relative)
                if old is not None and _digest(old) == digest: changes[folder / relative] = None
        before = self.status(mod)
        enabled = before['enabled'] if before['installed'] else True if enabled is None else enabled
        changes.update(self._activation(mod["id"], enabled))
        state["mods"][mod["id"]] = {"version": mod["version"], "revision": self.snapshot.revision, "files": hashes,
                                    'source_id': self.source_id, 'mod_id': mod['id'],
                                    'personal_files': sorted(personal), 'definition': mod}
        self._remember_personal(state, mod, personal)
        changes[self.state_file] = _json(state)
        self._transaction(changes)

    def set_enabled(self, mod, enabled):
        self._guard(); mod = self._mod(mod)
        self._ownership(mod)
        if type(enabled) is not bool: raise ValueError("Enabled must be boolean")
        if not self.status(mod)['installed']:
            raise ValueError("Install the mod first")
        changes = self._activation(mod['id'], enabled)
        if self.state_file.exists(): changes[self.state_file] = _json(self._state())
        self._transaction(changes)

    def remove(self, mod):
        self._guard(); mod = self._mod(mod); state = self._state(); self._ownership(mod, state)
        changes = self._activation(mod["id"], False)
        entry = state["mods"].pop(mod["id"], None)
        if entry:
            self._remember_personal(state, mod, entry.get('personal_files', []))
            for relative, digest in entry["files"].items():
                if self._is_personal(relative, entry.get('personal_files', [])): continue
                path = self.mods_dir / mod["id"] / relative; data = self._read(path)
                if data is not None and _digest(data) == digest: changes[path] = None
        changes[self.state_file] = _json(state)
        self._transaction(changes)

    def settings(self, mod):
        mod = self._mod(mod); self._ownership(mod)
        if 'configuration' in mod:
            from .configuration import read_configuration
            return read_configuration(mod, lambda path: self._read(self.mods_dir / mod['id'] / path))
        raw = self._read(self.mods_dir / mod["id"] / "settings.json")
        if not mod.get('settings'): return {}
        return validate_settings(mod, parse_json(raw) if raw is not None else {})

    def save_settings(self, mod, values):
        self._guard(); mod = self._mod(mod)
        # Read and validate existing settings before replacement, even for a full reset.
        self.settings(mod)
        folder = self.mods_dir / mod["id"]
        if 'configuration' in mod:
            from .configuration import write_configuration
            proposed = write_configuration(mod, values, lambda path: self._read(folder / path))
            self._transaction({folder / path: data for path, data in proposed.items()})
            return
        values = validate_settings(mod, values)
        self._transaction({folder / "settings.json": _json(values), folder / "settings.lua": lua_settings(values)})

    def _media_path(self, mod, relative_path):
        mod = self._mod(mod); self._ownership(mod); safe_path(relative_path)
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
        path = self._media_path(mod, relative_path)
        mod = self._mod(mod)
        state = self._state()
        self._remember_personal(state, mod, [relative_path])
        entry = state['mods'].get(mod['id'])
        if entry:
            entry['personal_files'] = sorted(set(entry.get('personal_files', [])) | {relative_path})
        self._transaction({path: data, self.state_file: _json(state)})

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
