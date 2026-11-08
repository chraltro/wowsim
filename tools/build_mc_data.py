#!/usr/bin/env python3
"""Build src/mc/classdata.js: everything the multi-class page needs per class.

Inputs: data/classes/<class>_levels.json, data/talents/<class>.json, data/routes/<class>.json,
the rotation presets and reference requests in vendor/mythicsim-forever-engine.

Per class it writes base stats per race and level, the talent trees in calculator code order,
each spec's leveling routes (only legal ones, first legal one is the default), level 60 builds
by dungeon role, and the engine template for each spec (class options and rotation preset).
"""
import json, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, 'vendor/mythicsim-forever-engine')
CLASSES = ['warrior', 'paladin', 'hunter', 'rogue', 'priest', 'shaman', 'mage', 'warlock', 'druid']
ENGINE_CLASS = {c: 'Class' + c.capitalize() for c in CLASSES}
ENGINE_RACE = {'human': 'RaceHuman', 'dwarf': 'RaceDwarf', 'night_elf': 'RaceNightElf', 'gnome': 'RaceGnome',
               'high_order_skyborne': 'RaceHighOrderSkyborne'}
RACE_LABEL = {'human': 'Human', 'dwarf': 'Dwarf', 'night_elf': 'Night Elf', 'gnome': 'Gnome',
              'high_order_skyborne': 'High Order Skyborne'}

# Route spec -> engine spec key, MythicSim rotation preset and display name
SPECS = {
    'warrior': {'arms': ('dpsWarrior', 'warrior/dps/arms', 'Arms'), 'fury': ('dpsWarrior', 'warrior/dps/dps_reck', 'Fury'),
                'protection': ('protectionWarrior', 'warrior/protection/protection', 'Protection')},
    'paladin': {'holy': ('holyPaladin', 'paladin/holy/flash_of_light', 'Holy'), 'protection': ('protectionPaladin', 'paladin/protection/p5', 'Protection'),
                'retribution': ('retributionPaladin', 'paladin/retribution/default', 'Retribution')},
    'hunter': {'beast_mastery': ('hunter', 'hunter/dps/bm', 'Beast Mastery'), 'marksmanship': ('hunter', 'hunter/dps/mm', 'Marksmanship'),
               'survival': ('hunter', 'hunter/dps/sv_melee', 'Survival')},
    'rogue': {'assassination': ('rogue', 'rogue/dps/forever_mutilate', 'Assassination'), 'combat': ('rogue', 'rogue/dps/combat_sinister_strike', 'Combat'),
              'subtlety': ('rogue', 'rogue/dps/forever_hemorrhage', 'Subtlety')},
    'priest': {'discipline': ('healerPriest', 'priest/healer/default', 'Discipline'), 'holy': ('healerPriest', 'priest/healer/default', 'Holy'),
               'shadow': ('dpsPriest', 'priest/dps/shadow', 'Shadow')},
    'shaman': {'ele': ('elementalShaman', 'shaman/elemental/forever', 'Elemental'), 'enh': ('enhancementShaman', 'shaman/enhancement/forever', 'Enhancement'),
               'res': ('restorationShaman', 'shaman/restoration/default', 'Restoration')},
    'mage': {'arcane': ('mage', 'mage/dps/arcane', 'Arcane'), 'fire': ('mage', 'mage/dps/fire', 'Fire'), 'frost': ('mage', 'mage/dps/frost', 'Frost')},
    'warlock': {'affliction': ('warlock', 'warlock/dps/affliction', 'Affliction'), 'demonology': ('warlock', 'warlock/dps/demonic_pact', 'Demonology'),
                'destruction': ('warlock', 'warlock/dps/destruction_conflag', 'Destruction')},
    'druid': {'balance': ('balanceDruid', 'druid/balance/launch', 'Balance'), 'feral_combat': ('feralCatDruid', 'druid/feralcat/default', 'Feral'),
              'restoration': ('restorationDruid', 'druid/restoration/default', 'Restoration')},
}
# Extra engine specs reachable from a route spec for a dungeon role
ROLE_SPEC = {('druid', 'feral_combat', 'tank'): ('feralBearDruid', 'druid/feralbear/default'),
             # Healers quest with their damage abilities: the rotation and spec options of a damage spec, their own talents
             ('paladin', 'holy', 'quest'): ('retributionPaladin', 'paladin/retribution/default'),
             ('priest', 'discipline', 'quest'): ('dpsPriest', 'priest/dps/smite'),
             ('priest', 'holy', 'quest'): ('dpsPriest', 'priest/dps/smite'),
             ('druid', 'restoration', 'quest'): ('balanceDruid', 'druid/balance/launch'),
             ('shaman', 'res', 'quest'): ('enhancementShaman', 'shaman/enhancement/forever')}

STD = {'buffs', 'characterSheet', 'class', 'consumables', 'distanceFromTarget', 'equipment', 'level', 'name', 'profession1',
       'profession2', 'race', 'reactionTimeMs', 'rotation', 'talentsString', 'knownSpells', 'cooldowns', 'bonusStats',
       'channelClipDelayMs', 'disableRacials', 'enableItemSwap', 'itemSwap', 'inFrontOfTarget'}


def vals(rows):
    return [r['value'] for r in rows]


def templates():
    """One reference request per engine spec key: its class options and the fields around them."""
    files = sorted(glob.glob(VENDOR + '/tests/classes/*/prepare/*.request.json')) + sorted(glob.glob(VENDOR + '/fixtures/healers/*.request.json'))
    out = {}
    for f in files:
        try:
            p = json.load(open(f))['raid']['parties'][0]['players'][0]
        except Exception:
            continue
        keys = [k for k in p if k not in STD]
        if len(keys) != 1 or keys[0] in out:
            continue
        k = keys[0]
        out[k] = {'source': os.path.relpath(f, VENDOR), 'options': p[k], 'distanceFromTarget': p.get('distanceFromTarget', 5),
                  'reactionTimeMs': p.get('reactionTimeMs', 100), 'channelClipDelayMs': p.get('channelClipDelayMs'), 'inFrontOfTarget': p.get('inFrontOfTarget', False),
                  'consumables': {c: v for c, v in (p.get('consumables') or {}).items() if c in ('mhImbueId', 'ohImbueId', 'petId')}}
    return out


def legal(route, tal):
    """Check a route [[id, n], ...] against the tree: 5 points per row in the tree, prerequisites at max."""
    meta = {t['id']: t for tr in tal['trees'] for t in tr['talents']}
    spent, have = {}, {}
    for tid, n in route:
        for _ in range(n):
            t = meta.get(tid)
            if not t:
                return 'unknown talent ' + tid
            tree = t['tree']
            if spent.get(tree, 0) < 5 * (t['row'] - 1):
                return f"{t['name']} needs {5 * (t['row'] - 1)} points in {tree}"
            if t.get('prereq') and have.get(t['prereq'], 0) < meta[t['prereq']]['maxRank']:
                return f"{t['name']} needs {meta[t['prereq']]['name']} maxed"
            have[tid] = have.get(tid, 0) + 1
            if have[tid] > t['maxRank']:
                return f"{t['name']} over max rank"
            spent[tree] = spent.get(tree, 0) + 1
    if sum(n for _, n in route) > 51:
        return 'more than 51 points'
    return None


def runs_from_order(order):
    runs = []
    for step in order:
        if runs and runs[-1][0] == step['id']:
            runs[-1][1] += 1
        else:
            runs.append([step['id'], 1])
    return runs


def main():
    presets = {}
    tmpl = templates()
    out = {}
    for c in CLASSES:
        lv = json.load(open(f'{ROOT}/data/classes/{c}_levels.json'))
        tal = json.load(open(f'{ROOT}/data/talents/{c}.json'))
        rt = json.load(open(f'{ROOT}/data/routes/{c}.json'))
        L = lv['levels']
        races = {}
        for rk, r in lv['races'].items():
            cols = [r['levels'][a] for a in ('strength', 'agility', 'stamina', 'intellect', 'spirit')]
            races[rk] = {'label': RACE_LABEL.get(rk, rk), 'engine': ENGINE_RACE[rk],
                         'base': [[cols[i][l]['value'] for i in range(5)] for l in range(60)]}
        trees = [{'key': tr['key'], 'name': tr['name'],
                  'talents': [[t['id'], t['name'], t['maxRank'], t['row'], t['col'], t.get('prereq')] for t in tr['talents']]}
                 for tr in tal['trees']]
        code_order = tal['codeOrder']
        specs = {}
        for sk, (ekey, preset, label) in SPECS[c].items():
            s = rt['specs'].get(sk)
            if not s:
                continue
            routes = []
            for entry in s.get('leveling', []):
                if entry.get('kind') != 'point_by_point' or not entry.get('order'):
                    continue
                run = entry.get('route_runs') or runs_from_order(entry['order'])
                problem = legal(run, tal)
                src = entry.get('source', {})
                routes.append({'name': entry.get('name'), 'site': src.get('site'), 'url': src.get('url'),
                               'updated': src.get('updated') or src.get('published'), 'route': run, 'problem': problem})
            routes.sort(key=lambda r: r['problem'] is not None)
            end = {}
            for role, builds in (s.get('endgame') or {}).items():
                end[role] = [{'name': b.get('name'), 'site': b.get('source', {}).get('site'), 'url': b.get('source', {}).get('url'),
                              'code': b.get('code') or b.get('final_code'), 'split': b.get('split')} for b in builds]
            for name in [preset] + [v[1] for k2, v in ROLE_SPEC.items() if k2[:2] == (c, sk)]:
                if name not in presets:
                    presets[name] = json.load(open(f'{VENDOR}/presets/{name}.apl.json'))
            spec = {'label': label, 'engineSpec': ekey, 'preset': preset, 'roles': s.get('dungeon_roles', []),
                    'routes': routes, 'endgame': end}
            for (cc, ss, role), (ekey2, preset2) in ROLE_SPEC.items():
                if (cc, ss) == (c, sk):
                    spec.setdefault('roleSpec', {})[role] = {'engineSpec': ekey2, 'preset': preset2}
            specs[sk] = spec
        missing = sorted(({s['engineSpec'] for s in specs.values()} | {r['engineSpec'] for s in specs.values() for r in s.get('roleSpec', {}).values()}) - set(tmpl))
        if missing:
            raise SystemExit(f'{c}: no reference request for {missing}')
        out[c] = {
            'engineClass': ENGINE_CLASS[c], 'races': races,
            'baseHP': vals(L['base_health']), 'baseMana': vals(L['base_mana']),
            'hpPerSta': vals(L['hp_per_stamina']), 'manaPerInt': vals(L['mana_per_intellect']),
            'critPerAgi': vals(L['melee_crit_pct_per_agility']), 'critPerInt': vals(L['spell_crit_pct_per_intellect']),
            'baseMeleeCrit': vals(L['base_melee_crit_pct']), 'baseSpellCrit': vals(L['base_spell_crit_pct']),
            'dodgePerAgi': vals(L['dodge_pct_per_agility']), 'baseDodge': vals(L['base_dodge_pct']),
            'apLevel': vals(L['attack_power_level_term']), 'rapLevel': vals(L['ranged_attack_power_level_term']),
            'apRule': L['attack_power_level_term'][0].get('formula'), 'rapRule': L['ranged_attack_power_level_term'][0].get('formula'),
            'trees': trees, 'codeOrder': code_order, 'specs': specs,
        }
    used = {s['engineSpec'] for c in out.values() for s in c['specs'].values()} | {r['engineSpec'] for c in out.values() for s in c['specs'].values() for r in s.get('roleSpec', {}).values()}
    meta = {'engine': 'MythicSim Forever engine b3c5eb6 (MIT)', 'presetsFrom': 'vendor/mythicsim-forever-engine/presets'}
    js = 'const CLASSDATA = ' + json.dumps(out, separators=(',', ':')) + ';\n'
    js += 'const PRESETS_APL = ' + json.dumps(presets, separators=(',', ':')) + ';\n'
    js += 'const SPEC_TEMPLATES = ' + json.dumps({k: v for k, v in tmpl.items() if k in used}, separators=(',', ':')) + ';\n'
    js += 'const MC_META = ' + json.dumps(meta) + ';\n'
    js += "if(typeof module !== 'undefined' && module.exports) module.exports = {CLASSDATA, PRESETS_APL, SPEC_TEMPLATES, MC_META};\n"
    os.makedirs(f'{ROOT}/src/mc', exist_ok=True)
    open(f'{ROOT}/src/mc/classdata.js', 'w').write(js)
    print('classdata.js', len(js), 'bytes')
    for c, d in out.items():
        print(c, {k: (len(s['routes']), sum(1 for r in s['routes'] if not r['problem']), s['routes'][0]['site'] if s['routes'] else None) for k, s in d['specs'].items()})


if __name__ == '__main__':
    main()
