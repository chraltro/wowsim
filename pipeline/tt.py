import json, re, sys, urllib.request, html as H
def fetch(i):
    u=f"https://forever.warcraftdb.com/api/v1/tooltip/item/{i}"
    try:
        import subprocess; return json.loads(subprocess.run(["curl","-sS","-m","30",u],capture_output=True).stdout)
    except Exception as e:
        return None
PAT=[
 ('int',r'\+(\d+) Intellect'),('spi',r'\+(\d+) Spirit'),('sta',r'\+(\d+) Stamina'),('str',r'\+(\d+) Strength'),('agi',r'\+(\d+) Agility'),
 ('heal',r'Increases healing done by magical spells and effects by up to (\d+)'),
 ('dmg',r'Increases damage done by magical spells and effects by up to (\d+)'),
 ('sp',r'Increases spell power by (\d+)'),
 ('dh',r'Increases damage and healing done by magical spells and effects by up to (\d+)'),
 ('mp5',r'Restores (\d+) mana per 5 sec'),
 ('crit',r'Increases your critical strike by (\d+)'),
 ('hit',r'Increases your hit by (\d+)'),
 ('haste',r'Increases your haste by (\d+)'),
 ('ap',r'\+(\d+) Attack Power'),
 ('armor',r'^(\d+) Armor'),
]
def parse(d):
    h=d['html']
    lines=re.findall(r'<tt-(?:line|double-line)[^>]*>(.*?)</tt-(?:line|double-line)>',h)
    out={'name':d['name'],'q':d['quality']}
    other=[]
    setpart=False
    for raw in lines:
        t=H.unescape(re.sub(r'<[^>]+>',' ',raw)).strip(); t=re.sub(r'\s+',' ',t)
        if 'Set:' in t or t.startswith('('): 
            if 'Set:' in t: other.append('SET '+t); continue
        m=re.match(r'Item Level (\d+)',t)
        if m: out['ilvl']=int(m.group(1)); continue
        m=re.match(r'Requires Level (\d+)',t)
        if m: out['req']=int(m.group(1)); continue
        m=re.match(r'(\d+) - (\d+) Damage Speed ([\d.]+)',t)
        if m: out['wdmg']=f"{m.group(1)}-{m.group(2)}"; out['speed']=float(m.group(3)); continue
        m=re.match(r'\(([\d.]+) damage per second\)',t)
        if m: out['dps']=float(m.group(1)); continue
        hit=False
        for k,p in PAT:
            m=re.search(p,t)
            if m:
                out[k]=out.get(k,0)+int(m.group(1)); hit=True; break
        if not hit and not re.match(r'(Binds|Durability|Sell Price|Unique|Classes)',t):
            other.append(t)
    out['other']=other
    return out
if __name__=='__main__':
    ids=sys.argv[1:]
    res=[]
    for i in ids:
        d=fetch(i)
        if not d: res.append({'id':i,'err':True}); continue
        p=parse(d); p['id']=i; res.append(p)
    print(json.dumps(res,indent=0))
