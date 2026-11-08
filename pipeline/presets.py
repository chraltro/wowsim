import json, re, importlib.util, collections
spec=importlib.util.spec_from_file_location('b','/home/claude/scripts/build_dataset.py'); b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
D={x['id']:x for x in json.load(open('/home/claude/data/items_forever.json'))['items']}
byname={}
for it in b.items.values(): byname.setdefault(it['name'].lower(),[]).append(it['id'])
for x in D.values(): byname.setdefault(x['name'].lower(),[]).append(x['id'])
def rec(i):
    if i in D: return D[i]
    it=b.items.get(i)
    if not it: return None
    so=it['scalingOptions']['0']; st={b.STAT[int(k)]:v for k,v in so.get('stats',{}).items() if int(k) in b.STAT}
    lines=b.wh_lines(i)
    r={'id':i,'name':it['name'],'ilvl':so.get('ilvl'),'reqLvl':it.get('reqLvl'),'quality':it.get('quality'),'stats':st,'setName':it.get('setName'),'outsideDatasetScope':True}
    if it.get('type')==13 and it.get('weaponType') not in (5,7): r['weapon']={'min':so.get('weaponDamageMin'),'max':so.get('weaponDamageMax'),'speed':it.get('weaponSpeed'),'dps':round(so.get('unroundedDps',0),2)}
    if lines is None:
        import subprocess,os
        rr=subprocess.run(['curl','-sS','-m','30','-A','Mozilla/5.0',f'https://nether.wowhead.com/forever/tooltip/item/{i}'],capture_output=True,text=True)
        open(f'/home/claude/cache/wh/{i}.json','w').write(rr.stdout); lines=b.wh_lines(i)
    if lines: w=b.wh_parse(lines); r['setBonuses']=w['setBonuses']; r['effectsText']=w['effects']; r['sources']=[{'type':'drop','npc':w.get('droppedBy'),'dropChancePct':w.get('dropChancePct')}] if w.get('droppedBy') else []
    return r
KEYS=['int','spi','sta','healing','spellDamage','mp5','critRating','hitRating','str','agi','ap','armor']
def table(title, rows):
    tot=collections.Counter(); out=[]; sets=collections.Counter(); setb={}
    for slot,i in rows:
        r=rec(i) if isinstance(i,int) else None
        if r is None and isinstance(i,str):
            ids=byname.get(i.lower(),[]); r=rec(ids[0]) if ids else None
        if r is None: out.append({'slot':slot,'item':i,'missing':True}); continue
        for k in KEYS: tot[k]+=r['stats'].get(k,0)
        if r.get('setName'): sets[r['setName']]+=1; setb[r['setName']]=r.get('setBonuses',[])
        out.append({'slot':slot,'id':r['id'],'name':r['name'],'ilvl':r['ilvl'],'reqLvl':r['reqLvl'],'stats':{k:r['stats'].get(k,0) for k in KEYS if r['stats'].get(k)},'weapon':r.get('weapon'),'set':r.get('setName'),'effects':[e for e in r.get('effectsText',[]) if not re.search(r'Increases (healing|damage and healing|attack power)|Restores \+?\d+ mana|chance to hit by|critical strike by \d|\+\d+ Attack Power\.$',e)],
                    'source':[ {k:v for k,v in s.items() if k in ('type','npc','zone','quest','profession','skill','dropChancePct','faction','standing','questLevel')} for s in r.get('sources',[])][:2],
                    'outsideDatasetScope':r.get('outsideDatasetScope',False),'dataOrigin':r.get('dataOrigin')})
    active=[]
    for s,n in sets.items():
        for line in setb.get(s,[]):
            m=re.match(r'\((\d)\)',line)
            if m and int(m.group(1))<=n: active.append(f'{s} {n}pc: {line}')
    return {'title':title,'rows':out,'totals_items_only':dict(tot),'activeSetBonuses':active,'derived':{'critPct_fromRating':round(tot['critRating']/14,2),'hitPct_fromRating':round(tot['hitRating']/10,2)}}
P={}
P['resto_timesaver']=table('Timesaver.gg Resto Shaman L60 pre-raid BiS, Alliance column (data checked 2026-11-06)',[
 ('Head',252561),('Neck',19426),('Shoulder',16718),('Back',18510),('Chest',16666),('Wrist',252573),('Hands',20296),('Waist',279252),('Legs',16719),('Feet',16715),('Finger1',281635),('Finger2',273031),('Trinket1',10659),('Trinket2',744),('Main Hand',7721),('Off Hand',279262)])
P['resto_timesaver_l55']=table('Timesaver.gg Resto Shaman level-55 gear, Alliance column (data checked 2026-11-06)',[
 ('Head',12018),('Neck',10769),('Shoulder',9411),('Back',273825),('Chest',11194),('Wrist',18449),('Hands',16672),('Waist',15813),('Legs',274161),('Feet',273042),('Finger1',281635),('Finger2',273031),('Trinket1',10659),('Trinket2',744),('Main Hand',7721),('Off Hand',274290)])
P['resto_wowgg']=table('wow.gg Resto Shaman BiS (published 2026-11-04), 9 slots only',[
 ('Head','Crown of the Penitent'),('Shoulder','Wildheart Spaulders'),('Chest','Red Dragonscale Breastplate'),('Wrist','Virtuous Bracers'),('Hands','Green Dragonscale Gauntlets'),('Waist','Wisdom of the Timbermaw'),('Legs',"Senior Designer's Pantaloons"),('Feet','Virtuous Sandals'),('Two-Hand','Thorium Greatmace')])
P['enh_timesaver']=table('Timesaver.gg Enhancement Shaman L60 pre-raid BiS, Alliance column (data checked 2026-11-06)',[
 ('Head',252605),('Neck',22150),('Shoulder',15067),('Back',286994),('Chest',16666),('Wrist',279256),('Hands',15063),('Waist',18504),('Legs',15062),('Feet',16670),('Finger1',281635),('Finger2',18402),('Trinket1',249469),('Trinket2',10659),('Main Hand',279260)])
eq=json.load(open('/home/claude/data/repos/wowsims-forever/ui/specs/shaman/enhancement/builds/testing.build.json'))['player']['equipment']['items']
SL=['Head','Neck','Shoulder','Back','Chest','Wrist','Hands','Waist','Legs','Feet','Finger1','Finger2','Trinket1','Trinket2','Main Hand','Off Hand','Relic']
P['enh_wowsims_testing']=table('wowsims/forever Enhancement "Testing" gear set (devOnly preset, ui/specs/shaman/enhancement/builds/testing.build.json, commit 125e534 2026-11-08); enchants ignored',[(SL[k],e['id']) for k,e in enumerate(eq) if e.get('id')])
json.dump(P,open('/home/claude/data/presets/shaman_presets_resolved.json','w'),indent=1)
for k,v in P.items():
    print('=====',v['title'])
    for r in v['rows']:
        if r.get('missing'): print('  MISSING',r); continue
        print(f"  {r['slot']:<9} {r['id']:>6} {r['name'][:32]:<32} i{r['ilvl']} r{r['reqLvl']} {r['stats']} {('W '+str(r['weapon'])) if r.get('weapon') else ''} {'[set '+r['set']+']' if r.get('set') else ''} {r['source']} {'OUT-OF-SCOPE' if r['outsideDatasetScope'] else ''} {'SUPPL' if r.get('dataOrigin') else ''} {r['effects'][:2]}")
    print('  TOTAL', v['totals_items_only'], v['derived']); print('  SETS', v['activeSetBonuses'])
