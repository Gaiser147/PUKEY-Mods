"""Baut ein unkomprimiertes, unverschlüsseltes UE-Pak (Version 12, wie das Spiel) aus einem Ordner.

Gedacht für Mods, die lose Dateien (z. B. .mp4, .png, .ini) per Pfad überschreiben.
Cooked .uasset-Dateien gehören bei diesem Spiel dagegen in IoStore-Container (.utoc/.ucas, z. B. mit retoc).

Aufbau des Eingabeordners = Pfad relativ zum Mount-Punkt "../../../", z. B.:
    <ordner>/PUKEY_GODDESS_SHOT_TRICK/Content/Bacchus/Movie/Fam/T_FAM_BOW_A.mp4

Benutzung:
    py make_pak.py <eingabeordner> <ausgabe.pak>

Ins Spiel: Content/Paks/~mods/<Name>_P.pak (Suffix _P = höhere Priorität als das Original).

ACHTUNG (getestet 2026-10-24): Dieses Spiel bindet ein .pak OHNE gleichnamige .utoc/.ucas nicht ein
(CVar pak.AllowMissingUToc ist aus und wird zu spät gelesen, um sie per Engine.ini zu setzen).
Das Format dieses Werkzeugs ist korrekt (Index-/PathHash-SHA1 und FNV-Pfad-Hashes geprüft), ein
nutzbares Mod-Pak braucht aber zusätzlich einen IoStore-Container (z. B. mit retoc erzeugt).
Für Videos stattdessen die MovieSwap-Mod verwenden.
"""
import hashlib
import os
import struct
import sys
import zlib

PAK_MAGIC = 0x5A6F12E1
PAK_VERSION = 12
MOUNT_POINT = "../../../"


def fstring(s: str) -> bytes:
    """FString wie UE: ASCII/UTF-8 mit Nullterminator, sonst UTF-16 mit negativer Länge."""
    try:
        b = s.encode("ascii") + b"\0"
        return struct.pack("<i", len(b)) + b
    except UnicodeEncodeError:
        b = s.encode("utf-16-le") + b"\0\0"
        return struct.pack("<i", -(len(b) // 2)) + b


def path_hash(rel_path: str, seed: int) -> int:
    """FNV-1a 64 über den kleingeschriebenen UTF-16-Pfad relativ zum Mount-Punkt (wie FPakFile::HashPath)."""
    h = (0xCBF29CE484222325 + seed) & 0xFFFFFFFFFFFFFFFF
    for b in rel_path.lower().encode("utf-16-le"):
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def entry_header(size: int, sha1: bytes) -> bytes:
    """FPakEntry vor den Daten. Offset-Feld ist im Datenkopf 0 (wie UnrealPak)."""
    return struct.pack("<qqqI", 0, size, size, 0) + sha1 + struct.pack("<BI", 0, 0)


def encoded_entry(offset: int, size: int) -> bytes:
    """Kompakte Index-Kodierung eines unkomprimierten Eintrags."""
    flags = 0
    body = b""
    if offset <= 0xFFFFFFFF:
        flags |= 1 << 31
        body += struct.pack("<I", offset)
    else:
        body += struct.pack("<Q", offset)
    if size <= 0xFFFFFFFF:
        flags |= (1 << 30) | (1 << 29)
        body += struct.pack("<I", size)
    else:
        body += struct.pack("<Q", size)
    return struct.pack("<I", flags) + body


def collect(root: str):
    files = []
    for dirpath, _, names in os.walk(root):
        for n in names:
            full = os.path.join(dirpath, n)
            rel = os.path.relpath(full, root).replace("\\", "/")
            files.append((rel, full))
    files.sort()
    return files


def build(root: str, out_path: str):
    files = collect(root)
    if not files:
        sys.exit("Keine Dateien im Eingabeordner.")

    data = bytearray()
    encoded = bytearray()
    seed = zlib.crc32(os.path.basename(out_path).lower().encode("utf-8"))
    hashes = []   # (hash, encoded_offset)
    directories = {"/": []}   # Verzeichnis (relativ, mit '/') -> [(dateiname, encoded_offset)]

    for rel, full in files:
        payload = open(full, "rb").read()
        offset = len(data)
        data += entry_header(len(payload), hashlib.sha1(payload).digest())
        data += payload

        enc_off = len(encoded)
        encoded += encoded_entry(offset, len(payload))
        hashes.append((path_hash(rel, seed), enc_off))

        d, name = rel.rsplit("/", 1) if "/" in rel else ("", rel)
        dkey = d + "/" if d else "/"
        directories.setdefault(dkey, []).append((name, enc_off))
        # Elternverzeichnisse ebenfalls eintragen (wie UnrealPak)
        parts = d.split("/") if d else []
        for i in range(1, len(parts)):
            directories.setdefault("/".join(parts[:i]) + "/", [])

    # Full Directory Index
    fdi = bytearray(struct.pack("<i", len(directories)))
    for dname in sorted(directories):
        entries = directories[dname]
        fdi += fstring(dname) + struct.pack("<i", len(entries))
        for name, enc_off in entries:
            fdi += fstring(name) + struct.pack("<i", enc_off)

    # Path Hash Index: Hash -> Eintrag, danach ein (hier ungekürzter) Verzeichnisindex
    phi = bytearray(struct.pack("<i", len(hashes)))
    for h, enc_off in sorted(hashes):
        phi += struct.pack("<Qi", h, enc_off)
    phi += fdi

    index_offset = len(data)
    # Primärindex; seine Größe hängt nicht von den Offsets ab, daher vorab berechenbar
    def primary(phi_offset, fdi_offset):
        p = bytearray()
        p += fstring(MOUNT_POINT)
        p += struct.pack("<i", len(files))
        p += struct.pack("<Q", seed)                    # PathHashSeed
        p += struct.pack("<I", 1)                       # PathHashIndex vorhanden
        p += struct.pack("<qq", phi_offset, len(phi)) + hashlib.sha1(phi).digest()
        p += struct.pack("<I", 1)                       # Full Directory Index vorhanden
        p += struct.pack("<qq", fdi_offset, len(fdi)) + hashlib.sha1(fdi).digest()
        p += struct.pack("<i", len(encoded)) + encoded
        p += struct.pack("<i", 0)                       # keine nicht-kodierten Einträge
        return bytes(p)

    primary_size = len(primary(0, 0))
    phi_offset = index_offset + primary_size
    fdi_offset = phi_offset + len(phi)
    prim = primary(phi_offset, fdi_offset)

    footer = bytearray()
    footer += b"\0" * 16                                # EncryptionKeyGuid
    footer += struct.pack("<B", 0)                      # bEncryptedIndex
    footer += struct.pack("<Ii", PAK_MAGIC, PAK_VERSION)
    footer += struct.pack("<qq", index_offset, len(prim)) + hashlib.sha1(prim).digest()
    footer += b"\0" * (5 * 32)                          # Kompressionsmethoden (keine)

    with open(out_path, "wb") as f:
        f.write(data)
        f.write(prim)
        f.write(phi)
        f.write(fdi)
        f.write(footer)

    print(f"{out_path}: {len(files)} Datei(en), {os.path.getsize(out_path) / 1024 / 1024:.1f} MB")
    for rel, _ in files:
        print("  " + MOUNT_POINT + rel)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
