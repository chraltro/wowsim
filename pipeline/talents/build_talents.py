# Build /home/claude/wowsim/data/talents/<class>.json for the nine classes from the Forever client tables
# (build 1.60.1.70862), with cross-checks against wowsims-forever, timesaver.gg, Warcraft DB and wowforevertalents.com.
import json, csv, re, sys, collections, datetime, os
sys.path.insert(0, '/home/claude/wowsim/pipeline/talents')
import lib
from talent_text import Client, resolve

TODAY = '2026-11-08'
OUTDIR = '/home/claude/wowsim/data/talents'
os.makedirs(OUTDIR, exist_ok=True)
W = '/home/claude/ext/wago_talents'
WS = '/home/claude/data/repos/wowsims-forever'
cl = Client()
CL = lib.load_classes()

def rows(t):
    with open(f'{W}/{t}_70862.csv', newline='') as f:
        return list(csv.DictReader(f))

# ---- enum names from wowsims dbcenums (text parse only) ----
def enum(path, typ):
    out = {}
    for m in re.finditer(r'^\s*([A-Z][A-Z0-9_]*)\s+' + typ + r'\s*=\s*(\d+)', open(path).read(), re.M):
        out[int(m.group(2))] = m.group(1)
    return out
AURA = enum(f'{WS}/sim/core/dbcenums/auras.go', 'EffectAuraType')
MODOP = enum(f'{WS}/sim/core/dbcenums/spellmods.go', 'SpellModOp')
EFFECT = enum(f'{WS}/sim/core/dbcenums/effects.go', 'SpellEffectType')

# ---- class spell families and learnable spell names for "affects" lists ----
FAMILY = {'mage': 3, 'warrior': 4, 'warlock': 5, 'priest': 6, 'druid': 7, 'rogue': 8, 'hunter': 9, 'paladin': 10, 'shaman': 11}
CMASK = {'warrior': 1, 'paladin': 2, 'hunter': 4, 'rogue': 8, 'priest': 16, 'shaman': 64, 'mage': 128, 'warlock': 256, 'druid': 1024}
sco = {}
for r in rows('SpellClassOptions'):
    sco[int(r['SpellID'])] = (int(r['SpellClassSet']), [int(r[f'SpellClassMask_{i}']) & 0xffffffff for i in range(4)])
learn = collections.defaultdict(set)
for r in rows('SkillLineAbility'):
    for c, m in CMASK.items():
        if int(r['ClassMask']) & m:
            learn[c].add(int(r['Spell']))
talent_spells = {c: {t['spell_id'] for tab in CL[c] for t in tab['talents']} for c in CL}

def affects(cls, mask):
    fam = FAMILY[cls]; names = set()
    for sp in learn[cls] | talent_spells[cls]:
        o = sco.get(sp)
        if not o or o[0] != fam: continue
        if any(a & b for a, b in zip(o[1], mask)):
            n = cl.name.get(sp)
            if n: names.add(n)
    return sorted(names)

# ---- legacy Classic Talent table (still in the Forever client, not used by the Forever trees) ----
legacy = collections.defaultdict(dict)
tabclass = {int(r['ID']): int(r['ClassMask']) for r in rows('TalentTab')}
for r in rows('Talent'):
    m = tabclass.get(int(r['TabID']))
    ranks = [int(r[f'SpellRank_{i}']) for i in range(9) if int(r[f'SpellRank_{i}'])]
    if m and ranks:
        legacy[m][cl.name.get(ranks[0], '')] = ranks

# ---- third-party data ----
WFT = {c['slug']: c for c in json.load(open('/home/claude/dl/talents_all/wft/wft_classes.json'))}
TEXTCMP = json.load(open('/home/claude/work/talents/text_compare.json'))
import gzip
_store = json.loads(gzip.open(f'{WS}/assets/db_inputs/spell_store_inputs.json').read())
def store_compare(cls):
    n = 0; diffs = []
    for tab in CL[cls]:
        for t in tab['talents']:
            for idx, pts in (_store['TraitPoints'].get(str(t['definition_id'])) or {}).items():
                for r, v in pts.items():
                    mine, _ = cl.effect_points(t['spell_id'], int(idx), int(r), t['definition_id']); n += 1
                    if mine is None or abs(mine - v) > 1e-6: diffs.append([t['name'], int(idx), int(r), mine, v])
    return {'rank_values_compared': n, 'differences': diffs,
            'against': 'wowsims-forever assets/db_inputs/spell_store_inputs.json TraitPoints (class data from build %s with hotfix push %s)' % (_store['Builds'][cls], _store['Hotfixes'][cls])}
DECODE = json.load(open('/home/claude/work/talents/decode_checks.json')) if os.path.exists('/home/claude/work/talents/decode_checks.json') else {}

STAT = {0: 'str', 1: 'agi', 2: 'sta', 3: 'int', 4: 'spi', -1: 'all_stats'}
SCHOOL = {1: 'physical', 2: 'holy', 4: 'fire', 8: 'nature', 16: 'frost', 32: 'shadow', 64: 'arcane', 126: 'all_magic', 127: 'all'}

def plain(aura, misc, vals):
    """A plain stat key where the aura states one directly."""
    a = AURA.get(aura, '')
    if a == 'A_MOD_STAT': return {'stat': STAT.get(misc, f'stat{misc}') + '_flat'}
    if a in ('A_MOD_PERCENT_STAT', 'A_MOD_TOTAL_STAT_PERCENTAGE'): return {'stat': STAT.get(misc, f'stat{misc}') + '_pct'}
    if a == 'A_MOD_CRIT_PCT': return {'stat': 'crit_pct'}
    if a == 'A_MOD_WEAPON_CRIT_PERCENT': return {'stat': 'melee_crit_pct'}
    if a == 'A_MOD_SPELL_CRIT_CHANCE': return {'stat': 'spell_crit_pct'}
    if a == 'A_MOD_HIT_CHANCE': return {'stat': 'melee_hit_pct'}
    if a == 'A_MOD_SPELL_HIT_CHANCE': return {'stat': 'spell_hit_pct'}
    if a == 'A_MOD_DAMAGE_PERCENT_DONE': return {'stat': 'damage_done_pct', 'school': SCHOOL.get(misc, misc)}
    if a == 'A_MOD_INCREASE_HEALTH_PERCENT': return {'stat': 'max_health_pct'}
    if a == 'A_MOD_DODGE_PERCENT': return {'stat': 'dodge_pct'}
    if a == 'A_MOD_PARRY_PERCENT': return {'stat': 'parry_pct'}
    if a == 'A_MOD_BLOCK_PERCENT': return {'stat': 'block_pct'}
    if a == 'A_MOD_ATTACK_POWER_PCT': return {'stat': 'attack_power_pct'}
    if a == 'A_MOD_HEALING_DONE_PERCENT': return {'stat': 'healing_done_pct'}
    if a == 'A_MOD_RESISTANCE_PCT' and misc == 1: return {'stat': 'armor_pct'}
    if a == 'A_MOD_BASE_RESISTANCE_PCT' and misc == 1: return {'stat': 'base_armor_pct'}
    if a == 'A_MOD_POWER_REGEN_PERCENT': return {'stat': 'power_regen_pct', 'power': misc}
    if a == 'A_MOD_ATTACK_POWER_OF_STAT_PERCENT': return {'stat': 'attack_power_from_stat_pct', 'from': STAT.get(misc, misc)}
    if a == 'A_MOD_SPELL_DAMAGE_OF_STAT_PERCENT': return {'stat': 'spell_damage_from_stat_pct', 'from': STAT.get(misc, misc)}
    if a == 'A_MOD_SPELL_HEALING_OF_STAT_PERCENT': return {'stat': 'spell_healing_from_stat_pct', 'from': STAT.get(misc, misc)}
    return None

def effects(cls, t):
    out = []
    for idx, e in sorted(cl.eff.get(t['spell_id'], {}).items()):
        vals = []; src = None
        for r in range(1, t['max'] + 1):
            v, s = cl.effect_points(t['spell_id'], idx, r, t['definition_id'])
            vals.append(v); src = s
        aura = int(e['EffectAura']); misc = int(e['EffectMiscValue_0'])
        d = {'effect_index': idx, 'effect': EFFECT.get(int(e['Effect']), int(e['Effect'])), 'aura': AURA.get(aura, aura) if aura else None,
             'misc_value': misc, 'per_rank': [None if v is None else (int(v) if abs(v - round(v)) < 1e-9 else round(v, 4)) for v in vals],
             'value_source': 'trait curve (TraitDefinitionEffectPoints)' if src == 'curve' else ('level-scaled base points at level 60' if src and src.startswith('level') else 'SpellEffect base points, same at every rank')}
        if all(v is not None for v in vals) and len(vals) > 1:
            steps = {round(vals[i] - vals[i - 1], 4) for i in range(1, len(vals))}
            if len(steps) == 1 and abs(vals[0] - list(steps)[0]) < 1e-9:
                d['per_rank_step'] = d['per_rank'][0]
        a = AURA.get(aura, '')
        if a in ('A_ADD_FLAT_MODIFIER', 'A_ADD_PCT_MODIFIER'):
            d['spell_mod'] = MODOP.get(misc, misc)
            d['mod_kind'] = 'pct' if a == 'A_ADD_PCT_MODIFIER' else 'flat'
            mask = [int(e[f'EffectSpellClassMask_{i}']) & 0xffffffff for i in range(4)]
            d['affects'] = affects(cls, mask)
        p = plain(aura, misc, vals)
        if p: d.update(p)
        trig = int(e['EffectTriggerSpell'])
        if trig: d['trigger_spell'] = {'id': trig, 'name': cl.name.get(trig)}
        out.append(d)
    return out

def proto_fields(cls):
    txt = open(f'{WS}/proto/{cls}.proto').read()
    m = re.search(r'message \w+Talents \{(.*?)\n\}', txt, re.S)
    return [(f.group(2), int(f.group(3))) for f in re.finditer(r'(int32|bool)\s+(\w+)\s*=\s*\d+\s*\[\(talent_spell_id\)\s*=\s*(\d+)', m.group(1))]

summary = {}
for cls in lib.CLASSES:
    tabs = CL[cls]
    order = lib.code_order(tabs)
    ws = json.load(open(f'{WS}/ui/sim/talents/trees/{cls}.json'))
    ts = json.load(open(f'/home/claude/dl/talents_all/ts/{cls}.json'))['cls']['trees']
    wdb = json.load(open(f'/home/claude/dl/talents_all/wdb/{cls}.json'))['trees']
    wft = WFT[cls]['trees']
    pf = proto_fields(cls)
    # ---- tree-level checks ----
    checks = {'wowsims_tree_json': True, 'timesaver': True, 'warcraftdb': True, 'wowforevertalents': True, 'wowsims_proto_order': True}
    notes = []
    flat_ids = [i for o in order for i in o]
    B = lib.by_id(tabs)
    if [B[i]['spell_id'] for i in flat_ids] != [s for _, s in pf]:
        checks['wowsims_proto_order'] = False; notes.append('wowsims proto field order differs from the calculator order')
    for ti, tab in enumerate(tabs):
        A = [(t['name'], t['row'], t['col'], t['max']) for t in sorted(tab['talents'], key=lambda t: (t['row'], t['col']))]
        if A != [(t['fancyName'], t['location']['rowIdx'], t['location']['colIdx'], t['maxPoints']) for t in ws[ti]['talents']]: checks['wowsims_tree_json'] = False
        if A != [(t['name'], t['row'], t['col'], t['max']) for t in ts[ti]['talents']]: checks['timesaver'] = False
        if set(A) != {(t['name'], t['tier'], t['column'], t['max_rank']) for t in wdb[ti]['talents']}: checks['warcraftdb'] = False
        WA = {(t['name'], t['row'], t['col'], t['maxRank']) for t in wft[ti]['talents']}
        if set(A) != WA:
            checks['wowforevertalents'] = False
            notes.append(f'wowforevertalents.com {tab["name"]}: lists {sorted(WA - set(A))} that the client tree parks off the canvas (wowsims, timesaver.gg and Warcraft DB leave it out); missing {sorted(set(A) - WA)}')
        # timesaver prereq index check
        tsl = ts[ti]['talents']
        for k, t in enumerate(tsl):
            mine = B[order[ti][k]]
            want = order[ti].index(mine['prereq_id']) if mine['prereq_id'] else None
            if t.get('req') != want:
                checks['timesaver'] = False; notes.append(f'timesaver prereq differs for {t["name"]}: {t.get("req")} vs client {want}')
    trees_out = []
    for ti, tab in enumerate(tabs):
        wftn = {t['name']: t for t in wft[ti]['talents']}
        tals = []
        for tid in order[ti]:
            t = B[tid]
            cmp = TEXTCMP.get(f'{cls}|{tab["name"]}|{t["name"]}', [])
            ranks = []
            for r in range(1, t['max'] + 1):
                c = cmp[r - 1] if len(cmp) >= r else {}
                if c and not c['unresolved']:
                    text, src = c['client'], 'client (resolved from Spell.Description_lang, build 70862)'
                elif c and c.get('wft'):
                    text, src = c['wft'], 'wowforevertalents.com (client text with the resolver here unable to fill every token)'
                elif c and c.get('timesaver'):
                    text, src = c['timesaver'], 'timesaver.gg'
                else:
                    text, src = None, None
                rk = {'rank': r, 'text': text, 'text_source': src, 'spell_id': t['spell_id'],
                      'numbers_match': {'timesaver': c.get('num_match_ts'), 'wowforevertalents': c.get('num_match_wft')}}
                if c and not (c.get('num_match_ts') and c.get('num_match_wft')):
                    rk['other_texts'] = {'client': c.get('client'), 'timesaver': c.get('timesaver'), 'wowforevertalents': c.get('wft')}
                if c and c['unresolved']:
                    rk['client_unresolved_tokens'] = sorted(set(c['unresolved']))
                ranks.append(rk)
            w = wftn.get(t['name'], {})
            leg = legacy[CMASK[cls]].get(t['name'])
            entry = {
                'id': tid, 'name': t['name'], 'tree': tab['key'], 'row': t['row'] + 1, 'col': t['col'] + 1,
                'maxRank': t['max'], 'prereq': t['prereq_id'],
                'prereq_rank': B[t['prereq_id']]['max'] if t['prereq_id'] else None,
                'tier_points_required': 5 * t['row'],
                'spell_id': t['spell_id'], 'rank_spell_ids': [t['spell_id']] * t['max'],
                'trait': {'definition_id': t['definition_id'], 'node_id': t['node_id'], 'node_entry_id': t['entry_id']},
                'wowsims_field': next((f for f, s in pf if s == t['spell_id']), None),
                'ranks': ranks,
                'effects': effects(cls, t),
                'forever_vs_classic': {'status': w.get('status'), 'classic_max_rank': (w.get('classic') or {}).get('maxRank'),
                                       'source': 'wowforevertalents.com classification (Forever client 70862 vs Classic Era 1.15.9.69722); not checked here'} if w else None,
            }
            if leg:
                entry['legacy_classic_rank_spell_ids'] = leg
            tals.append(entry)
        trees_out.append({'key': tab['key'], 'name': tab['name'], 'talent_tab_id': tab['talent_tab_id'], 'talents': tals})
    out = {
        'class': cls,
        'client_build': '1.60.1.70862',
        'generated': TODAY,
        'generator': 'wowsim/pipeline/talents/build_talents.py',
        'row_col_base': 1,
        'codeOrder': {tab['key']: order[ti] for ti, tab in enumerate(tabs)},
        'code_format': 'timesaver.gg / wowsims talents string: trees in the order of "trees", joined with "-"; within a tree one digit (the rank) per talent in codeOrder (row by row, left to right); trailing zeros of each tree and trailing dashes are dropped. Example: ' + ('-055-5530003315513151' if cls == 'shaman' else lib.encode(tabs, {})),
        'rules': {'tier': 'a talent in row N (1-based) needs 5 x (N-1) points in its tree; client TraitCond SpentAmountRequired matches 5 x (N-1) for all 467 nodes. Whether points in the gated row itself count (Method.gg planner) or only rows above (wowsims) is not settled by the client data.',
                  'prereq': 'prerequisite at its maximum rank (wowsims ui/sim/talents/broken_talents.ts rule; client TraitEdge Type 2/3 gives the link, not the rank)',
                  'max_points': 51, 'first_point_level': 10},
        'sources': {
            'client': 'Forever client DB2 tables TraitTree, TraitNode, TraitNodeEntry, TraitNodeXTraitNodeEntry, TraitDefinition, TraitDefinitionEffectPoints, TraitEdge, TraitCond, CurvePoint, Spell, SpellEffect, SpellName, SkillLineAbility, SpellClassOptions, build 1.60.1.70862 (wago.tools CSV export, fetched 2026-11-08). These exports carry no hotfixes.',
            'wowsims': 'wowsims/forever commit 125e534 (2026-11-08): ui/sim/talents/trees/%s.json, proto/%s.proto' % (cls, cls),
            'timesaver': 'https://timesaver.gg/tools/wow-forever/talent-calculator/%s (fetched 2026-11-08)' % cls,
            'warcraftdb': 'https://forever.warcraftdb.com/api/v1/talents/%s (fetched 2026-11-08)' % cls,
            'wowforevertalents': 'https://wowforevertalents.com/%s/ (bundle data says client 1.60.1.70862 plus DBCache hotfixes of 2026-11-07; fetched 2026-11-08)' % cls,
        },
        'verification': {'tree_matches': checks, 'notes': notes, 'rank_values_vs_wowsims_hotfixed_store': store_compare(cls),
                         'decode_checks': DECODE.get(cls, []),
                         'decode_checks_legend': {'A': 'timesaver.gg preset code decoded with codeOrder equals the Maxroll planner build read from client TraitNodeEntry ids',
                                                  'B': 'timesaver.gg preset code decoded with codeOrder equals the Method.gg embed decoded from its own bit format (client TraitNode ids)',
                                                  'B2': 'Method.gg embed: its point order ends on the same build as its loadout string',
                                                  'C': 'talents linked in the Maxroll guide talent text are present in the decoded profile builds (soft: the text also names optional swaps)',
                                                  'D': 'wowsims-forever preset string (same format) decodes to a legal build'}},
        'trees': trees_out,
    }
    json.dump(out, open(f'{OUTDIR}/{cls}.json', 'w'), indent=1, ensure_ascii=False)
    nr = sum(len(t['ranks']) for tr in trees_out for t in tr['talents'])
    nm = sum(1 for tr in trees_out for t in tr['talents'] for r in t['ranks'] if r['numbers_match']['timesaver'] and r['numbers_match']['wowforevertalents'])
    summary[cls] = {'talents': sum(len(tr['talents']) for tr in trees_out), 'ranks': nr, 'ranks_numbers_agree_all3': nm, 'checks': checks, 'notes': notes}
    print(cls, summary[cls])
json.dump(summary, open('/home/claude/work/talents/build_summary.json', 'w'), indent=1)
