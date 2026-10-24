"""Kleine PNG-Werkzeuge ohne externe Bibliotheken (nur zlib).

  py png_util.py testimage <out.png> [breite hoehe]
      Erzeugt ein Testbild: grüner Hintergrund (Chroma Key) mit einer farbigen Figur oben mittig.

  py png_util.py testimage_alpha <out.png> [breite hoehe]
      Wie testimage, aber mit transparentem statt grünem Hintergrund (für die Bar-Fam).

  py png_util.py fit <in.png> <out.png> [breite hoehe]
      Skaliert ein freigestelltes PNG unverzerrt auf eine transparente Fläche (Standard 2220x4312 =
      Format der Bar-Fam-Textur), Figur oben mittig (Kopf oben, die Beine verdeckt die Theke). Ergebnis als FamSwap/bar.png verwenden.

  py png_util.py greenscreen <in.png> <out.png> [breite hoehe] [hoehe_anteil]
      Setzt ein PNG (8 Bit RGB/RGBA, nicht interlaced) skaliert und zentriert oben auf eine
      16:9-Fläche mit reinem Grün RGB(0,255,0). Transparente Bereiche werden grün.
      hoehe_anteil = Anteil der Bildhöhe, den die Figur einnimmt (Standard 1.0).
"""
import struct
import sys
import zlib

GREEN = (0, 255, 0)


def write_png(path, width, height, rows, alpha=False):
    """rows: Liste von bytes (je width*3 RGB, bzw. width*4 RGBA bei alpha=True)."""
    raw = b"".join(b"\x00" + r for r in rows)
    def chunk(t, data):
        c = struct.pack(">I", len(data)) + t + data
        return c + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6 if alpha else 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def read_png(path):
    """Gibt (breite, hoehe, kanaele, pixel-zeilen als bytearray) zurück. Nur 8 Bit, RGB(A)/Grau, nicht interlaced."""
    d = open(path, "rb").read()
    assert d[:8] == b"\x89PNG\r\n\x1a\n", "keine PNG-Datei"
    p, idat, palette, trns = 8, b"", None, None
    while p < len(d):
        n, t = struct.unpack(">I4s", d[p:p + 8])
        body = d[p + 8:p + 8 + n]
        if t == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif t == b"IDAT":
            idat += body
        elif t == b"PLTE":
            palette = body
        elif t == b"tRNS":
            trns = body
        p += 12 + n
    if depth != 8 or interlace:
        sys.exit("Nur 8-Bit-PNGs ohne Interlacing werden unterstützt.")
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * ch
    rows, prev, pos = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[pos]; line = bytearray(raw[pos + 1:pos + 1 + stride]); pos += 1 + stride
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        rows.append(line); prev = line
    # Alles nach RGBA wandeln
    out = []
    for line in rows:
        r = bytearray()
        for x in range(w):
            if ctype == 6: r += line[x * 4:x * 4 + 4]
            elif ctype == 2: r += line[x * 3:x * 3 + 3] + b"\xff"
            elif ctype == 0: v = line[x]; r += bytes((v, v, v, 255))
            elif ctype == 4: v = line[x * 2]; r += bytes((v, v, v, line[x * 2 + 1]))
            elif ctype == 3:
                i = line[x]; rgb = palette[i * 3:i * 3 + 3]
                a = trns[i] if trns and i < len(trns) else 255
                r += rgb + bytes((a,))
        out.append(r)
    return w, h, out


def testimage(path, w=1920, h=1080, alpha=False):
    rows = []
    cx, top, bot = w // 2, int(h * 0.12), int(h * 0.95)
    for y in range(h):
        r = bytearray()
        for x in range(w):
            col = GREEN
            # Kopf (Kreis) und Körper (Trapez), dazu Streifen zur Erkennung
            if (x - cx) ** 2 + (y - int(h * 0.25)) ** 2 < (h * 0.11) ** 2:
                col = (255, 220, 120)
            elif int(h * 0.36) < y < bot:
                half = int(h * 0.08 + (y - h * 0.36) * 0.35)
                if abs(x - cx) < half:
                    col = (40, 90, 255) if ((y // 40) % 2) else (255, 40, 120)
            if alpha:
                r += bytes(col) + bytes((0 if col == GREEN else 255,))
            else:
                r += bytes(col)
        rows.append(bytes(r))
    write_png(path, w, h, rows, alpha)
    print("Testbild geschrieben:", path, w, "x", h)


def greenscreen(src, dst, W=1920, H=1080, frac=1.0):
    w, h, rows = read_png(src)
    target_h = int(H * frac)
    scale = target_h / h
    tw = max(1, int(w * scale))
    if tw > W:
        scale = W / w; tw = W; target_h = int(h * scale)
    x0 = (W - tw) // 2
    out = []
    for y in range(H):
        r = bytearray(bytes(GREEN) * W)
        if y < target_h:
            sy = min(h - 1, int(y / scale))
            line = rows[sy]
            for x in range(tw):
                sx = min(w - 1, int(x / scale))
                pr, pg, pb, pa = line[sx * 4:sx * 4 + 4]
                if pa < 128:
                    continue
                o = (x0 + x) * 3
                # Halbtransparente Kanten mit Grün mischen
                a = pa / 255.0
                r[o] = int(pr * a); r[o + 1] = int(pg * a + 255 * (1 - a)); r[o + 2] = int(pb * a)
        out.append(bytes(r))
    write_png(dst, W, H, out)
    print("Greenscreen-Bild geschrieben:", dst, W, "x", H)


def fit(src, dst, W=2220, H=4312):
    """Skaliert ein (freigestelltes) PNG unverzerrt in eine transparente WxH-Fläche, oben mittig."""
    w, h, rows = read_png(src)
    scale = min(W / w, H / h)
    tw, th = max(1, int(w * scale)), max(1, int(h * scale))
    x0, y0 = (W - tw) // 2, 0
    empty = bytes(W * 4)
    out = []
    for y in range(H):
        if y < y0:
            out.append(empty)
            continue
        line = rows[min(h - 1, int((y - y0) / scale))]
        r = bytearray(W * 4)
        for x in range(tw):
            sx = min(w - 1, int(x / scale)) * 4
            o = (x0 + x) * 4
            r[o:o + 4] = line[sx:sx + 4]
        out.append(bytes(r))
    write_png(dst, W, H, out, alpha=True)
    print("Angepasstes Bild geschrieben:", dst, W, "x", H)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd in ("testimage", "testimage_alpha"):
        args = [int(a) for a in sys.argv[3:5]]
        testimage(sys.argv[2], *args, alpha=(cmd == "testimage_alpha"))
    elif cmd == "fit":
        nums = [int(a) for a in sys.argv[4:6]]
        fit(sys.argv[2], sys.argv[3], *nums)
    elif cmd == "greenscreen":
        nums = sys.argv[4:]
        W = int(nums[0]) if len(nums) > 0 else 1920
        H = int(nums[1]) if len(nums) > 1 else 1080
        frac = float(nums[2]) if len(nums) > 2 else 1.0
        greenscreen(sys.argv[2], sys.argv[3], W, H, frac)
    else:
        sys.exit(__doc__)
