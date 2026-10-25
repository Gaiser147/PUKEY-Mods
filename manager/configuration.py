"""Read and propose typed configuration changes without executing code or writing files.

The caller supplies reads relative to a mod root and applies the returned proposals
as one installer transaction. Unsupported existing syntax is always left intact.
"""
import json
import math
from pathlib import PurePosixPath
import re
from typing import Callable

from .catalog import MAX_FILE, lua_settings, parse_json, safe_path, validate_settings

Reader = Callable[[str], bytes | None]
_MISSING = object()
_NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?')


def _name(value, label):
    if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) < 32 or c in '\x7f\x85\u2028\u2029' for c in value):
        raise ValueError('Invalid configuration ' + label)
    return value


def validate_configuration(mod: dict) -> None:
    """Check complete, unambiguous bindings and safe personal-file ownership."""
    if 'configuration' not in mod:
        return
    targets = mod['configuration']
    if not isinstance(targets, list) or not targets:
        raise ValueError('Configuration must contain at least one target')
    specs = mod.get('settings', [])
    if not isinstance(specs, list) or any(not isinstance(s, dict) or not isinstance(s.get('key'), str) for s in specs):
        raise ValueError('Invalid configuration settings')
    keys = {s['key'] for s in specs}
    if len(keys) != len(specs):
        raise ValueError('Duplicate configuration setting')
    bound = set(); paths = set()
    programs = {p.casefold() for p in mod.get('files', [])}
    programs.update(p.casefold() for p in mod.get('program_files', []))
    for entry in mod.get('entrypoints', []):
        if not isinstance(entry, dict):
            raise ValueError('Invalid configuration entrypoint')
        programs.add(safe_path(entry.get('path')).casefold())
    for target in targets:
        if not isinstance(target, dict) or set(target) != {'file', 'format', 'bindings'}:
            raise ValueError('Invalid configuration target')
        path = safe_path(target['file']); folded = path.casefold()
        fmt = target['format']
        if not isinstance(fmt, str) or fmt not in ('json', 'ini', 'lua'):
            raise ValueError('Unsupported configuration format')
        if PurePosixPath(path).suffix.casefold() != '.' + fmt:
            raise ValueError('Configuration extension does not match its format')
        if folded in programs or PurePosixPath(path).name.casefold() in ('main.lua', 'enabled.txt'):
            raise ValueError('Configuration target conflicts with program files')
        if any(folded == p or folded.startswith(p + '/') or p.startswith(folded + '/') for p in paths):
            raise ValueError('Duplicate or overlapping configuration targets')
        if any(folded.startswith(p + '/') or p.startswith(folded + '/') for p in programs):
            raise ValueError('Configuration target conflicts with program path')
        paths.add(folded)
        bindings = target['bindings']
        if not isinstance(bindings, dict) or not bindings:
            raise ValueError('Configuration bindings must be a nonempty object')
        addresses = []
        for key, binding in bindings.items():
            if key not in keys or key in bound:
                raise ValueError('Unknown or repeated configuration binding: ' + str(key))
            if not isinstance(binding, dict):
                raise ValueError('Invalid configuration binding')
            if fmt == 'json':
                path_parts = binding.get('path')
                if set(binding) != {'path'} or not isinstance(path_parts, list) or not path_parts:
                    raise ValueError('JSON binding requires a nonempty path')
                address = tuple(_name(p, 'JSON path') for p in path_parts)
                if any(address[:len(other)] == other or other[:len(address)] == address for other in addresses):
                    raise ValueError('Overlapping JSON configuration bindings')
            elif fmt == 'ini':
                if set(binding) != {'section', 'key'}:
                    raise ValueError('INI binding requires section and key')
                section = _name(binding['section'], 'INI section'); option = _name(binding['key'], 'INI key')
                if section != section.strip() or option != option.strip() or any(c in section for c in '[]') or section.casefold() == 'default' or any(c in option for c in '=:#;[]'):
                    raise ValueError('Unsafe INI binding')
                address = (section.casefold(), option.casefold())
            else:
                if set(binding) != {'key'}:
                    raise ValueError('Lua binding requires a key')
                address = (_name(binding['key'], 'Lua key'),)
            if address in addresses:
                raise ValueError('Duplicate configuration destination')
            addresses.append(address); bound.add(key)
    if bound != keys:
        raise ValueError('Every setting needs exactly one configuration binding')
    _validate_values(mod, {})


def _validate_values(mod, values):
    try:
        return validate_settings(mod, values)
    except OverflowError as exc:
        raise ValueError('Configuration number exceeds supported finite range') from exc


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Non-finite configuration number')
    if isinstance(value, dict):
        for child in value.values(): _finite(child)
    elif isinstance(value, list):
        for child in value: _finite(child)


def _text(data):
    if not isinstance(data, bytes) or len(data) > MAX_FILE:
        raise ValueError('Invalid or oversized configuration file')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeError as exc:
        raise ValueError('Configuration must use UTF-8; file left unchanged') from exc
    if '\x00' in text:
        raise ValueError('NUL is not supported in configuration files')
    return text


class _Lua:
    """A deliberately small parser: return { identifier|string-key = literal }."""
    def __init__(self, text):
        self.text = text; self.pos = 0

    def error(self):
        raise ValueError('Lua configuration must be a literal return table (string, number, boolean values only); edit this file manually')

    def skip(self):
        while True:
            match = re.match(r'\s*', self.text[self.pos:]); self.pos += match.end()
            if not self.text.startswith('--', self.pos): return
            self.pos += 2
            match = re.match(r'\[(=*)\[', self.text[self.pos:])
            if match:
                self.pos += match.end(); end = ']' + match[1] + ']'
                stop = self.text.find(end, self.pos)
                if stop < 0: self.error()
                self.pos = stop + len(end)
            else:
                stop = self.text.find('\n', self.pos)
                self.pos = len(self.text) if stop < 0 else stop + 1

    def take(self, value):
        self.skip()
        if self.text.startswith(value, self.pos):
            self.pos += len(value); return True
        return False

    def string(self):
        self.skip()
        if self.pos >= len(self.text) or self.text[self.pos] not in '\"\'': self.error()
        quote = self.text[self.pos]; self.pos += 1; result = bytearray()
        escapes = {'a': 7, 'b': 8, 'f': 12, 'n': 10, 'r': 13, 't': 9, 'v': 11, '\\': 92, '\"': 34, "'": 39}
        while self.pos < len(self.text):
            char = self.text[self.pos]; self.pos += 1
            if char == quote:
                try: return result.decode('utf-8')
                except UnicodeError: self.error()
            if ord(char) < 32: self.error()
            if char != '\\':
                result.extend(char.encode('utf-8')); continue
            if self.pos >= len(self.text): self.error()
            char = self.text[self.pos]; self.pos += 1
            if char in escapes: result.append(escapes[char])
            elif char.isascii() and char.isdigit():
                digits = char
                for _ in range(2):
                    if self.pos < len(self.text) and self.text[self.pos].isascii() and self.text[self.pos].isdigit():
                        digits += self.text[self.pos]; self.pos += 1
                    else: break
                value = int(digits)
                if value > 255: self.error()
                result.append(value)
            else: self.error()
        self.error()

    def literal(self):
        self.skip()
        if self.pos < len(self.text) and self.text[self.pos] in '\"\'': return self.string()
        for word, value in (('true', True), ('false', False)):
            if re.match(word + r'(?![A-Za-z0-9_])', self.text[self.pos:]):
                self.pos += len(word); return value
        match = _NUMBER.match(self.text, self.pos)
        if match:
            token = match[0]; self.pos = match.end()
            try: value = float(token) if any(c in token for c in '.eE') else int(token)
            except ValueError: self.error()
            try:
                if not math.isfinite(value): self.error()
            except OverflowError:
                self.error()
            return value
        self.error()

    def parse(self):
        if not self.take('return') or not self.take('{'): self.error()
        result = {}
        while not self.take('}'):
            if self.take('['):
                key = self.string()
                if not self.take(']'): self.error()
            else:
                self.skip(); match = re.match(r'[A-Za-z_][A-Za-z0-9_]*', self.text[self.pos:])
                if not match: self.error()
                key = match[0]; self.pos += match.end()
                if key in {'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'goto', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', 'while'}: self.error()
            if key in result or not self.take('='): self.error()
            result[key] = self.literal()
            if not (self.take(',') or self.take(';')):
                if not self.take('}'): self.error()
                break
        self.skip()
        if self.pos != len(self.text): self.error()
        return result


def _ini_parts(value):
    """Split an INI value from its inline comment, respecting quoted strings."""
    quote = None; escaped = False
    for index, char in enumerate(value):
        if quote:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == quote: quote = None
        elif char == '"' and not value[:index].strip(): quote = char
        elif char in ';#' and index and value[index - 1].isspace():
            prefix = value[:index]; stripped = prefix.rstrip()
            return stripped, prefix[len(stripped):] + value[index:]
    stripped = value.rstrip()
    return stripped, value[len(stripped):]


class _Ini:
    def __init__(self, text):
        if any(c in text for c in '\v\f\x1c\x1d\x1e\x85\u2028\u2029'):
            raise ValueError('Unsupported INI line separator; edit manually')
        self.lines = text.splitlines(keepends=True); self.sections = {}; self.entries = {}
        self.newline = '\r\n' if '\r\n' in text else '\n'
        section = None
        for index, line in enumerate(self.lines):
            body = line.rstrip('\r\n'); stripped = body.strip()
            if not stripped or stripped.startswith((';', '#')): continue
            match = re.fullmatch(r'\s*\[([^\[\]]+)\]\s*(?:[;#].*)?', body)
            if match:
                section = match[1].casefold()
                if section == 'default' or section in self.sections:
                    raise ValueError('Ambiguous or unsupported INI section; edit manually')
                self.sections[section] = (index, match[1]); continue
            match = re.fullmatch(r'(\s*[^=:#;\[\]\s][^=:#;\[\]]*?\s*=\s*)(.*)', body)
            if not match or section is None:
                raise ValueError('Unsupported INI syntax or multiline value; edit manually')
            key = match[1].split('=', 1)[0].strip().casefold()
            address = (section, key)
            if address in self.entries:
                raise ValueError('Ambiguous duplicate INI key; edit manually')
            value, comment = _ini_parts(match[2])
            ending = line[len(body):]
            self.entries[address] = (index, match[1], value, comment, ending)

    def get(self, binding, spec):
        entry = self.entries.get((binding['section'].casefold(), binding['key'].casefold()))
        if entry is None: return _MISSING
        value = entry[2].strip(); kind = spec['type']
        if kind == 'boolean':
            if value.casefold() not in ('true', 'false'): raise ValueError('Invalid INI boolean: ' + spec['key'])
            return value.casefold() == 'true'
        if kind == 'number':
            if not _NUMBER.fullmatch(value): raise ValueError('Invalid INI number: ' + spec['key'])
            try: return float(value) if any(c in value for c in '.eE') else int(value)
            except ValueError as exc: raise ValueError('Invalid INI number') from exc
        if value.startswith('"'):
            try: parsed = json.loads(value)
            except (ValueError, TypeError) as exc: raise ValueError('Invalid quoted INI string') from exc
            if not isinstance(parsed, str): raise ValueError('Invalid INI string')
            return parsed
        return value

    def render(self, target, values, existing, specs):
        edits = {}; additions = {}
        for key, binding in target['bindings'].items():
            address = (binding['section'].casefold(), binding['key'].casefold())
            entry = self.entries.get(address)
            if entry is not None and values[key] == existing[key]: continue
            value = values[key]
            rendered = ('true' if value else 'false') if type(value) is bool else repr(value) if type(value) in (int, float) else json.dumps(value, ensure_ascii=False)
            if entry:
                index, prefix, _, comment, ending = entry
                edits[index] = prefix + rendered + comment + ending
            else:
                additions.setdefault(address[0], []).append(binding['key'] + '=' + rendered + self.newline)
        inserts = {}
        section_order = sorted((entry[0], name) for name, entry in self.sections.items())
        extra = []
        for section, lines in additions.items():
            if section in self.sections:
                start = self.sections[section][0]
                stop = next((index for index, _ in section_order if index > start), len(self.lines))
                inserts.setdefault(stop, []).extend(lines)
            else:
                spelling = next(b['section'] for b in target['bindings'].values() if b['section'].casefold() == section)
                extra.extend(['[' + spelling + ']' + self.newline] + lines)
        output = ''
        for index in range(len(self.lines) + 1):
            if index in inserts:
                if output and not output.endswith(('\n', '\r')): output += self.newline
                output += ''.join(inserts[index])
            if index < len(self.lines): output += edits.get(index, self.lines[index])
        if extra:
            if output and not output.endswith(('\n', '\r')): output += self.newline
            output += ''.join(extra)
        return output.encode('utf-8')


def _json_get(document, path):
    for part in path:
        if not isinstance(document, dict):
            raise ValueError('JSON configuration path crosses a scalar or array')
        if part not in document: return _MISSING
        document = document[part]
    return document


def _load(mod, read):
    validate_configuration(mod)
    if not mod.get('configuration'):
        raise ValueError('This mod has no configuration bindings')
    specs = {s['key']: s for s in mod.get('settings', [])}
    documents = []; values = {}
    for target in mod['configuration']:
        data = read(target['file'])
        text = _text(data) if data is not None else ''
        fmt = target['format']
        if fmt == 'json':
            document = parse_json(text) if data is not None else {}
            if not isinstance(document, dict): raise ValueError('JSON configuration must be an object')
            _finite(document)
        elif fmt == 'ini': document = _Ini(text)
        else: document = _Lua(text).parse() if data is not None else {}
        for key, binding in target['bindings'].items():
            value = _json_get(document, binding['path']) if fmt == 'json' else document.get(binding, specs[key]) if fmt == 'ini' else document.get(binding['key'], _MISSING)
            if value is not _MISSING: values[key] = value
        documents.append((target, data, document))
    return _validate_values(mod, values), documents, specs


def read_configuration(mod: dict, read: Reader) -> dict:
    """Return validated existing values, with declared defaults for missing keys."""
    return _load(mod, read)[0]


def write_configuration(mod: dict, values: dict, read: Reader) -> dict[str, bytes]:
    """Validate all existing targets, then return only changed file proposals."""
    existing, documents, specs = _load(mod, read)
    if not isinstance(values, dict): raise ValueError('Settings must be an object')
    merged = _validate_values(mod, {**existing, **values})
    output = {}
    for target, original, document in documents:
        fmt = target['format']
        if fmt == 'ini':
            proposed = document.render(target, merged, existing, specs)
            if original is not None and original.startswith(b'\xef\xbb\xbf'):
                proposed = b'\xef\xbb\xbf' + proposed
        else:
            for key, binding in target['bindings'].items():
                if fmt == 'lua': document[binding['key']] = merged[key]
                else:
                    parent = document
                    for part in binding['path'][:-1]:
                        if part not in parent: parent[part] = {}
                        if not isinstance(parent[part], dict): raise ValueError('JSON configuration path crosses a scalar or array')
                        parent = parent[part]
                    parent[binding['path'][-1]] = merged[key]
            proposed = lua_settings(document) if fmt == 'lua' else (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
        # Preserve original formatting when every bound key already has the desired value.
        if original is not None and fmt != 'ini':
            old = _Lua(_text(original)).parse() if fmt == 'lua' else parse_json(_text(original))
            if old == document: proposed = original
        if proposed != original: output[target['file']] = proposed
    return output
