#!/usr/bin/env python3
"""Write src/levels.js (LEVELS + RANKS) from data/shaman_levels.json and src/ranks.json.

LEVELS arrays are indexed by level - 1. Player arrays cover 1-60, mob arrays 1-63.
Run tools/build_ranks.py first if data/shaman_ranks.json changed.
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, 'data/shaman_levels.json')))
ranks = json.load(open(os.path.join(ROOT, 'src/ranks.json')))
lv, mobs = d['levels'], d['mobs']['levels_1_to_63']
def col(key): return [row['value'] for row in lv[key]]
L = {
    'mobArmor': [m['normal']['armor']['value'] for m in mobs],
    'hp': col('base_health'), 'mana': col('base_mana'),
    'str': col('strength'), 'agi': col('agility'), 'sta': col('stamina'), 'int': col('intellect'), 'spi': col('spirit'),
    'cpa': col('melee_crit_pct_per_agility'), 'cpi': col('spell_crit_pct_per_intellect'),
    'apt': [2*l - 20 for l in range(1, 61)],
    'mobHP': [m['normal']['health']['value'] for m in mobs],
    'mobDPS': [round(m['normal']['auto_attack_dps']['value'], 2) for m in mobs],
    'eliteHP': [m['elite']['health']['value'] for m in mobs],
    'eliteDPS': [m['elite']['auto_attack_dps']['value'] for m in mobs],
}
js = 'const LEVELS = ' + json.dumps(L, separators=(',', ':')) + ';\n'
js += 'const RANKS = ' + json.dumps(ranks, separators=(',', ':')) + ';\n'
js += "if(typeof module !== 'undefined' && module.exports) module.exports = {LEVELS, RANKS};\n"
open(os.path.join(ROOT, 'src/levels.js'), 'w').write(js)
print('levels.js', len(js), 'bytes')
