# Step 4: final cleanup (same rules as ../all/finalize_all.py) + class fields for every record, then write
# wowsim/data/items_all.json.
#   usableBy      [{class, fromLevel, slots[, offHandFromLevel]}]  from cache/allclass/class_rules.json (Forever client DB2)
#   equipSlots    paper-doll slots the item fits (mainHand/offHand/ranged/head/finger1...)
#   weaponSubtype One-Handed Axe / Two-Handed Sword / Polearm / Bow / Wand / Idol / Shield / Held In Off-hand ...
#   rangedType    Bow / Gun / Crossbow / Thrown / Wand / Idol / Libram / Totem for the ranged/relic slot, else null
# In: cache/allclass/items_stage3.json
import json, os, re, time, collections
from common import WORK, OUT, SHAMAN_FILE, CLASS_IDS, CLASS_ORDER, rules, usable_by, equip_slots, weapon_subtype, load_build_dataset

b = load_build_dataset()
R = rules()
D = json.load(open(os.path.join(WORK, 'items_stage3.json')))
ITYPE = {v: k for k, v in b.TYPE.items()}          # 'Head' -> 1 ... 'Weapon' -> 13, 'Ranged/Relic' -> 14
SLOT_T = {'One-Hand': 13, 'Main Hand': 13, 'Off Hand': 13, 'Two-Hand': 13, 'Shield': 13, 'Held In Off-hand': 13, 'Ranged': 14}
RANGED = {'Bow', 'Gun', 'Crossbow', 'Thrown', 'Wand', 'Idol', 'Libram', 'Totem'}
HORDE = re.compile(r"^(Greater )?Insignia of the Horde$")
DEV = re.compile(r"\(DND\)|^Hidden (Shoulder|Bracers)$|^Invisible Dagger$|^Durability Shoulderpads$|^Tyler's Balanced Bobble$")


def item_type(x):
    t = ITYPE.get(x.get('itemType'))
    if t: return t
    s = x.get('slot') or ''
    return SLOT_T.get(s) or (14 if s.startswith('Relic') else ITYPE.get(s))


keep = []; ex = collections.Counter(); removed = []; dropped_nouse = []
for x in D['items']:
    if HORDE.search(x['name']): ex['horde-only insignia (name)'] += 1; removed.append((x['id'], x['name'])); continue
    if DEV.search(x['name']) and (x['ilvl'] or 0) <= 1 and not x['sources']: ex['developer/placeholder item (name, ilvl 1, no source)'] += 1; removed.append((x['id'], x['name'])); continue
    for l in b.wh_lines(x['id']) or []:
        if 'May not be in WoW: Forever' in l: x['wowheadNote'] = l
    t = item_type(x)
    if x.get('itemType') is None and t: x['itemType'] = b.TYPE.get(t)
    wt = x.get('weaponType'); hand = x.get('hand')
    allow = [CLASS_IDS[c] for c in x['classAllowlist'] if c in CLASS_IDS] if x.get('classAllowlist') else None
    if x.get('classAllowlist') and not allow: ex['class allowlist names no playable class'] += 1; dropped_nouse.append((x['id'], x['name'])); continue
    ub = usable_by(R, item_type=t, armor=x.get('armorType'), weapon_type=wt if t == 13 else None, hand=hand,
                   ranged=wt if t == 14 else None, allow=allow, faction=x.get('factionRestriction'))
    if not ub:
        ex['no class can equip it (class allowlist and proficiency rules exclude every class)'] += 1; dropped_nouse.append((x['id'], x['name'], x['slot'], wt)); continue
    x['usableBy'] = ub
    x['equipSlots'] = equip_slots(t, wt, hand)
    x['weaponSubtype'] = weapon_subtype(wt, hand) if t in (13, 14) and wt else None
    x['rangedType'] = wt if t == 14 and wt in RANGED else None
    keep.append(x)
keep.sort(key=lambda x: x['id'])

# ---- coverage ----
def has_chance(x): return any(s.get('dropChancePct') is not None for s in x['sources'] if s['type'] == 'drop')
cov = {'total': len(keep), 'withAnySource': sum(1 for x in keep if x['sources']), 'withDropSource': sum(1 for x in keep if 'drop' in x['sourceTypes']),
       'withDropChance': sum(1 for x in keep if has_chance(x)), 'perClass': {}}
for c in CLASS_ORDER:
    sub = [x for x in keep if any(e['class'] == c for e in x['usableBy'])]
    cov['perClass'][c] = {'items': len(sub), 'withAnySource': sum(1 for x in sub if x['sources']), 'withDropSource': sum(1 for x in sub if 'drop' in x['sourceTypes']),
                          'withDropChance': sum(1 for x in sub if has_chance(x)),
                          'gated': sum(1 for x in sub for e in x['usableBy'] if e['class'] == c and e.get('fromLevel'))}
unk = collections.Counter(); info = collections.Counter()
BODY = {'Head', 'Shoulder', 'Chest', 'Wrist', 'Hands', 'Waist', 'Legs', 'Feet'}
for x in keep:
    if x.get('ilvl') is None: unk['item.ilvl'] += 1
    if x.get('quality') is None: unk['item.quality'] += 1
    if x['slot'] in BODY and x.get('armorType') is None: info['body-armor slot with armorType null (armor subclass Miscellaneous/Cosmetic: no proficiency needed)'] += 1
    if x.get('reqLvl') is None: info['reqLvl null (item has no level requirement)'] += 1
    if x.get('phase') is None: info['phase null (wowsims db.json field; leftover_db, Warcraft DB and wowtbc items have none)'] += 1
    if x.get('crossCheckWowhead') == 'no wowhead tooltip': unk['no Wowhead Forever tooltip (no cross-check)'] += 1
    if x['itemType'] in ('Weapon', 'Ranged/Relic') and x.get('weaponType') not in ('Shield', 'Held In Off-hand', 'Idol', 'Libram', 'Totem'):
        if not x.get('weapon'): unk['weapon block missing on a weapon'] += 1
        else:
            for k in ('min', 'max', 'speed', 'dps'):
                if x['weapon'].get(k) is None: unk['weapon.' + k] += 1
    if not x['sources']: unk['item has no source at all'] += 1
    for s_ in x['sources']:
        t_ = s_['type']
        for k in {'drop': ('npc', 'zone', 'dropChancePct'), 'quest': ('questLevel', 'questMinLevel', 'zone'), 'crafted': ('profession', 'skill', 'reagents'),
                  'vendor': ('npc', 'zone', 'costCopper'), 'reputation': ('faction', 'standing'), 'pvp': ('rankFromName',)}.get(t_, ()):
            if s_.get(k) in (None, ''): unk[f'{t_}.{k}'] += 1
        if t_ == 'drop' and s_.get('instanceType') == 'dungeon' and s_.get('dungeonLevel') is None: unk['drop.dungeonLevel (dungeon drops)'] += 1
cov['unknownCounts'] = dict(sorted(unk.items()))
cov['nullByMeaning'] = dict(info)
cov['sourceRecordsByType'] = dict(collections.Counter(s_['type'] for x in keep for s_ in x['sources']))
cov['noSourceItems'] = sum(1 for x in keep if not x['sources'])

old = json.load(open(SHAMAN_FILE))['meta']
cr = R['crossCheck']
meta = {
    'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'scope': ('Items an Alliance character of any of the nine classes can equip while leveling 1-60: quality 2-5 with reqLvl 1-60, or no reqLvl at any ilvl; '
              'plus quality-1 (white) melee weapons, shields, held-in-off-hand items, ranged weapons and relics from the wowsims db under the same level rule. '
              'Horde-only items and Horde-only sources removed. Shirts, tabards, cosmetic items, fishing poles and items no class can equip are out of scope.'),
    'sameSchemaAs': SHAMAN_FILE + ' (Shaman-only build); every key of that file is kept with the same meaning. New keys: usableBy, equipSlots, weaponSubtype, rangedType; '
                    'slot gains "Ranged", "Relic (Idol)", "Relic (Libram)"; weaponType gains Sword, Polearm, Bow, Gun, Crossbow, Thrown, Wand, Idol, Libram; '
                    'ranged weapons carry a weapon block (min/max/speed/dps, plus spellSchool / damageSchoolWowhead on wands); classAllowlistSource marks allowlists read from a Wowhead "Classes:" line.',
    'usableBy': ('One entry per class that can equip the item on an Alliance character. fromLevel = the level gate from the class rules (Plate 40 for Warrior/Paladin, Mail 40 for '
                 'Hunter/Shaman, Polearms 20, Dual Wield 10/20 for Off Hand-only weapons); null = no gate. The character can equip it at max(reqLvl, fromLevel). slots = '
                 'where that class can put it; one-hand weapons list offHand only for dual-wield classes, with offHandFromLevel = the Dual Wield level.'),
    'equipSlots': 'Paper-doll slots the item fits regardless of class: head, neck, shoulder, back, chest, wrist, hands, waist, legs, feet, finger1/finger2, trinket1/trinket2, mainHand, offHand, ranged. Two-Hand weapons list mainHand and block the off hand.',
    'classRules': {'table': R['classes'], 'notes': R['notes'], 'sources': R['sources'],
                   'crossCheck': {'wowsimsDifferences': cr['wowsimsCapabilityTable']['differences'], 'wowsimsDualWieldSpecs': cr['wowsimsCapabilityTable']['dualWieldSpecs'],
                                  'warcraftTavernDifferences': cr['warcraftTavernTable']['differences'], 'dualWieldRows': cr['dualWieldRows']},
                   'resolutions': {
                       'hunterThrown': 'Allowed. Client DB2 SkillLineAbility spell 2567 (Thrown) has Hunter in its ClassMask and SkillRaceClassInfo row 143 gives Hunter the Thrown skill; Warcraft Tavern lists Thrown for Hunters and names the Thrown trainers. The wowsims capability table leaves Thrown out for Hunters.',
                       'hunterHeldInOffHand': 'Allowed. Held In Off-hand items are armor subclass Miscellaneous, and no proficiency spell in the client DB2 covers that subclass, so no class needs a skill for them. The wowsims weapon table lists OffHand for every class except Hunter.',
                       'shamanDualWield': 'Not allowed. The only Shaman SkillLineAbility row for Dual Wield (674) has AcquireMethod 3 (never learned); wowsims SpecCanDualWieldCapabilities has no Shaman spec. Off Hand-only weapons are therefore not Shaman-usable.',
                       'druidPolearms': 'Allowed from level 20 (Forever change). Client DB2 SkillLineAbility spell 200 includes Druid; SkillRaceClassInfo row 2483 sets MinLevel 20; Warcraft Tavern and wowsims agree.',
                       'rogueOneHandedAxes': 'Allowed (Forever change). Client DB2 spell 196 includes Rogue; Warcraft Tavern and wowsims agree.'}},
    'primarySource': old['primarySource'], 'secondarySources': dict(old['secondarySources'], **{
        'clientDB2': 'https://wago.tools/db2/<Table>/csv?build=1.60.1.70862 (SkillLine, SkillLineAbility, SkillRaceClassInfo, SpellEquippedItems, SpellEffect; class equip rules)',
        'warcraftTavern': 'https://www.warcrafttavern.com/forever/guides/weapon-trainers/ (fetched 2026-11-08; class x weapon skill table, polearm level)'}),
    'statKeys': old['statKeys'],
    'excludedCounts': dict(D['meta']['excludedCounts'], **dict(ex)),
    'supplement': D['meta'].get('supplement'), 'supplementSkipped': D['meta'].get('supplementSkipped'),
    'lootSupplementWowtbc': D['meta'].get('lootSupplementWowtbc'),
    'finalize': {'removed': removed, 'droppedNoClassCanEquip': dropped_nouse, 'wowheadNoteCount': sum(1 for x in keep if x.get('wowheadNote')),
                 'wowheadNote': old['finalize']['wowheadNote']},
    'coverage': cov,
    'count': len(keep)}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({'meta': meta, 'items': keep}, open(OUT, 'w'), indent=1, ensure_ascii=False)
print(len(keep), dict(ex)); print(json.dumps(cov['perClass'])); print(cov['unknownCounts']); print(cov['nullByMeaning'])
