import struct,sys,os
class R:
    def __init__(s,d,p=0): s.d=d; s.p=p
    def u(s,f):
        v=struct.unpack_from('<'+f,s.d,s.p); s.p+=struct.calcsize('<'+f); return v if len(v)>1 else v[0]
    def fs(s):
        n=s.u('i')
        if n==0: return ''
        if n<0:
            b=s.d[s.p:s.p-2*n]; s.p+=-2*n; return b.decode('utf-16le').rstrip('\0')
        b=s.d[s.p:s.p+n]; s.p+=n; return b.decode('utf-8','replace').rstrip('\0')
fn=sys.argv[1]; outdir=sys.argv[2]; filt=sys.argv[3:]
f=open(fn,'rb'); sz=os.path.getsize(fn)
f.seek(sz-512); t=f.read(); i=t.rfind(struct.pack('<I',0x5A6F12E1))
io,isz=struct.unpack_from('<QQ',t,i+8)
f.seek(io); r=R(f.read(isz))
mp=r.fs(); n=r.u('i'); seed=r.u('Q')
if r.u('I'): r.u('qq'); r.p+=20
r.u('I'); fdo,fds=r.u('qq'); r.p+=20
encsz=r.u('i'); enc=r.d[r.p:r.p+encsz]; r.p+=encsz
nfiles=r.u('i')
f.seek(fdo); d=R(f.read(fds))
def decode(off):
    e=R(enc,off); v=e.u('I')
    bs=(v&0x3f)<<11
    if (v&0x3f)==0x3f: bs=e.u('I')
    off32=v&(1<<31); usz32=v&(1<<30); sz32=v&(1<<29)
    cm=(v>>23)&0x3f
    o=e.u('I') if off32 else e.u('Q')
    return o,cm
stats={}
for _ in range(d.u('i')):
    dn=d.fs()
    for _ in range(d.u('i')):
        fnm=d.fs(); idx=d.u('i'); path=(mp+dn+fnm).replace('../../../','')
        if idx<0: continue
        o,cm=decode(idx)
        if filt and not any(x in path for x in filt): continue
        # read FPakEntry header at o
        f.seek(o); h=R(f.read(4096))
        eo,esz,eusz,ecm=h.u('qqqI'); h.p+=20
        blocks=[]
        if ecm:
            nb=h.u('I'); blocks=[h.u('qq') for _ in range(nb)]
        flags=h.u('B'); cbs=h.u('I')
        hdr=h.p
        print(path, 'method',ecm,'size',esz,'usize',eusz)
        if ecm==0:
            f.seek(o+hdr); data=f.read(eusz)
            op=os.path.join(outdir,path); os.makedirs(os.path.dirname(op),exist_ok=True); open(op,'wb').write(data)
