import sys,re
path=sys.argv[1]; ids=set(int(x) for x in sys.argv[2].split(','))
blocks={}
cur=None;buf=[]
with open(path) as f:
    for line in f:
        m=re.match(r'^\t\{ID: (\d+), ',line)
        if m:
            if cur is not None: blocks[cur]=''.join(buf)
            cur=int(m.group(1));buf=[line]
        elif cur is not None:
            buf.append(line)
if cur is not None: blocks[cur]=''.join(buf)
for i in sys.argv[2].split(','):
    i=int(i)
    print(blocks.get(i,'MISSING %d\n'%i))
