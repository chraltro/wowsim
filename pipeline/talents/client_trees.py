# Rebuild the nine WoW Forever talent trees from the client DB2 Trait* tables (build 1.60.1.70862, wago.tools CSV).
# This is an independent Python re-implementation of the placement rules that wowsims-forever documents in
# tools/database/tables.go (LoadTraitTalents): live tree per class = the tree with most nodes for that class mask,
# parked nodes (one coordinate 10x a lattice value) dropped, 600-px grid pitch, spec blocks split on X gaps > 1200,
# prerequisites from TraitEdge rows of Type 2 or 3. It does not run any wowsims code.
#
# Output: /home/claude/work/talents/client_trees.json
#   {class: {"tree_id":..,"tabs":[{"name":..,"talents":[{name,row,col,max,spell_id,definition_id,node_id,entry_id,prereq:[row,col]|None}]}]}}
import csv, json, collections, os, sys

W = '/home/claude/ext/wago_talents'
B = '70862'
OUT = '/home/claude/work/talents'
os.makedirs(OUT, exist_ok=True)

def rows(t):
    with open(f'{W}/{t}_{B}.csv', newline='') as f:
        return list(csv.DictReader(f))

I = int
spellname = {I(r['ID']): r['Name_lang'] for r in rows('SpellName')}
nodes = {I(r['ID']): r for r in rows('TraitNode')}
entries = {I(r['ID']): r for r in rows('TraitNodeEntry')}
defs = {I(r['ID']): r for r in rows('TraitDefinition')}
xref = rows('TraitNodeXTraitNodeEntry')
edges = [r for r in rows('TraitEdge') if r['Type'] in ('2', '3')]
tabs = rows('TalentTab')
sla = rows('SkillLineAbility')
skill = {I(r['ID']): r for r in rows('SkillLine')}

CLASS_MASK = {1: 'warrior', 2: 'paladin', 4: 'hunter', 8: 'rogue', 16: 'priest', 64: 'shaman', 128: 'mage', 256: 'warlock', 1024: 'druid'}

spell_classmask = collections.defaultdict(set)
spell_skill = collections.defaultdict(set)
for r in sla:
    sp = I(r['Spell'])
    if I(r['ClassMask']):
        spell_classmask[sp].add(I(r['ClassMask']))
    sl = skill.get(I(r['SkillLine']))
    if sl and sl['DisplayName_lang']:
        spell_skill[sp].add(sl['DisplayName_lang'])

# node -> list of (index, xref id, entry)
node_entries = collections.defaultdict(list)
for x in xref:
    node_entries[I(x['TraitNodeID'])].append((I(x['_Index']), I(x['ID']), I(x['TraitNodeEntryID'])))

def node_info(nid):
    lst = sorted(node_entries[nid])
    if not lst:
        return None
    idx, xid, eid = lst[0]          # lowest index = entry shown first in game (choice nodes)
    e = entries[eid]
    d = defs[I(e['TraitDefinitionID'])]
    sp = I(d['SpellID'])
    name = spellname.get(sp, '') or d['OverrideName_lang']
    return {'node_id': nid, 'entry_id': eid, 'definition_id': I(d['ID']), 'spell_id': sp,
            'max': I(e['MaxRanks']), 'name': name, 'x': I(nodes[nid]['PosX']), 'y': I(nodes[nid]['PosY']),
            'tree': I(nodes[nid]['TraitTreeID']), 'n_choices': len(lst)}

# class vote per tree
votes = collections.Counter()
tree_size = collections.Counter(I(n['TraitTreeID']) for n in nodes.values())
for nid in nodes:
    ni = node_info(nid)
    if not ni:
        continue
    for m in spell_classmask.get(ni['spell_id'], ()):
        votes[(ni['tree'], m)] += 1
best = {}
for (tree, m), c in votes.items():
    if tree not in best or c > best[tree][1]:
        best[tree] = (m, c)
live = {}
for tree, (m, c) in best.items():
    if m not in live or tree_size[tree] > tree_size[live[m]]:
        live[m] = tree

PITCH = 600
def parked_set():
    xs = collections.defaultdict(list); ys = collections.defaultdict(list)
    for n in nodes.values():
        xs[I(n['TraitTreeID'])].append(I(n['PosX'])); ys[I(n['TraitTreeID'])].append(I(n['PosY']))
    def near(v, others):
        return any(o != v and abs(o - v) <= PITCH for o in others)
    def parked(v, others):
        return (not near(v, others)) and v % 10 == 0 and near(v // 10, others)
    out = set()
    for nid, n in nodes.items():
        t = I(n['TraitTreeID'])
        if parked(I(n['PosX']), xs[t]) or parked(I(n['PosY']), ys[t]):
            out.add(nid)
    return out
parked = parked_set()

edge_pairs = {(I(e['LeftTraitNodeID']), I(e['RightTraitNodeID'])) for e in edges}

result = {}
log = []
for mask, tree in sorted(live.items()):
    cls = CLASS_MASK.get(mask)
    if not cls:
        continue
    tnodes = []
    for nid, n in nodes.items():
        if I(n['TraitTreeID']) != tree:
            continue
        if nid in parked:
            ni = node_info(nid); log.append(f'{cls}: parked node {nid} {ni and ni["name"]} at {n["PosX"]}/{n["PosY"]} dropped'); continue
        ni = node_info(nid)
        if not ni or not ni['spell_id'] or not ni['max'] or not ni['name']:
            log.append(f'{cls}: node {nid} skipped (no spell/ranks/name) {ni}'); continue
        tnodes.append(ni)
    xsorted = sorted({n['x'] for n in tnodes})
    origins = [x for i, x in enumerate(xsorted) if i == 0 or x - xsorted[i - 1] > 2 * PITCH]
    miny = min(n['y'] for n in tnodes)
    def tab_of(x):
        t = 0
        for i, o in enumerate(origins):
            if x >= o: t = i
        return t
    def gi(v, o):
        return (v - o + PITCH // 2) // PITCH
    for n in tnodes:
        t = tab_of(n['x'])
        n['tab'] = t; n['row'] = gi(n['y'], miny); n['col'] = gi(n['x'], origins[t])
        n['residual'] = abs(n['x'] - (origins[t] + n['col'] * PITCH)) + abs(n['y'] - (miny + n['row'] * PITCH))
    # one node per spell and per cell, closest to lattice wins
    def dedupe(lst, key, why):
        win = {}
        for n in lst:
            k = key(n)
            if k not in win or n['residual'] < win[k]['residual']:
                if k in win: log.append(f'{cls}: {why}: dropped {win[k]["name"]} node {win[k]["node_id"]} for {n["name"]} node {n["node_id"]}')
                win[k] = n
            else:
                log.append(f'{cls}: {why}: dropped {n["name"]} node {n["node_id"]} for {win[k]["name"]} node {win[k]["node_id"]}')
        keep = {id(v) for v in win.values()}
        return [n for n in lst if id(n) in keep]
    tnodes = dedupe(tnodes, lambda n: n['spell_id'], 'duplicate spell')
    tnodes = dedupe(tnodes, lambda n: (n['tab'], n['row'], n['col']), 'duplicate cell')
    byid = {n['node_id']: n for n in tnodes}
    # prereqs: edge left->right, drop mirrored pairs (keep the one running down the tree), lowest left id wins
    prereq = {}
    for (l, r) in sorted(edge_pairs, key=lambda p: (p[1], p[0])):
        if l not in byid or r not in byid:
            continue
        if (r, l) in edge_pairs:
            L, R = byid[l], byid[r]
            mirror = (L['y'] > R['y']) if L['y'] != R['y'] else (l > r)
            if mirror:
                continue
        if r in prereq and prereq[r] <= l:
            continue
        prereq[r] = l
    tab_rows = {I(t['OrderIndex']): t for t in tabs if I(t['ClassMask']) == mask}
    out_tabs = []
    for ti in range(len(origins)):
        tl = sorted([n for n in tnodes if n['tab'] == ti], key=lambda n: (n['row'], n['col']))
        tals = []
        for n in tl:
            p = prereq.get(n['node_id'])
            pr = None
            if p is not None:
                P = byid[p]
                if P['tab'] == n['tab']:
                    pr = [P['row'], P['col']]
                else:
                    log.append(f'{cls}: prereq of {n["name"]} sits in another tab')
            tals.append({'name': n['name'], 'row': n['row'], 'col': n['col'], 'max': n['max'], 'spell_id': n['spell_id'],
                         'definition_id': n['definition_id'], 'node_id': n['node_id'], 'entry_id': n['entry_id'],
                         'choice_entries': n['n_choices'], 'prereq': pr})
        tr = tab_rows.get(ti)
        out_tabs.append({'name': tr['Name_lang'] if tr else f'tab{ti}', 'talent_tab_id': I(tr['ID']) if tr else None, 'talents': tals})
    result[cls] = {'trait_tree_id': tree, 'class_mask': mask, 'tabs': out_tabs}

json.dump({'build': '1.60.1.70862', 'source': 'wago.tools DB2 CSV exports (TraitTree, TraitNode, TraitNodeEntry, TraitNodeXTraitNodeEntry, TraitDefinition, TraitEdge, SpellName, SkillLineAbility, SkillLine, TalentTab), fetched 2026-11-08',
           'classes': result, 'log': log}, open(f'{OUT}/client_trees.json', 'w'), indent=1)
for c, v in sorted(result.items()):
    print(c, v['trait_tree_id'], [(t['name'], len(t['talents']), sum(x['max'] for x in t['talents'])) for t in v['tabs']])
print(len(log), 'log lines')
for l in log: print('  ', l)
