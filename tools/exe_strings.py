import re,sys
d=open(sys.argv[1],'rb').read()
out=open(sys.argv[2],'w',encoding='utf-8')
for m in re.finditer(rb'(?:[\x20-\x7e]\x00){5,}',d): out.write('W '+m.group().decode('utf-16le')+'\n')
for m in re.finditer(rb'[\x20-\x7e]{6,}',d): out.write('A '+m.group().decode()+'\n')
