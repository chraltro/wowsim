import json
D=json.load(open('/home/claude/data/items_forever.json'))['items']
RAIDZ={"Naxxramas","Ahn'Qiraj","Ruins of Ahn'Qiraj","Temple of Ahn'Qiraj","Gates of Ahn'Qiraj","Zul'Gurub","Molten Core","Blackwing Lair","Onyxia's Lair","Silithus"}
BADV={'Lieutenant Jackspring'}; BADREP={'Brood of Nozdormu','Zandalar Tribe'}
RAIDQ=('The Lord of Blackrock','The Nightmare Manifests','Onyxia','Paragons of Power')
def avail(s):
    t=s['type']
    if t=='drop': return s.get('instanceType')!='raid' and s.get('zone') not in RAIDZ
    if t=='quest': return s.get('zone') not in RAIDZ and not any(q in (s.get('quest') or '') for q in RAIDQ)
    if t=='vendor': return s.get('npc') not in BADV
    if t=='reputation': return s.get('faction') not in BADREP
    if t=='pvp': return False
    return True
def ok(x):
    if x['quality']<3: return False
    if x.get('reqLvl') is None and (x['ilvl'] or 0)<55: return False
    if x.get('reqLvl') is not None and x['reqLvl']<50: return False
    if not x['sources'] or not any(avail(s) for s in x['sources']): return False
    return True
def src(x):
    s=[s for s in x['sources'] if avail(s)][0]; t=s['type']
    if t=='drop': return f"{s.get('npc') or s.get('other')}, {s.get('zone')}" + (f" {s['dropChancePct']:.0f}%" if s.get('dropChancePct') else '')
    if t=='quest': return f"Q {s['quest']} ({s.get('zone')})"
    if t=='crafted': return f"{s.get('profession')} {s.get('skill')}"
    if t=='vendor': return f"vendor {s.get('npc')} ({s.get('zone')})"
    if t=='reputation': return f"{s.get('faction')} {s.get('standing')}"
    return t
SLOTS=['Head','Neck','Shoulder','Back','Chest','Wrist','Hands','Waist','Legs','Feet','Finger','Trinket','Main Hand/One-Hand','Shield/Off-hand','Two-Hand','Relic (Totem)']
out={}
for sl in SLOTS:
    if sl=='Main Hand/One-Hand': c=[x for x in D if x['slot'] in ('Main Hand','One-Hand')]
    elif sl=='Shield/Off-hand': c=[x for x in D if x['slot'] in ('Shield','Held In Off-hand')]
    else: c=[x for x in D if x['slot']==sl]
    c=[x for x in c if ok(x) and (x['stats'].get('healing',0)>0 or x['stats'].get('mp5',0)>0 or sl in ('Trinket','Relic (Totem)'))]
    c.sort(key=lambda x:(-x['stats'].get('healing',0), -(x['stats'].get('int',0)+x['stats'].get('spi',0))))
    out[sl]=[{'id':x['id'],'name':x['name'],'ilvl':x['ilvl'],'reqLvl':x['reqLvl'],'quality':x['quality'],'armorType':x['armorType'],
              'stats':{k:v for k,v in x['stats'].items() if k in ('int','spi','sta','healing','spellDamage','mp5','critRating','hitRating')},
              'weapon':x.get('weapon'),'source':src(x),'effects':[e for e in x.get('effectsText',[]) if e.startswith(('Use:','Chance','Equip:')) and not any(w in e for w in ('Increases healing','Increases damage and healing','Restores','chance to hit','critical strike by'))][:1],'lowConfidence':bool(x.get('dataOrigin'))} for x in c[:6]]
json.dump({'note':'Constructed sample, not a published list. Ranked by bonus healing, then Int+Spirit. Sources limited to dungeons, crafting, non-raid quests, vendors, reputation (raid, AQ/Silithus, ZG, Naxx, PvP excluded). quality>=3, reqLvl>=50 (or none with ilvl>=55), Alliance-usable. From /home/claude/data/items_forever.json.','slots':out},open('/home/claude/data/presets/resto_slot_samples.json','w'),indent=1)
for sl,v in out.items():
    print('==',sl)
    for r in v[:5]:
        st=r['stats']; w=r['weapon']
        print(f"  {r['id']}|{r['name']}|{r['armorType'] or ''}|i{r['ilvl']} r{r['reqLvl']} q{r['quality']}|Int {st.get('int',0)} Spi {st.get('spi',0)} Sta {st.get('sta',0)} Heal {st.get('healing',0)} Dmg {st.get('spellDamage',0)} mp5 {st.get('mp5',0)} crit {st.get('critRating',0)} hit {st.get('hitRating',0)}|{('%s-%s %s'%(w['min'],w['max'],w['speed'])) if w else ''}|{r['source']}|{'LOWCONF' if r['lowConfidence'] else ''}|{r['effects']}")
