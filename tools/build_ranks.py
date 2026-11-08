#!/usr/bin/env python3
"""Turn shaman_ranks.json (+ shaman_levels.json when present) into compact level data for the page."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, 'data/shaman_ranks.json')))['spells']
def eff(e):
    return {'b':e.get('base_points') or 0, 'p':e.get('points_per_level') or 0, 'bl':e.get('scaling_base_level') or 0, 'ml':e.get('scaling_max_level') or 0}
def cost(r):
    c = r.get('cost') or {}
    return {'mana':c.get('mana'), 'pct':c.get('pct_base_mana')}
def first(effects, pred):
    for e in effects:
        if pred(e): return e
    return None
def direct(name):
    out = []
    for r in R[name]['ranks']:
        e = first(r['effects'], lambda e: e['type'] in ('E_HEAL','E_SCHOOL_DAMAGE'))
        d = {'l':r['learn_level'], 'cast':(r.get('cast_ms') or 0)/1000, 'book':r.get('book_rank', False), 'v':e.get('variance') or 0, 'c':e.get('sp_coef') or 0, **eff(e), **cost(r)}
        out.append(d)
    return out
def linked_eff(r, pred):
    for L in (r.get('linked') or r.get('extra',{}).get('linked') or []):
        e = first(L.get('effects',[]), pred)
        if e: return e, L
    return None, None
OUT = {}
for k, n in [('hw','HealingWave'),('lhw','LesserHealingWave'),('ch','ChainHeal'),('lb','LightningBolt'),('es','EarthShock')]:
    OUT[k] = direct(n)
# Flame Shock: direct + DoT
fs = []
for r in R['FlameShock']['ranks']:
    d = first(r['effects'], lambda e: e['type']=='E_SCHOOL_DAMAGE')
    t = first(r['effects'], lambda e: e.get('aura')=='A_PERIODIC_DAMAGE')
    fs.append({'l':r['learn_level'], 'book':r.get('book_rank',False), 'c':d.get('sp_coef') or 0, **eff(d), 'tick':t['base_points'], 'ticks':t.get('ticks') or 4, 'tc':t.get('sp_coef') or 0, **cost(r)})
OUT['fs'] = fs
# Riptide: HoT
rt = []
for r in R['Riptide']['ranks']:
    t = first(r['effects'], lambda e: e.get('aura')=='A_PERIODIC_HEAL')
    rt.append({'l':r['learn_level'] if r['rank']!='Rank 1' else 40, 'ticks':t.get('ticks') or 5, 'period':(t.get('period_ms') or 3000)/1000, 'c':t.get('sp_coef') or 0, **eff(t), **cost(r)})
OUT['rt'] = rt
# Totems with linked periodic auras
def totem(name, aura):
    out = []
    for r in R[name]['ranks']:
        e, L = linked_eff(r, lambda e: e.get('aura')==aura)
        if not e: continue
        per = (e.get('period_ms') or L.get('period_ms') or (2000 if name!='ManaTideTotem' else 3000))/1000
        out.append({'l':r['learn_level'], 'tick':e['base_points'], 'p':e.get('points_per_level') or 0, 'bl':e.get('scaling_base_level') or 0, 'ml':e.get('scaling_max_level') or 0, 'c':e.get('sp_coef') or 0, 'period':per, **cost(r)})
    return out
OUT['hst'] = totem('HealingStreamTotem','A_PERIODIC_HEAL')
OUT['ms'] = totem('ManaSpringTotem','A_PERIODIC_ENERGIZE')
OUT['mtt'] = totem('ManaTideTotem','A_PERIODIC_ENERGIZE')
for m in OUT['mtt']: m['ticks'] = 4
if OUT['mtt']: OUT['mtt'][0]['l'] = 25
# Weapon imbues
wf = []
for r in R['WindfuryWeapon']['ranks']:
    e, L = linked_eff(r, lambda e: e.get('aura')=='A_MOD_ATTACK_POWER')
    wf.append({'l':r['learn_level'], **(eff(e) if e else {'b':0,'p':0,'bl':0,'ml':0}), **cost(r)})
OUT['wf'] = wf
ft = []
for r in R['FlametongueWeapon']['ranks']:
    e, L = linked_eff(r, lambda e: e['type']=='E_DUMMY' and (e.get('base_points') or 0) > 0)
    ft.append({'l':r['learn_level'], **(eff(e) if e else {'b':0,'p':0,'bl':0,'ml':0}), **cost(r)})
OUT['ft'] = ft
rb = []
for r in R['RockbiterWeapon']['ranks']:
    e, L = linked_eff(r, lambda e: e.get('aura')=='A_MOD_ATTACK_POWER')
    rb.append({'l':r['learn_level'], **(eff(e) if e else {'b':0,'p':0,'bl':0,'ml':0}), **cost(r)})
OUT['rb'] = rb
json.dump(OUT, open(os.path.join(ROOT, 'src/ranks.json'),'w'), indent=0)
for k,v in OUT.items(): print(k, len(v), v[0], v[-1])
