"""Build data/crafts.json for the Craft Profits page from the inputs fetch_inputs.sh downloads into raw/.

Recipes and reagents: AHledger's crafting endpoint. Skill levels, recipe items, item names, qualities and
vendor prices: the Forever client tables (via wago.tools). Which vendors sell an item, per faction: MetaBot's
item pages (Classic vendor lists). Learn skill for trainer recipes: MetaBot's profession tables.
Reference prices for trimming: the median of each house's median, per region, from AHledger price tables.
"""
import json, csv, glob, re, os, sys, collections, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from parse_mb import parse as parse_mb
from parse_prof import parse as parse_prof
csv.field_size_limit(10**9)
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'raw')
MARKET = 'forever.rppvp.alliance.eu'   # the house whose scan is built into the page
BUILD = '1.60.1.70862'
os.chdir(RAW)
QMAP={'POOR':0,'COMMON':1,'UNCOMMON':2,'RARE':3,'EPIC':4,'LEGENDARY':5,'ARTIFACT':6,'HEIRLOOM':7}
# --- game data
sp={int(r['ID']):r for r in csv.DictReader(open('ItemSparse.csv',encoding='utf-8',errors='ignore'))}
icls={int(r['ID']):(int(r['ClassID']),int(r['SubclassID'])) for r in csv.DictReader(open('Item.csv',encoding='utf-8',errors='ignore'))}
sla={}
for r in csv.DictReader(open('SkillLineAbility.csv')):
    sla.setdefault(int(r['Spell']),r)
eff={}
for r in csv.DictReader(open('ItemEffect.csv')):
    if r['TriggerType']=='6': eff[int(r['ID'])]=int(r['SpellID'])
spell2items=collections.defaultdict(list)
for r in csv.DictReader(open('ItemXItemEffect.csv')):
    e=int(r['ItemEffectID'])
    if e in eff: spell2items[eff[e]].append(int(r['ItemID']))
# --- AHledger recipes
recs=[]
for f in sorted(glob.glob('crafting_*.json')):
    recs+=json.load(open(f))['recipes']
# dedupe by spellId
byspell={}
for x in recs: byspell.setdefault(x['recipe']['spellId'],x)
recs=list(byspell.values())
# --- metabot profession tables
mbrows=[]
for f in glob.glob('mbprof/*.html'):
    mbrows+=parse_prof(f)
mb_by_key={}; mb_by_name=collections.defaultdict(list)
for r in mbrows:
    k=(r['name'].lower(), tuple(sorted((a.lower(),q) for a,q in r['reagents'])))
    mb_by_key.setdefault(k,r); mb_by_name[r['name'].lower()].append(r)
# --- AHledger item fallbacks
ahl={}
for f in glob.glob('ahl_items/*.json'):
    try:
        d=json.load(open(f)); 
        if 'id' in d: ahl[d['id']]=d
    except Exception: pass
# --- metabot vendor data
mbv={}
for f in glob.glob('mb/*.html'):
    i=int(os.path.basename(f).split('.')[0])
    try: mbv[i]=parse_mb(f)
    except Exception as e: mbv[i]={'ok':False}
# names from crafting data
cname={}; cqual={}
for x in recs:
    cname[x['result']['id']]=x['result']['name']; cqual[x['result']['id']]=QMAP.get(x['result']['quality'],1)
    for g in x['reagents']: cname.setdefault(g['id'],g['name'])
PROFS=['Alchemy','Blacksmithing','Cooking','Enchanting','Engineering','First Aid','Leatherworking','Mining','Tailoring','Herbalism','Skinning']
R=[]; stats=collections.Counter(); need_items=set()
for x in recs:
    rc=x['recipe']; res=x['result']; sid=rc['spellId']
    s=sla.get(sid)
    yellow=int(s['TrivialSkillLineRankLow']) if s else None
    grey=int(s['TrivialSkillLineRankHigh']) if s else None
    acq=int(s['AcquireMethod']) if s else None
    ritems=[i for i in spell2items.get(sid,[]) if icls.get(i,(0,0))[0]==9]
    ritem=ritems[0] if ritems else 0
    rlearn=int(sp[ritem]['RequiredSkillRank']) if ritem and ritem in sp and sp[ritem]['RequiredSkillRank'] not in ('','0') else None
    key=(rc['name'].lower(), tuple(sorted((g['name'].lower(),g['qty']) for g in x['reagents'])))
    m=mb_by_key.get(key)
    if not m and len(mb_by_name.get(rc['name'].lower(),[]))==1: m=mb_by_name[rc['name'].lower()][0]
    if rlearn: learn=rlearn; stats['learn_item']+=1
    elif m: learn=m['learn']; stats['learn_mb']+=1
    elif yellow: learn=max(1,yellow-40); stats['learn_est']+=1
    else: learn=rc['skillRequired'] or 1; stats['learn_ahl']+=1
    if acq==1 or (m and m['source']=='Auto'): src=0
    elif ritem or (m and m['source']=='Recipe'): src=2
    else: src=1
    stats[('src',src)]+=1
    if not yellow and m: yellow=m['yellow']; grey=m['grey']
    reag=[]
    for g in x['reagents']:
        reag+= [g['id'],g['qty']]; need_items.add(g['id'])
    need_items.add(res['id'])
    if ritem: need_items.add(ritem)
    nm=rc['name'] if rc['name']!=res['name'] else 0
    R.append([sid,nm,PROFS.index(rc['profession']),learn,yellow or 0,grey or 0,src,ritem,res['id'],res['qtyMin'],res['qtyMax'],reag])
print(stats)
# --- price tables
def pt_ids(path):
    return [int(l.split(':')[0]) for l in open(path).read().strip().split('\n')[1:] if l]
mine=set(pt_ids('pt/'+MARKET+'.txt'))
union=set()
for f in glob.glob('pt/*.txt'): union|=set(pt_ids(f))
# --- crates, writs and Merchant's Favor recipes (guides.json, from parse_guides.py)
G=json.load(open(os.path.join(HERE,'guides.json')))
byname={}
for i,row in sp.items(): byname.setdefault(row['Display_lang'].lower(),i)
gmiss=[]
def find(name):
    i=byname.get(name.lower())
    if i is None: gmiss.append(name)
    return i
TIERS=['Apprentice','Journeyman','Expert','Artisan']
CRATES=[]
for c in G['crates']:
    cid=find(c['name'])
    if cid is None: continue
    fills=[]
    for nm,qty in c['fills']:
        fid=find(nm)
        if fid is not None: fills+=[fid,qty]
    quality=sp[cid]['OverallQualityID']
    CRATES.append([cid,TIERS.index(c['tier']),c['level'],G['favor_per_crate'].get(c['tier'],{}).get(quality,0),fills])
WRIT={}
for w in G['writs']:
    wid=find(w['item'])
    if wid is not None: WRIT[wid]=w['rep']
FAV={}
for r in G['favor_recipes']:
    fid=find(r['name'])
    if fid is not None: FAV[fid]=[r['favor'],1 if r['rep'] else 0]
guide_ids=set(c[0] for c in CRATES)|set(i for c in CRATES for i in c[4][0::2])|set(WRIT)|set(FAV)
print('guides: crates',len(CRATES),'writ items',len(WRIT),'favor recipes',len(FAV),'unresolved',len(gmiss),gmiss[:12])
ids=need_items|mine|(union&set(sp))|guide_ids
CLSNAME={'Consumable':0,'Container':1,'Weapon':2,'Armor':4,'Reagent':5,'Projectile':6,'Trade Goods':7,'Tradeskill':7,'Recipe':9,'Quiver':11,'Quest':12,'Key':13,'Miscellaneous':15}
I={}; vstats=collections.Counter()
for i in sorted(ids):
    row=sp.get(i); a=ahl.get(i)
    name=(row['Display_lang'] if row else None) or cname.get(i) or (a['name'] if a else None)
    if not name: vstats['noname']+=1; continue
    q=int(row['OverallQualityID']) if row else (cqual.get(i) if i in cqual else QMAP.get((a or {}).get('quality','COMMON'),1))
    sell=int(row['SellPrice']) if row else int((a or {}).get('vendorSell') or 0)
    bop=1 if row and row['Bonding']=='1' else 0
    vunit=0; fac=0; lim=0
    v=mbv.get(i)
    if v and v.get('ok') and v.get('vendors'):
        t=(v.get('title') or '').lower()
        if not t.startswith(name.lower()[:20]):
            vstats['title_mismatch']+=1
        else:
            vs=v['vendors']
            A=any(x['faction'] in ('Alliance',None) for x in vs)
            H=any(x['faction'] in ('Horde',None) for x in vs)
            fac=(1 if A else 0)|(2 if H else 0)
            stocks=[x['stock'] for x in vs]
            lim=0 if any(s=='Always in stock' for s in stocks) else 1
            if row and row['BuyPrice'] not in ('','0'):
                bp=int(row['BuyPrice']); vsc=max(1,int(row['VendorStackCount'] or 1))
                vunit=bp/vsc
                mp=v.get('desc_price') or v.get('faq_price')
                if mp and mp not in (bp, round(bp/vsc)): vstats['price_mismatch']+=1
            else:
                vunit=v.get('desc_price') or v.get('faq_price') or 0
            if vunit and fac: vstats['vendor_sold']+=1
            else: fac=0
    kind=icls[i][0] if i in icls else CLSNAME.get((a or {}).get('itemClass',''),15)
    ilvl=int(row['ItemLevel'] or 0) if row else int((a or {}).get('level') or 0)
    I[i]=[name,q,sell,round(vunit,2) if vunit else 0,fac,lim,bop,kind,ilvl]
print(vstats, 'items',len(I))
snap=open('pt/'+MARKET+'.txt').read().strip()
# --- cross-house reference prices: median of each house's median, per region, needs 3+ houses
import statistics
reg_vals={'eu':collections.defaultdict(list),'us':collections.defaultdict(list)}
for f in glob.glob('pt/*.txt'):
    lines=open(f).read().strip().split('\n')
    mk=lines[0].split('|')[1].split('/')
    region=mk[3]
    if region not in reg_vals: continue
    for l in lines[1:]:
        p=l.split(':')
        if len(p)>2 and p[1]:
            reg_vals[region][int(p[0])].append(int(p[1]))
sale_ids=set(r[8] for r in R)|set(i for i,v in I.items() if v[3])|set(r[7] for r in R if r[7])|guide_ids
REF={}
for region,vals in reg_vals.items():
    REF[region]={i:round(statistics.median(v)) for i,v in vals.items() if i in sale_ids and len(v)>=3}
print('refs',{k:len(v) for k,v in REF.items()})
# --- how fast things sell: units sold a day per unit listed, median over the region's houses that report sales
turn={'eu':collections.defaultdict(list),'us':collections.defaultdict(list)}
for f in glob.glob('pt/*.txt'):
    lines=open(f).read().strip().split('\n')
    region=lines[0].split('|')[1].split('/')[3]
    if region not in turn: continue
    rows=[l.split(':') for l in lines[1:]]
    if not any(len(p)>8 and p[8]!='' for p in rows): continue      # this house has no sales estimate yet
    for p in rows:
        if len(p)>8 and p[8]!='' and p[3] not in ('','0'):
            turn[region][int(p[0])].append(int(p[8])/10/int(p[3]))
TURN={}
for region,vals in turn.items():
    TURN[region]={i:round(statistics.median(v),3) for i,v in vals.items() if i in sale_ids and len(v)>=2}
print('turnover',{k:len(v) for k,v in TURN.items()})
out={'build':BUILD,'generated':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'profs':PROFS,'R':R,'I':I,'ref':REF,'turn':TURN,'crates':CRATES,'writ':WRIT,'fav':FAV,'snap':snap}
dest=os.path.join(ROOT,'data','crafts.json')
json.dump(out,open(dest,'w'),separators=(',',':'),ensure_ascii=False)
print('bytes',os.path.getsize(dest))
