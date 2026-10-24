"""Liest Auflösung, Codec, Dauer, FPS und Audio-Spuren aus MP4-Dateien (ohne ffmpeg)."""
import struct, sys, os, glob

CONTAINERS = {b'moov', b'trak', b'mdia', b'minf', b'stbl', b'edts', b'udta'}

def boxes(d, start, end):
    p = start
    while p + 8 <= end:
        size, typ = struct.unpack('>I4s', d[p:p+8]); hdr = 8
        if size == 1: size = struct.unpack('>Q', d[p+8:p+16])[0]; hdr = 16
        elif size == 0: size = end - p
        yield typ, p + hdr, p + size
        p += size

def info(path):
    d = open(path, 'rb').read()
    tracks = []
    def walk(s, e, cur):
        for typ, a, b in boxes(d, s, e):
            if typ == b'trak':
                t = {}; tracks.append(t); walk(a, b, t)
            elif typ in CONTAINERS: walk(a, b, cur)
            elif typ == b'tkhd' and cur is not None:
                v = d[a]; off = a + (84 if v == 1 else 76)
                cur['w'], cur['h'] = struct.unpack('>II', d[off:off+8]); cur['w'] >>= 16; cur['h'] >>= 16
            elif typ == b'mdhd' and cur is not None:
                v = d[a]
                if v == 1: ts, dur = struct.unpack('>IQ', d[a+20:a+32])
                else: ts, dur = struct.unpack('>II', d[a+12:a+20])
                cur['dur'] = dur / ts; cur['ts'] = ts
            elif typ == b'hdlr' and cur is not None and 'kind' not in cur: cur['kind'] = d[a+8:a+12].decode('latin1')
            elif typ == b'stsd' and cur is not None: cur['codec'] = d[a+12:a+16].decode('latin1')
            elif typ == b'stsz' and cur is not None: cur['samples'] = struct.unpack('>I', d[a+8:a+12])[0]
    walk(0, len(d), None)
    out = []
    for t in tracks:
        if t.get('kind') == 'vide':
            fps = t['samples'] / t['dur'] if t.get('dur') else 0
            out.append(f"video {t.get('codec')} {t.get('w')}x{t.get('h')} {t.get('dur',0):.2f}s {fps:.2f}fps")
        elif t.get('kind') == 'soun':
            out.append(f"audio {t.get('codec')}")
    return '; '.join(out)

if __name__ == '__main__':
    files = []
    for a in sys.argv[1:]:
        files += glob.glob(os.path.join(a, '**', '*.mp4'), recursive=True) if os.path.isdir(a) else [a]
    for f in sorted(files):
        print(f"{os.path.basename(f):48s} {os.path.getsize(f)//1024:6d} KB  {info(f)}")
