import struct,sys
d=open(sys.argv[1],'rb').read()
hs,ec,cbc,cbs,cmc,cml,cbsz,dis,pc=struct.unpack_from('<9I',d,20)
seeds,=struct.unpack_from('<I',d,84); nph,=struct.unpack_from('<I',d,96)
p=hs+ec*12+ec*10+seeds*4+nph*4+cbc*12+cmc*cml
p0=p
def fs():
    global p
    n,=struct.unpack_from('<i',d,p); p+=4
    if n<0: s=d[p:p-2*n].decode('utf-16le'); p+=-2*n
    else: s=d[p:p+n].decode('utf-8','replace'); p+=n
    return s.rstrip('\0')
mp=fs()
n,=struct.unpack_from('<i',d,p); p+=4
dirs=[struct.unpack_from('<4I',d,p+16*i) for i in range(n)]; p+=16*n
n,=struct.unpack_from('<i',d,p); p+=4
files=[struct.unpack_from('<3I',d,p+12*i) for i in range(n)]; p+=12*n
n,=struct.unpack_from('<i',d,p); p+=4
st=[fs() for _ in range(n)]
NONE=0xffffffff
out=[]
def walk(di,path):
    name,fc,ns,ff=dirs[di]
    if name!=NONE: path=path+st[name]+'/'
    f=ff
    while f!=NONE:
        fn,nf,ud=files[f]; out.append(path+st[fn]); f=nf
    c=fc
    while c!=NONE:
        walk(c,path); c=dirs[c][2]
walk(0,mp)
for o in sorted(out): print(o)
