# Derive the Forever class equip rules (armor, weapon skills, ranged, dual wield, level gates) from the Forever client
# DB2 tables (wago.tools CSV exports, build 1.60.1.70862), then cross-check them against
#   - wowsims Forever sim/core/character_constants.go (read as text, not built)
#   - Warcraft Tavern "Weapon Skill Trainer Locations" (WoW Forever guide) class x skill table
# Output: cache/allclass/class_rules.json (rules + every source + every disagreement and how it was resolved).
import csv, json, os, re, html, subprocess, time, collections
from common import ROOT, DB2, WEB, WORK, WOWSIMS, BUILD, CLASS_IDS, CLASS_ORDER

TABLES = ['SkillLine', 'SkillLineAbility', 'SkillRaceClassInfo', 'SpellEquippedItems', 'SpellEffect']
TAVERN = 'https://www.warcrafttavern.com/forever/guides/weapon-trainers/'


def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return
    for a in range(4):
        r = subprocess.run(['curl', '-sS', '-m', '120', '-A', 'Mozilla/5.0', '-o', path + '.part', '-w', '%{http_code}', url], capture_output=True, text=True)
        if r.stdout == '200': os.replace(path + '.part', path); return
        time.sleep(3 * (a + 1))
    raise RuntimeError(f'fetch failed {url}: {r.stdout} {r.stderr}')


os.makedirs(DB2, exist_ok=True); os.makedirs(WEB, exist_ok=True)
for t in TABLES:
    fetch(f'https://wago.tools/db2/{t}/csv?build={BUILD}', os.path.join(DB2, f'{t}_{BUILD.split(".")[-1]}.csv'))
fetch(TAVERN, os.path.join(WEB, 'weapon-trainers.html'))


def rows(t): return list(csv.DictReader(open(os.path.join(DB2, f'{t}_{BUILD.split(".")[-1]}.csv'), encoding='utf-8')))


def classes_of(mask):
    mask = int(mask)
    return [n for c, n in CLASS_IDS.items() if mask & (1 << (c - 1))]


# item subclass names, in DB2 order, from wowsims tools/database/dbc/enums.go (ITEM_SUBCLASS_WEAPON_* / ITEM_SUBCLASS_ARMOR_* iota blocks)
enums = open(os.path.join(WOWSIMS, 'tools/database/dbc/enums.go')).read()
def iota(prefix):
    m = re.search(r'const \(\s*\n\s*' + prefix + r'(\w+) = iota(.*?)\)', enums, re.S)
    names = [m.group(1)] + re.findall(r'^\s*' + prefix + r'(\w+)\s*$', m.group(2), re.M)
    return names
WSUB = iota('ITEM_SUBCLASS_WEAPON_'); ASUB = iota('ITEM_SUBCLASS_ARMOR_')
# DB2 subclass token -> the subtype names used in the item file
WNAME = {'AXE': 'One-Handed Axe', 'AXE2': 'Two-Handed Axe', 'BOW': 'Bow', 'GUN': 'Gun', 'MACE': 'One-Handed Mace', 'MACE2': 'Two-Handed Mace',
         'POLEARM': 'Polearm', 'SWORD': 'One-Handed Sword', 'SWORD2': 'Two-Handed Sword', 'STAFF': 'Staff', 'FIST': 'Fist Weapon', 'DAGGER': 'Dagger',
         'THROWN': 'Thrown', 'CROSSBOW': 'Crossbow', 'WAND': 'Wand'}
ANAME = {'CLOTH': 'Cloth', 'LEATHER': 'Leather', 'MAIL': 'Mail', 'PLATE': 'Plate', 'SHIELD': 'Shield', 'IDOL': 'Idol', 'LIBRAM': 'Libram', 'TOTEM': 'Totem'}
RELIC = {'Idol', 'Libram', 'Totem'}
RANGED = {'Bow', 'Gun', 'Crossbow', 'Thrown', 'Wand'}

SL = {int(r['ID']): r['DisplayName_lang'] for r in rows('SkillLine')}
SLA = rows('SkillLineAbility'); SRCI = rows('SkillRaceClassInfo')
SEI = {int(r['SpellID']): r for r in rows('SpellEquippedItems')}
EFF = collections.defaultdict(set)
for r in rows('SpellEffect'): EFF[int(r['SpellID'])].add(int(r['Effect']))
PROFICIENCY_EFFECT, DUAL_WIELD_EFFECT = 60, 40   # SpellEffect.Effect values on the proficiency / Dual Wield spells (seen on 750 Plate Mail, 674 Dual Wield)
NEVER_LEARNED = 3                                # SkillLineAbility.AcquireMethod 3: row is never learned (Shaman Dual Wield 674 carries it)


def min_level(skill, cls):
    lv = [int(r['MinLevel']) for r in SRCI if int(r['SkillID']) == skill and cls in classes_of(r['ClassMask'])]
    return (min(lv) if lv else None), len(lv)


rules = {c: {'armor': {}, 'weapons': {}, 'ranged': {}, 'dualWield': None} for c in CLASS_ORDER}
evidence = []; missing_srci = []
for r in SLA:
    sp = int(r['Spell']); sk = int(r['SkillLine'])
    if sp not in SEI or PROFICIENCY_EFFECT not in EFF[sp] or int(r['AcquireMethod']) == NEVER_LEARNED: continue
    e = SEI[sp]; icls = int(e['EquippedItemClass']); mask = int(e['EquippedItemSubclass'])
    names = WSUB if icls == 2 else ASUB if icls == 4 else None
    if names is None: continue
    subs = [names[i] for i in range(len(names)) if mask & (1 << i)]
    for cls in classes_of(r['ClassMask']):
        lv, n = min_level(sk, cls)
        if n == 0: missing_srci.append((cls, SL.get(sk)))
        for s in subs:
            if icls == 2 and s in WNAME:
                nm = WNAME[s]; (rules[cls]['ranged'] if nm in RANGED else rules[cls]['weapons'])[nm] = lv
            elif icls == 4 and s in ANAME:
                (rules[cls]['ranged'] if ANAME[s] in RELIC else rules[cls]['armor'])[ANAME[s]] = lv
        evidence.append({'class': cls, 'skillLine': SL.get(sk), 'skillLineId': sk, 'spell': sp, 'itemClass': icls, 'subclasses': subs,
                         'minLevel': lv, 'acquireMethod': int(r['AcquireMethod'])})
# Dual Wield (skill line 118, spell 674, effect 40): classes from SkillLineAbility rows that are not NeverLearned
dw_rows = []
for r in SLA:
    sp = int(r['Spell'])
    if DUAL_WIELD_EFFECT in EFF[sp] and int(r['SkillLine']) == 118:
        dw_rows.append({'spell': sp, 'classes': classes_of(r['ClassMask']), 'acquireMethod': int(r['AcquireMethod'])})
        if int(r['AcquireMethod']) == NEVER_LEARNED: continue
        for cls in classes_of(r['ClassMask']):
            rules[cls]['dualWield'] = min_level(118, cls)[0] or 1

# ---- wowsims capability table (cross-check only) ----
go = open(os.path.join(WOWSIMS, 'sim/core/character_constants.go')).read()
def go_block(name):
    m = re.search(r'var ' + name + r' = map\[proto\.Class\](.*?)\n}\n', go, re.S); return m.group(1)
GOCLS = {'ClassWarrior': 'warrior', 'ClassPaladin': 'paladin', 'ClassHunter': 'hunter', 'ClassRogue': 'rogue', 'ClassPriest': 'priest',
         'ClassShaman': 'shaman', 'ClassMage': 'mage', 'ClassWarlock': 'warlock', 'ClassDruid': 'druid'}
ws_ranged = {GOCLS[c]: re.findall(r'RangedWeaponType_RangedWeaponType(\w+)', body) for c, body in re.findall(r'proto\.Class_(\w+):\s*\{([^\n]*)\}', go_block('ClassRangedWeaponTypeCapabilities'))}
ws_armor = {GOCLS[c]: re.findall(r'ArmorType_ArmorType(\w+)', body) for c, body in re.findall(r'proto\.Class_(\w+):\s*\{([^\n]*)\}', go_block('ClassArmorTypeCapabilities'))}
ws_weap = {}
for c, body in re.findall(r'proto\.Class_(\w+): \{\n(.*?)\n\t\}', go_block('ClassWeaponTypeCapabilities'), re.S):
    ws_weap[GOCLS[c]] = {w: 'CanUseTwoHand: true' in rest for w, rest in re.findall(r'WeaponType_WeaponType(\w+):\s*\{([^}]*)\}', body)}
ws_dw = re.findall(r'Spec_Spec(\w+):\s*true', go[go.find('SpecCanDualWieldCapabilities'):])
# relics (armor subclasses LIBRAM/IDOL/TOTEM) get their proficiency from 'GENERIC (DND)' skill-line spells; MISC must have none
relic_prof = [x for x in evidence if x['itemClass'] == 4 and set(x['subclasses']) & {'MISC', 'LIBRAM', 'IDOL', 'TOTEM'}]

# ---- cross-check 1: wowsims capability table ----
def ws_view(c):
    w = ws_weap.get(c, {}); out = set()
    for t, two in w.items():
        if t in ('OffHand',): out.add('Held In Off-hand'); continue
        if t == 'Shield': out.add('Shield'); continue
        n = {'Fist': 'Fist Weapon'}.get(t, t)
        if n in ('Axe', 'Mace', 'Sword'):
            out.add('One-Handed ' + n)
            if two: out.add('Two-Handed ' + n)
        else: out.add(n)
    out |= set(ws_ranged.get(c, [])); out |= set(ws_armor.get(c, []))
    return out
def my_view(c):
    r = rules[c]; return set(r['weapons']) | set(r['ranged']) | set(r['armor']) | {'Held In Off-hand'}
diff_ws = {}
for c in CLASS_ORDER:
    a, b_ = my_view(c), ws_view(c)
    if a != b_: diff_ws[c] = {'onlyClientDB2': sorted(a - b_), 'onlyWowsims': sorted(b_ - a)}
dw_ws = sorted({'DpsWarrior': 'warrior', 'ProtectionWarrior': 'warrior', 'Hunter': 'hunter', 'Rogue': 'rogue'}.get(s, s) for s in ws_dw)

# ---- cross-check 2: Warcraft Tavern class x weapon skill table ----
t = open(os.path.join(WEB, 'weapon-trainers.html'), encoding='utf-8').read()
tb = re.search(r'<table.*?</table>', t, re.S).group(0)
trs = re.findall(r'<tr.*?</tr>', tb, re.S)
hdr = [html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', trs[0], re.S)]
tavern = {}
for tr in trs[1:]:
    cells = [html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', tr, re.S)]
    tavern[cells[0]] = sorted(h.lower() for h, v in zip(hdr[1:], cells[1:]) if '✓' in v)
TAV2 = {'Bows': 'Bow', 'Crossbows': 'Crossbow', 'Daggers': 'Dagger', 'Fist Weapons': 'Fist Weapon', 'Guns': 'Gun', 'One-Handed Axes': 'One-Handed Axe',
        'One-Handed Maces': 'One-Handed Mace', 'One-Handed Swords': 'One-Handed Sword', 'Polearms': 'Polearm', 'Staves': 'Staff', 'Thrown': 'Thrown',
        'Two-Handed Axes': 'Two-Handed Axe', 'Two-Handed Maces': 'Two-Handed Mace', 'Two-Handed Swords': 'Two-Handed Sword', 'Wands': 'Wand'}
diff_tav = {}
for sk, cls in tavern.items():
    n = TAV2[sk]
    mine = sorted(c for c in CLASS_ORDER if n in rules[c]['weapons'] or n in rules[c]['ranged'])
    if mine != cls: diff_tav[n] = {'clientDB2': mine, 'warcraftTavern': cls}
pole_lvl = re.search(r'Polearms require level (\d+)', html.unescape(re.sub(r'<[^>]+>', '', t)))

out = {
    'build': BUILD,
    'classes': rules,
    'notes': {
        'fromLevel': 'Level gate from DB2 SkillRaceClassInfo.MinLevel for the skill line and class (null = no gate). The character can equip the item at max(item reqLvl, fromLevel).',
        'dualWield': 'Level at which the class can learn Dual Wield (DB2 SkillRaceClassInfo skill 118); null = cannot dual wield. One-hand weapons go in the off hand only from that level; Off Hand-only weapons need it.',
        'heldInOffHand': 'Held In Off-hand items are armor subclass 0 (Miscellaneous). No proficiency spell in the DB2 covers that subclass, so every class can hold one.',
        'relics': 'Idol, Libram and Totem (armor subclasses 8, 7, 9) are granted by proficiency spells 27764 (Druid), 27762 (Paladin), 27763 (Shaman) on the GENERIC (DND) skill line.',
        'neckFingerTrinket': 'No proficiency; every class.',
    },
    'sources': {
        'clientDB2': {'build': BUILD, 'site': 'https://wago.tools/db2/<Table>/csv?build=' + BUILD, 'tables': TABLES,
                      'method': 'Proficiency spells = SkillLineAbility spells that have a SpellEquippedItems row and a SpellEffect of type 60 (Proficiency); the classes come from SkillLineAbility.ClassMask '
                                '(rows with AcquireMethod 3 = never learned are skipped), the item subclasses from SpellEquippedItems.EquippedItemSubclass, and the level gate from SkillRaceClassInfo.MinLevel '
                                'for the same skill line and class. Dual Wield = skill line 118 / spell 674 (SpellEffect type 40).'},
        'wowsims': {'file': 'sim/core/character_constants.go', 'commit': '125e534558b5b5588f26aae393894c6ea80bba5e'},
        'warcraftTavern': {'url': TAVERN, 'fetched': '2026-11-08', 'polearmLevelText': pole_lvl.group(0) if pole_lvl else None},
        'warcraftTavernWarriorLeveling': {'url': 'https://www.warcrafttavern.com/forever/guides/warrior-leveling/', 'confirms': 'Polearms 20, Dual Wield 20, Plate Armor 40 (Warrior)'},
        'warcraftTavernHunterLeveling': {'url': 'https://www.warcrafttavern.com/forever/guides/hunter-leveling/', 'confirms': 'Thrown trainers listed for Hunters (Bixi Wobblebonk, Ilyenia Moonfire); Polearms 20'},
    },
    'crossCheck': {
        'wowsimsCapabilityTable': {'differences': diff_ws, 'dualWieldSpecs': dw_ws, 'raw': {'armor': ws_armor, 'weapons': ws_weap, 'ranged': ws_ranged}},
        'warcraftTavernTable': {'differences': diff_tav, 'raw': tavern},
        'dualWieldRows': dw_rows,
        'relicOrMiscProficiencySpells': relic_prof,
        'miscSubclassHasProficiency': any('MISC' in x['subclasses'] for x in relic_prof),
        'classSkillPairsWithoutSkillRaceClassInfoRow': sorted(set(missing_srci)),
    },
    'evidence': evidence,
}
json.dump(out, open(os.path.join(WORK, 'class_rules.json'), 'w'), indent=1)
for c in CLASS_ORDER:
    r = rules[c]
    print(f"{c:8} armor={r['armor']} dw={r['dualWield']}\n         weapons={r['weapons']}\n         ranged={r['ranged']}")
print('wowsims diffs', json.dumps(diff_ws)); print('wowsims DW', dw_ws)
print('tavern diffs', json.dumps(diff_tav)); print('DW rows', dw_rows); print('relic/misc prof', relic_prof); print('missing SRCI', sorted(set(missing_srci)))
