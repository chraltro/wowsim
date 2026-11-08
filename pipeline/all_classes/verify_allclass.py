# Step 5: checks on wowsim/data/items_all.json
#  1. Shaman subset (items whose usableBy names shaman) vs the Shaman-only file: ids only in one of them, with the reason.
#  2. Spot-check: 10 random items per class (seed 20261108) against a fresh Wowhead Forever tooltip fetch
#     (cache/allclass/spotcheck/<id>.json): required level, item class/subclass (armor type / weapon subtype), primary stats,
#     armor, weapon damage and speed, and the tooltip's "Classes:" line against usableBy.
#  3. Whole-file subclass check against every cached Wowhead tooltip (<!--scstartC:S--> marker).
#  4. Counts per class, with a known source, with a drop chance.
# Output: cache/allclass/verify_report.json (+ printed summary)
import json, os, re, random, subprocess, time, collections
from common import WORK, OUT, SHAMAN_FILE, CACHE, CLASS_ORDER, NAME_TO_ID, load_build_dataset

b = load_build_dataset()
D = json.load(open(OUT)); S = json.load(open(SHAMAN_FILE))
items = {x['id']: x for x in D['items']}; old = {x['id']: x for x in S['items']}
rep = {}

# ---- 1. Shaman subset ----
sh = {i for i, x in items.items() if any(e['class'] == 'shaman' for e in x['usableBy'])}
only_old = sorted(set(old) - sh); only_new = sorted(sh - set(old))
def why_old(i):
    x = items.get(i); o = old[i]
    if x is None: return 'not in the new file at all'
    if o.get('hand') == 'Off Hand' and o.get('weaponType') not in ('Shield', 'Held In Off-hand'): return 'Off Hand-only weapon: Shaman cannot dual wield in Forever (DB2 Dual Wield row for Shaman is never-learned; wowsims has no Shaman dual-wield spec)'
    return 'usableBy has no shaman: ' + json.dumps({k: x.get(k) for k in ('slot', 'armorType', 'weaponType', 'hand', 'classAllowlist')})
rep['shamanSubset'] = {'shamanFileCount': len(old), 'newShamanSubsetCount': len(sh), 'sameIds': len(sh & set(old)),
                       'onlyInShamanFile': [{'id': i, 'name': old[i]['name'], 'reason': why_old(i)} for i in only_old],
                       'onlyInNewShamanSubset': [{'id': i, 'name': items[i]['name'], 'slot': items[i]['slot'], 'dataOrigin': items[i].get('dataOrigin')} for i in only_new]}
same_stats = sum(1 for i in sh & set(old) if items[i]['stats'] == old[i]['stats'])
same_src = sum(1 for i in sh & set(old) if items[i]['sources'] == old[i]['sources'])
def nores(d): return {k: v for k, v in d.items() if not k.endswith('Res')}
res_only = [i for i in sh & set(old) if items[i]['stats'] != old[i]['stats'] and nores(items[i]['stats']) == nores(old[i]['stats'])]
rep['shamanSubset']['sharedIdsStatsDifferOnlyByAddedResistances'] = len(res_only)
rep['shamanSubset']['sharedIdsStatsDifferOtherwise'] = [i for i in sh & set(old) if nores(items[i]['stats']) != nores(old[i]['stats'])]
other_keys = collections.Counter(k for i in sh & set(old) for k in set(old[i]) | set(items[i]) if k not in ('usableBy', 'equipSlots', 'weaponSubtype', 'rangedType', 'stats', 'itemType', 'weaponType', 'classAllowlist', 'classAllowlistSource') and old[i].get(k) != items[i].get(k))
rep['shamanSubset']['sharedIdsOtherFieldDiffs'] = dict(other_keys)
rep['shamanSubset']['sharedIdsIdenticalStats'] = same_stats; rep['shamanSubset']['sharedIdsIdenticalSources'] = same_src
diff_src = [i for i in sh & set(old) if items[i]['sources'] != old[i]['sources']]
rep['shamanSubset']['sourceDiffSample'] = [{'id': i, 'name': items[i]['name'], 'old': old[i]['sources'], 'new': items[i]['sources']} for i in diff_src[:5]]

# ---- helpers on Wowhead tooltips ----
WSUB = ['One-Handed Axe', 'Two-Handed Axe', 'Bow', 'Gun', 'One-Handed Mace', 'Two-Handed Mace', 'Polearm', 'One-Handed Sword', 'Two-Handed Sword', 'Warglaive',
        'Staff', 'Exotic', 'Exotic2', 'Fist Weapon', 'Miscellaneous', 'Dagger', 'Thrown', 'Spear', 'Crossbow', 'Wand', 'Fishing Pole']   # enums.go ITEM_SUBCLASS_WEAPON_* order
ASUB = ['Miscellaneous', 'Cloth', 'Leather', 'Mail', 'Plate', 'Cosmetic', 'Shield', 'Libram', 'Idol', 'Totem']                      # ITEM_SUBCLASS_ARMOR_* order
CN = '(?:Warrior|Paladin|Hunter|Rogue|Priest|Shaman|Mage|Warlock|Druid)'
CLASSES_RE = re.compile(r'Classes: (' + CN + '(?:, ' + CN + ')*)')
SLOT_RE = re.compile(r'<td>(Head|Neck|Shoulder|Back|Chest|Wrist|Hands|Waist|Legs|Feet|Finger|Trinket|One-Hand|Main Hand|Off Hand|Two-Hand|Held In Off-hand|Ranged|Thrown|Relic|Shield)</td>')
def slot_ok(x, t):
    m = SLOT_RE.search(t)
    if not m: return None
    s = m.group(1)
    if s == 'Thrown': s = 'Ranged'
    if s == 'Relic': return x['slot'].startswith('Relic')
    if s == 'Off Hand' and x['slot'] == 'Shield': return True
    return s == x['slot']
def tt(path):
    if not os.path.exists(path): return None
    d = json.load(open(path)); return None if '__404__' in d else d['tooltip']
def wh_class(t):
    m = re.search(r'<!--scstart(\d+):(\d+)-->', t)
    if not m: return None
    c, s = int(m.group(1)), int(m.group(2))
    return ('weapon', WSUB[s]) if c == 2 and s < len(WSUB) else ('armor', ASUB[s]) if c == 4 and s < len(ASUB) else (c, s)
def expected_kind(x):
    if x.get('weaponSubtype') in ('Shield', 'Held In Off-hand'): return ('armor', 'Shield' if x['weaponSubtype'] == 'Shield' else 'Miscellaneous')
    if x.get('rangedType') in ('Idol', 'Libram', 'Totem'): return ('armor', x['rangedType'])
    if x.get('weaponSubtype'): return ('weapon', x['weaponSubtype'])
    return ('armor', x.get('armorType') or 'Miscellaneous')
def subclass_ok(x, k):
    e = expected_kind(x)
    if e == k: return True
    return e == ('armor', 'Miscellaneous') and k in (('armor', 'Cloth'), ('armor', 'Miscellaneous'))   # neck/finger/trinket/cloak: misc or cloth in the client


# ---- 2. spot-check, fresh fetch ----
SP = os.path.join(WORK, 'spotcheck'); os.makedirs(SP, exist_ok=True)
def fetch(i):
    p = os.path.join(SP, f'{i}.json')
    if os.path.exists(p): return p
    for a in range(4):
        r = subprocess.run(['curl', '-sS', '-m', '30', '-A', 'Mozilla/5.0', '-w', '\n%{http_code}', f'https://nether.wowhead.com/forever/tooltip/item/{i}'], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n'); time.sleep(0.3)
        if code == '200': open(p, 'w').write(body); return p
        if code == '404': open(p, 'w').write('{"__404__":true}'); return p
        time.sleep(2 * (a + 1))
    return None
rng = random.Random(20261108)
spot = {}; tally = collections.Counter()
for c in CLASS_ORDER:
    pool = sorted(i for i, x in items.items() if any(e['class'] == c for e in x['usableBy']))
    pick = rng.sample(pool, 10); res = []
    for i in pick:
        x = items[i]; p = fetch(i); t = tt(p) if p else None
        r = {'id': i, 'name': x['name'], 'slot': x['slot'], 'reqLvl': x.get('reqLvl'), 'fromLevel': next(e.get('fromLevel') for e in x['usableBy'] if e['class'] == c)}
        if t is None: r['result'] = 'no Wowhead tooltip'; tally['no tooltip'] += 1; res.append(r); continue
        chk = {}
        m = re.search(r'<!--rlvl-->(\d+)', t); whl = int(m.group(1)) if m else None
        chk['reqLvl'] = 'ok' if whl == x.get('reqLvl') or (whl is None and x.get('reqLvl') in (None, 1)) else {'file': x.get('reqLvl'), 'wowhead': whl}
        k = wh_class(t)
        if k: chk['subclass'] = 'ok' if subclass_ok(x, k) else {'file': expected_kind(x), 'wowhead': k}
        so = slot_ok(x, t); chk['slot'] = 'ok' if so else {'file': x['slot'], 'wowhead': (SLOT_RE.search(t) or [None, None])[1] if so is not None else 'no slot text'}
        w = b.wh_parse(b.wh_lines(i) if os.path.exists(os.path.join(CACHE, 'wh', f'{i}.json')) else [])  # parse helper needs lines; re-parse the fresh text below
        lines = [l for l in (re.sub(r'\s+', ' ', z).strip() for z in re.sub(r'<[^>]+>', ' ', re.sub(r'<br\s*/?>|</(tr|div|table)>', '\n', t)).split('\n')) if l]
        import html as _h; lines = [_h.unescape(l) for l in lines]
        w = b.wh_parse(lines)
        sd = {}
        for s in ('str', 'agi', 'sta', 'int', 'spi'):
            if abs(x['stats'].get(s, 0) - w['stats'].get(s, 0)) > 0.5: sd[s] = {'file': x['stats'].get(s, 0), 'wowhead': w['stats'].get(s, 0)}
        m = re.search(r'<!--amr-->(\d+) Armor', t)   # base armor; green "+N Armor" lines are bonus armor (wowsims bonusArmor)
        if m and x['stats'].get('armor', 0) != int(m.group(1)): sd['armor'] = {'file': x['stats'].get('armor', 0), 'wowhead': int(m.group(1))}
        bonus = sum(int(z) for z in re.findall(r'^\+(\d+) Armor$', '\n'.join(lines), re.M))
        if bonus != x['stats'].get('bonusArmor', 0): sd['bonusArmor'] = {'file': x['stats'].get('bonusArmor', 0), 'wowhead': bonus}
        chk['stats'] = sd or 'ok'
        DM = r'^(\d+)(?: - (\d+))? (?:\w+ )?Damage'
        dm = next((re.match(DM, l) for l in lines if re.match(DM, l)), None)
        if dm or x.get('weapon'):
            fw = x.get('weapon') or {}
            sp = re.search(r'Speed ([\d.]+)', ' '.join(lines))
            wl, wh_ = (int(dm.group(1)), int(dm.group(2) or dm.group(1))) if dm else (None, None)
            ok = dm and fw.get('min') == wl and fw.get('max') == wh_ and (not sp or abs((fw.get('speed') or 0) - float(sp.group(1))) < 0.005)
            chk['weapon'] = 'ok' if ok else {'file': [fw.get('min'), fw.get('max'), fw.get('speed')], 'wowhead': [wl, wh_, float(sp.group(1)) if sp else None] if dm else None}
        cl = CLASSES_RE.search(' '.join(lines))
        if cl:
            allowed = {z.strip().lower() for z in cl.group(1).split(',')}
            ub = {e['class'] for e in x['usableBy']}
            chk['classes'] = 'ok' if ub <= allowed else {'usableBy': sorted(ub), 'wowhead': sorted(allowed)}
        r['checks'] = chk
        bad = [k2 for k2, v in chk.items() if v != 'ok']
        r['result'] = 'match' if not bad else 'mismatch: ' + ','.join(bad)
        tally['match' if not bad else 'mismatch'] += 1
        for k2 in bad: tally['mismatch.' + k2] += 1
        res.append(r)
    spot[c] = res
rep['spotCheck'] = {'seed': 20261108, 'tally': dict(tally), 'perClass': spot}

# ---- 3. whole-file subclass check against cached tooltips ----
sc = collections.Counter(); bad = []; badlvl = []; badslot = []; badcls = []
for i, x in items.items():
    t = tt(os.path.join(CACHE, 'wh', f'{i}.json'))
    if t is None: sc['no cached tooltip'] += 1; continue
    k = wh_class(t)
    if k is None: sc['no subclass marker'] += 1
    elif subclass_ok(x, k): sc['subclass match'] += 1
    else: sc['subclass mismatch'] += 1; bad.append({'id': i, 'name': x['name'], 'file': expected_kind(x), 'wowhead': k})
    m = re.search(r'<!--rlvl-->(\d+)', t); whl = int(m.group(1)) if m else None
    ok = whl == x.get('reqLvl') or (whl is None and x.get('reqLvl') in (None, 1))
    sc['reqLvl match' if ok else 'reqLvl mismatch'] += 1
    if not ok: badlvl.append({'id': i, 'name': x['name'], 'file': x.get('reqLvl'), 'wowhead': whl, 'dataOrigin': x.get('dataOrigin')})
    so = slot_ok(x, t)
    sc['slot ' + ('no slot text' if so is None else 'match' if so else 'mismatch')] += 1
    if so is False: badslot.append({'id': i, 'name': x['name'], 'file': x['slot'], 'wowhead': SLOT_RE.search(t).group(1)})
    m = re.search(r'<!--amr-->(\d+) Armor', t)
    if m: sc['armor match' if x['stats'].get('armor', 0) == int(m.group(1)) else 'armor mismatch'] += 1
    plain = re.sub(r'<[^>]+>', '', t); cl = CLASSES_RE.search(plain)
    if cl:
        allowed = {z.strip().lower() for z in cl.group(1).split(',')}; ub = {e['class'] for e in x['usableBy']}
        sc['classes line respected' if ub <= allowed else 'classes line violated'] += 1
        if not ub <= allowed: badcls.append({'id': i, 'name': x['name'], 'usableBy': sorted(ub), 'wowhead': sorted(allowed)})
rep['subclassCheck'] = {'counts': dict(sc), 'subclassMismatches': bad, 'reqLvlMismatches': badlvl, 'slotMismatches': badslot, 'classLineViolations': badcls}

# ---- 4. counts ----
rep['counts'] = D['meta']['coverage']
json.dump(rep, open(os.path.join(WORK, 'verify_report.json'), 'w'), indent=1, ensure_ascii=False)
print('SHAMAN', {k: v for k, v in rep['shamanSubset'].items() if k not in ('onlyInShamanFile', 'onlyInNewShamanSubset', 'sourceDiffSample')})
print('COUNTS', json.dumps(rep['counts']['perClass']))
print('  only in Shaman file', [(z['id'], z['name'], z['reason'][:60]) for z in rep['shamanSubset']['onlyInShamanFile']])
print('  only in new subset', [(z['id'], z['name'], z['slot']) for z in rep['shamanSubset']['onlyInNewShamanSubset']])
print('SPOT', dict(tally))
for c, res in spot.items():
    for r in res:
        if r['result'] != 'match': print('  ', c, r['id'], r['name'], r['result'], json.dumps(r.get('checks'))[:300])
print('WHOLE FILE', dict(sc))
print('  subclass mismatches', collections.Counter((tuple(z['file']), tuple(z['wowhead']) if isinstance(z['wowhead'], tuple) else str(z['wowhead'])) for z in bad))
print('  reqLvl mismatches', len(badlvl), badlvl[:12]); print('  slot mismatches', len(badslot), badslot[:12]); print('  class-line violations', len(badcls), badcls[:12])
