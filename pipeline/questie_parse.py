# Parse QuestieDB Forever TOC (data only) -> quests.json with name, levels, races, zoneOrSort, requiredSkill, rep
import base64, struct, zlib, json, re, sys
toc=open(sys.argv[1],encoding='utf-8').read().splitlines()
store={}
for line in toc:
    line=line.rstrip('\r')
    if line.startswith('## X-') and ': ' in line:
        k,v=line.split(': ',1); store[k[5:]]=v
def b64(key):
    v=store.get(key)
    if v is None: return None
    m=re.match(r'^~(\d+)~$',v)
    if m: v=''.join(store[f"{key}-{i}"] for i in range(1,int(m.group(1))+1))
    return base64.b64decode(v)
def cbor(b,i=0):
    ib=b[i]; mt=ib>>5; ai=ib&31; i+=1
    def arg(ai,i):
        if ai<24: return ai,i
        if ai==24: return b[i],i+1
        if ai==25: return struct.unpack('>H',b[i:i+2])[0],i+2
        if ai==26: return struct.unpack('>I',b[i:i+4])[0],i+4
        if ai==27: return struct.unpack('>Q',b[i:i+8])[0],i+8
        raise ValueError(ai)
    if mt==7:
        if ai==20: return False,i
        if ai==21: return True,i
        if ai==22 or ai==23: return None,i
        if ai==25:
            h=struct.unpack('>e',b[i:i+2])[0]; return h,i+2
        if ai==26: return struct.unpack('>f',b[i:i+4])[0],i+4
        if ai==27: return struct.unpack('>d',b[i:i+8])[0],i+8
        raise ValueError('simple',ai)
    n,i=arg(ai,i)
    if mt==0: return n,i
    if mt==1: return -1-n,i
    if mt==2:
        bs=b[i:i+n]
        try: return bs.decode('utf-8'),i+n
        except Exception: return bs.hex(),i+n
    if mt==3: return b[i:i+n].decode('utf-8','replace'),i+n
    if mt==4:
        out=[]
        for _ in range(n):
            v,i=cbor(b,i); out.append(v)
        return out,i
    if mt==5:
        out={}
        for _ in range(n):
            k,i=cbor(b,i); v,i=cbor(b,i); out[k]=v
        return out,i
    if mt==6:
        return cbor(b,i)
    raise ValueError(mt)
def val(key):
    d=b64(key)
    if d is None: return None
    return cbor(d)[0]
def ids(name):
    return cbor(zlib.decompress(b64(name+'-IDS')))[0]
def row(name,i):
    v=val(f"{name}-{i}-S")
    if v is None: return None
    f={}
    if isinstance(v,list):
        for j,x in enumerate(v): f[j+1]=x
    else:
        for k,x in v.items():
            if isinstance(k,int): f[k]=x
            elif k=='p': f['p']=x
    return f
def field(name,i,f,idx):
    if idx in f: return f[idx]
    p=f.get('p',0)
    if p and (p>>(idx-1))&1:
        return val(f"{name}-{i}-{idx}")
    return None
qids=ids('Quest')
quests={}
for q in qids:
    f=row('Quest',q)
    if f is None: continue
    rec={'name':field('Quest',q,f,1),'requiredLevel':field('Quest',q,f,4),'questLevel':field('Quest',q,f,5),
         'requiredRaces':field('Quest',q,f,6),'requiredClasses':field('Quest',q,f,7),'zoneOrSort':field('Quest',q,f,17),
         'requiredSkill':field('Quest',q,f,18),'requiredMinRep':field('Quest',q,f,19)}
    quests[q]=rec
nids=ids('Npc'); npcs={}
for n in nids:
    f=row('Npc',n)
    if f is None: continue
    npcs[n]={'name':field('Npc',n,f,1),'minLevel':field('Npc',n,f,4),'maxLevel':field('Npc',n,f,5),'rank':field('Npc',n,f,6),'zoneID':field('Npc',n,f,9),'friendlyToFaction':field('Npc',n,f,13),'subName':field('Npc',n,f,14)}
json.dump({'quests':quests,'npcs':npcs},open(sys.argv[2],'w'),default=lambda o: o.hex() if isinstance(o,bytes) else str(o))
print(len(quests),len(npcs))
