# Shared paths and class-usability helpers for the all-classes item build.
# Every path hangs off ROOT (default /home/claude, override with WOWSIM_ROOT).
import os, json, importlib.util

ROOT = os.environ.get('WOWSIM_ROOT', '/home/claude')
HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.dirname(HERE)                                   # wowsim/pipeline (Shaman scripts, read-only)
CACHE = os.path.join(ROOT, 'cache')
WORK = os.path.join(CACHE, 'allclass')                         # intermediate files of this build
DB2 = os.path.join(ROOT, 'ext', 'wago_allclass')               # Forever client DB2 CSVs (wago.tools)
WEB = os.path.join(CACHE, 'web_allclass')                      # cached guide pages
WOWSIMS = os.path.join(ROOT, 'data', 'repos', 'wowsims-forever')
DBDIR = os.path.join(WOWSIMS, 'assets', 'database')
OUT = os.path.join(ROOT, 'wowsim', 'data', 'items_all.json')
SHAMAN_FILE = os.path.join(ROOT, 'data', 'items_forever_all.json')
BUILD = '1.60.1.70862'
os.makedirs(WORK, exist_ok=True)

CLASS_IDS = {1: 'warrior', 2: 'paladin', 3: 'hunter', 4: 'rogue', 5: 'priest', 7: 'shaman', 8: 'mage', 9: 'warlock', 11: 'druid'}
CLASS_ORDER = ['warrior', 'paladin', 'hunter', 'rogue', 'priest', 'shaman', 'mage', 'warlock', 'druid']
NAME_TO_ID = {v: k for k, v in CLASS_IDS.items()}


def load_build_dataset():
    """Import the Shaman build module (wowsim/pipeline/build_dataset.py) for its helpers and lookup tables."""
    spec = importlib.util.spec_from_file_location('b', os.path.join(PIPE, 'build_dataset.py'))
    b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    return b


def load_wowsims_items():
    items = {}
    for f in ('leftover_db.json', 'db.json'):                  # main db wins, as in targets_all.py
        for it in json.load(open(os.path.join(DBDIR, f)))['items']:
            it['_db'] = f; items[it['id']] = it
    return items


def rules():
    return json.load(open(os.path.join(WORK, 'class_rules.json')))


# ---- item category -> rule key -------------------------------------------------------------
# wowsims proto enums (proto/common.proto): ItemType 1-14, ArmorType 1-4, WeaponType 1-9, HandType 1-4, RangedWeaponType 1-8
WT = {1: 'Axe', 2: 'Dagger', 3: 'Fist Weapon', 4: 'Mace', 5: 'Held In Off-hand', 6: 'Polearm', 7: 'Shield', 8: 'Staff', 9: 'Sword'}
RT = {1: 'Bow', 2: 'Crossbow', 3: 'Gun', 4: 'Thrown', 5: 'Wand', 6: 'Idol', 7: 'Libram', 8: 'Totem'}
ARM = {1: 'Cloth', 2: 'Leather', 3: 'Mail', 4: 'Plate'}
HAND = {1: 'Main Hand', 2: 'One-Hand', 3: 'Off Hand', 4: 'Two-Hand'}
ARMOR_SLOTS = {1: ['head'], 2: ['neck'], 3: ['shoulder'], 4: ['back'], 5: ['chest'], 6: ['wrist'], 7: ['hands'], 8: ['waist'],
               9: ['legs'], 10: ['feet'], 11: ['finger1', 'finger2'], 12: ['trinket1', 'trinket2']}


def weapon_subtype(weapon_type, hand):
    """Warcraft item-subclass style name from wowsims weaponType name + hand."""
    if weapon_type in ('Axe', 'Mace', 'Sword'):
        return ('Two-Handed ' if hand == 'Two-Hand' else 'One-Handed ') + weapon_type
    return weapon_type   # Dagger, Fist Weapon, Staff, Polearm, Shield, Held In Off-hand, ranged/relic names


def usable_by(R, *, item_type, armor=None, weapon_type=None, hand=None, ranged=None, allow=None, faction=None):
    """Return the usableBy list for one item, using the rule table R from class_rules.json.
    item_type: wowsims ItemType number (1-14). armor: 'Cloth'..'Plate' or None. weapon_type: WT name. hand: HAND name.
    ranged: RT name. allow: list of class names (class allowlist) or None. faction: 'Horde'/'Alliance'/None.
    Each entry: {class, fromLevel, slots[, offHandFromLevel]}; fromLevel is the proficiency/training gate (None = no gate)."""
    if faction == 'Horde':
        return []
    out = []
    for c in CLASS_ORDER:
        if allow and c not in allow: continue
        cr = R['classes'][c]
        e = None
        if item_type in (2, 11, 12):                                    # neck, finger, trinket
            e = {'fromLevel': None, 'slots': ARMOR_SLOTS[item_type]}
        elif item_type in (1, 3, 4, 5, 6, 7, 8, 9, 10):
            if not armor:
                e = {'fromLevel': None, 'slots': ARMOR_SLOTS[item_type]}  # misc armor subclass: no proficiency exists
            elif armor in cr['armor']:
                e = {'fromLevel': cr['armor'][armor], 'slots': ARMOR_SLOTS[item_type]}
        elif item_type == 13:
            if weapon_type == 'Held In Off-hand':
                e = {'fromLevel': None, 'slots': ['offHand']}
            elif weapon_type == 'Shield':
                if 'Shield' in cr['armor']: e = {'fromLevel': cr['armor']['Shield'], 'slots': ['offHand']}
            elif weapon_type and hand:
                sub = weapon_subtype(weapon_type, hand)
                if sub in cr['weapons']:
                    lv = cr['weapons'][sub]; dw = cr['dualWield']
                    if hand in ('Two-Hand', 'Main Hand'):
                        e = {'fromLevel': lv, 'slots': ['mainHand']}
                    elif hand == 'One-Hand':
                        e = {'fromLevel': lv, 'slots': ['mainHand'] + (['offHand'] if dw is not None else [])}
                        if dw is not None: e['offHandFromLevel'] = max(lv or 1, dw)
                    elif hand == 'Off Hand' and dw is not None:
                        e = {'fromLevel': max(lv or 1, dw), 'slots': ['offHand']}
        elif item_type == 14 and ranged:
            if ranged in cr['ranged']:
                e = {'fromLevel': cr['ranged'][ranged], 'slots': ['ranged']}
        if e is not None:
            if e['fromLevel'] in (0, 1): e['fromLevel'] = None
            out.append(dict({'class': c}, **e))
    return out


def equip_slots(item_type, weapon_type=None, hand=None):
    if item_type in ARMOR_SLOTS: return ARMOR_SLOTS[item_type]
    if item_type == 14: return ['ranged']
    if item_type == 13:
        if weapon_type in ('Shield', 'Held In Off-hand'): return ['offHand']
        return {'Main Hand': ['mainHand'], 'Two-Hand': ['mainHand'], 'One-Hand': ['mainHand', 'offHand'], 'Off Hand': ['offHand']}.get(hand, [])
    return []
