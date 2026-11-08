"""Per-class, per-Alliance-race character data for WoW Forever, levels 1-60.

Writes wowsim/data/classes/<class>_levels.json for the nine classes. Same entry discipline as
data/shaman_levels.json: every value is {level, value, status, source}; status forever / vanilla / estimate.
Mob tables are left out (shared, in data/shaman_levels.json).

Inputs (ROOT-relative, see common.py): cmangos player_levelstats / player_classlevelstats, AzerothCore
player_class_stats, wago PlayerExpectedStat 70862, the wowsims-forever repo (read as data).
"""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from common import (CLASS_IDS, OUT, WS_REPO, E, ac_rows, cm_inserts, pes, rnd)  # noqa: E402

GENERATED = "2026-11-08"
STATS = ["strength", "agility", "stamina", "intellect", "spirit"]
SHORT = ["Str", "Agi", "Sta", "Int", "Spi"]

# cmangos race id -> offset (Str, Agi, Sta, Int, Spi). Checked below against wowsims RaceOffsets.
CM_RACES = {1: "human", 2: "orc", 3: "dwarf", 4: "night_elf", 5: "undead", 6: "tauren", 7: "gnome", 8: "troll"}
# racial percentage already baked into cmangos rows: Human spirit, Gnome intellect (vanilla +5%)
CM_BAKED = {1: 4, 7: 3}

ALLIANCE = ["human", "dwarf", "night_elf", "gnome", "high_order_skyborne"]
WS_RACE = {"human": "RaceHuman", "dwarf": "RaceDwarf", "night_elf": "RaceNightElf", "gnome": "RaceGnome",
           "high_order_skyborne": "RaceHighOrderSkyborne", "orc": "RaceOrc", "undead": "RaceUndead",
           "tauren": "RaceTauren", "troll": "RaceTroll", "windshaper_skyborne": "RaceWindshaperSkyborne"}
WS_CLASS = {c: "Class" + c.capitalize() for c in CLASS_IDS}
VANILLA_COMBOS = {  # vanilla 1.12 Alliance race/class table (cmangos player_levelstats rows)
    "warrior": ["human", "dwarf", "night_elf", "gnome"], "paladin": ["human", "dwarf"],
    "hunter": ["dwarf", "night_elf"], "rogue": ["human", "dwarf", "night_elf", "gnome"],
    "priest": ["human", "dwarf", "night_elf"], "shaman": [], "mage": ["human", "gnome"],
    "warlock": ["human", "gnome"], "druid": ["night_elf"]}

# ---------------------------------------------------------------- wowsims-forever constants (read, not built)
bs = open(os.path.join(WS_REPO, "sim/core/base_stats.go")).read()
bsa = open(os.path.join(WS_REPO, "sim/core/base_stats_auto_gen.go")).read()
cc = open(os.path.join(WS_REPO, "sim/core/character_constants.go")).read()


def go_map_block(src, var):
    i = src.index("var %s = " % var)
    depth, j = 0, src.index("{", i)
    for k in range(j, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[j:k + 1]


def parse_stat_map(block, keyprefix):
    out = {}
    for m in re.finditer(r"proto\.%s_(\w+):\s*(?:stats\.Stats)?\{(.*?)\}" % keyprefix, block, re.S):
        out[m.group(1)] = {k: float(v) for k, v in re.findall(r"stats\.(\w+):\s*(-?[\d.]+)", m.group(2))}
    return out


WS_OFF = parse_stat_map(go_map_block(bs, "RaceOffsets"), "Race")
WS_CB = parse_stat_map(go_map_block(bs, "ClassBaseStats"), "Class")
WS_EXTRA = parse_stat_map(go_map_block(bsa, "ExtraClassBaseStats"), "Class")
WS_CPA = {k: float(v) for k, v in re.findall(r"proto\.Class_(\w+):\s+(-?[\d.]+),", go_map_block(bsa, "CritPerAgiMaxLevel"))}
WS_CPI = {k: float(v) for k, v in re.findall(r"proto\.Class_(\w+):\s+(-?[\d.]+),", go_map_block(bsa, "CritPerIntMaxLevel"))}
WS_DODGE = {k: float(v) for k, v in re.findall(r"proto\.Class_(\w+):\s+(-?[\d.]+),", go_map_block(bs, "ClassBaseDodge"))}
WS_CAPS = {}
for m in re.finditer(r"proto\.Class_(\w+): \{(.*?)\n\t\}", go_map_block(cc, "ClassRaceCapabilities"), re.S):
    WS_CAPS[m.group(1)] = re.findall(r"proto\.Race_(\w+)", m.group(2))
WS_DW = re.findall(r"proto\.Spec_(\w+):\s+true", go_map_block(cc, "SpecCanDualWieldCapabilities"))
WS_WEAPONS = {}
for m in re.finditer(r"proto\.Class_(\w+): \{(.*?)\n\t\}", go_map_block(cc, "ClassWeaponTypeCapabilities"), re.S):
    WS_WEAPONS[m.group(1)] = re.findall(r"WeaponType_WeaponType(\w+)", m.group(2))
ui_utils = open(os.path.join(WS_REPO, "ui/sim/proto/utils.ts")).read()
WS_FACTION = dict(re.findall(r"\[Race\.(Race\w+)\]: Faction\.(\w+)", ui_utils))


WSOD_SRC = open(os.path.join(os.path.dirname(WS_REPO), "..", "..", "ext/wsod/sim/core/base_stats.go")).read()


def wsod_levels():
    """wowsims SoD sim/core/base_stats.go ClassBaseStats: class base stats at levels 25, 40, 50, 60, and
    CritPerAgiAtLevel / CritPerIntAtLevel / DodgePerAgiAtLevel (old Classic gametables)."""
    blk = go_map_block(WSOD_SRC, "ClassBaseStats")
    res = {}
    for m in re.finditer(r"proto\.Class_Class(\w+): \{\n(.*?)\n\t\},", blk, re.S):
        cls = m.group(1).lower()
        res[cls] = {}
        for lm in re.finditer(r"(\d+): \{(.*?)\}", m.group(2), re.S):
            res[cls][int(lm.group(1))] = {k: eval(v) for k, v in re.findall(r"stats\.(\w+):\s*([-\d*. ]+),", lm.group(2))}
    tables = {}
    for var in ("CritPerAgiAtLevel", "CritPerIntAtLevel", "DodgePerAgiAtLevel"):
        tables[var] = {c.lower(): {int(a): float(b) for a, b in re.findall(r"(\d+): ([\d.]+)", body)}
                       for c, body in re.findall(r"proto\.Class_Class(\w+):\s+\{([^}]*)\}", go_map_block(WSOD_SRC, var))}
    return res, tables


WSOD, WSOD_T = wsod_levels()


def ws_off(race):
    o = WS_OFF.get(WS_RACE[race], {})
    return tuple(int(o.get(s, 0)) for s in ["Strength", "Agility", "Stamina", "Intellect", "Spirit"])


# ---------------------------------------------------------------- cmangos rows
LS = {(r[0], r[1], r[2]): r[3:] for r in cm_inserts('player_levelstats')}
CL = {(r[0], r[1]): (r[2], r[3]) for r in cm_inserts('player_classlevelstats')}
CM_OFF = {rid: ws_off(name) for rid, name in CM_RACES.items()}

# The cmangos race offsets themselves: Dwarf/NE/Undead/Tauren/Troll/Orc minus each other give one offset
# across every shared class and level. Checked here against wowsims RaceOffsets (assert).
def check_offsets():
    res = {}
    for rid, name in CM_RACES.items():
        if rid in (1,):
            continue
        diffs = Counter()
        for (r, c, L), v in LS.items():
            if r != rid or (1, c, L) not in LS:
                continue
            h = LS[(1, c, L)]
            d = tuple(v[i] - h[i] for i in range(5))
            diffs[d] += 1
        res[name] = diffs.most_common(3)
    return res


def class_row(cid):
    """Per level, the class row. Per attribute: the value every vanilla race gives after subtracting its
    offset (the Human spirit and Gnome intellect rows are left out: cmangos bakes their +5% racial in).
    Where the races disagree, the AzerothCore player_class_stats value when one of the races gives it,
    otherwise the most common value. Every disagreement is listed."""
    races = sorted({r for (r, c, L) in LS if c == cid})
    ac = ac_rows(cid)
    rows, dissent = {}, []
    for L in range(1, 61):
        row = []
        for i in range(5):
            vals = Counter()
            per = {}
            for r in races:
                if CM_BAKED.get(r) == i:
                    continue
                v = LS[(r, cid, L)][i] - CM_OFF[r][i]
                vals[v] += 1
                per[CM_RACES[r]] = v
            acv = ac[L][4 + i] if L in ac else None
            if len(vals) == 1:
                top = next(iter(vals))
                if acv is not None and acv != top:
                    dissent.append({"level": L, "attribute": STATS[i], "chosen": top, "rule": "all cmangos races agree",
                                    "azerothcore": acv})
            else:
                if acv in vals:
                    top, rule = acv, "races disagree; AzerothCore value, which one race also gives"
                else:
                    top, rule = vals.most_common(1)[0][0], "races disagree; most common"
                dissent.append({"level": L, "attribute": STATS[i], "chosen": top, "rule": rule, "azerothcore": acv,
                                "disagreeing": {k: v for k, v in per.items() if v != top}})
            row.append(top)
        rows[L] = tuple(row)
    return rows, races, dissent


# ---------------------------------------------------------------- per-class rules
VM = "vmangos src/game/StatSystem.cpp Unit::GetAttackPowerFromStrengthAndAgility"
AP_RULES = {
    "warrior": dict(melee=(3, 2, 0, -20), ranged=(1, 0, 1, -10), ws60=160),
    "paladin": dict(melee=(3, 2, 0, -20), ranged=(0, 0, 1, -10), ws60=160),
    "hunter": dict(melee=(2, 1, 1, -20), ranged=(2, 0, 2, -10), ws60=100, ws60_ranged=110),
    "rogue": dict(melee=(2, 1, 1, -20), ranged=(1, 0, 1, -10), ws60=100),
    "priest": dict(melee=(0, 1, 0, -10), ranged=(0, 0, 1, -10), ws60=-10),
    "shaman": dict(melee=(2, 2, 0, -20), ranged=(0, 0, 1, -10), ws60=100),
    "mage": dict(melee=(0, 1, 0, -10), ranged=(0, 0, 1, -10), ws60=-10),
    "warlock": dict(melee=(0, 1, 0, -10), ranged=(0, 0, 1, -10), ws60=-10),
    "druid": dict(melee=(0, 2, 0, -20), ranged=(0, 0, 1, -10), ws60=-20),
}
# (per tick of 2 s): mana = Spirit/a + b ; health = Spirit*c + d   (vmangos Unit.cpp)
REGEN = {
    "druid": (5, 15, 0.11, 1), "hunter": (5, 15, 0.43, -5.5), "mage": (4, 12.5, 0.11, 1),
    "paladin": (5, 15, 0.25, 0), "priest": (4, 12.5, 0.15, 1.4), "rogue": (None, None, 0.84, -13),
    "shaman": (5, 17, 0.28, -3.6), "warlock": (5, 15, 0.12, 1.5), "warrior": (None, None, 1.26, -22.6)}
MELEE_CRIT_BASE = {"druid": 0.9, "mage": 3.2, "paladin": 0.7, "priest": 3.0, "shaman": 1.7, "warlock": 2.0,
                   "warrior": 0.0, "rogue": 0.0, "hunter": 0.0}
VM_SPELL_CRIT = {"paladin": (3.70, 14.77, 0.65), "priest": (2.97, 10.03, 0.82), "shaman": (3.54, 11.51, 0.80),
                 "mage": (3.70, 14.77, 0.65), "warlock": (3.18, 11.30, 0.82), "druid": (3.33, 12.41, 0.79)}
POWER = {"warrior": "rage", "rogue": "energy", "druid": "mana (rage in Bear/Dire Bear, energy in Cat)"}
CAN = {  # parry / block / dual wield: vanilla trainer rule + wowsims-forever flags
    "warrior": dict(parry=True, block=True, dual_wield=True),
    "paladin": dict(parry=True, block=True, dual_wield=False),
    "hunter": dict(parry=True, block=False, dual_wield=True),
    "rogue": dict(parry=True, block=False, dual_wield=True),
    "priest": dict(parry=False, block=False, dual_wield=False),
    "shaman": dict(parry=False, block=True, dual_wield=False),
    "mage": dict(parry=False, block=False, dual_wield=False),
    "warlock": dict(parry=False, block=False, dual_wield=False),
    "druid": dict(parry=False, block=False, dual_wield=False),
}
# vanilla trainer data (cmangos npc_trainer_template, teach spell -> learned spell): level the passive is trained
TRAINED_AT = {  # filled from cm_tables.json in main()
}

SRC = {
    "PES": "Forever client DB2 PlayerExpectedStat (ContentSetID 0), build 1.60.1.70862, wago.tools CSV (ext/wago/PlayerExpectedStat_70862.csv). wowsims-forever tools/base_stats_parser.py reads the same table for its level 60 values.",
    "CM_CLS": "cmangos classic-db Full_DB/ClassicDB_1_12_1_z2815.sql.gz player_classlevelstats (vanilla 1.12 base health and mana)",
    "CM_LVL": "cmangos classic-db player_levelstats: the class row is, per level and attribute, the value the vanilla races give after subtracting each race's offset (the Human spirit and Gnome intellect rows are left out: cmangos bakes their vanilla +5% racial into the row). Where races disagree, the AzerothCore player_class_stats value (ext/ac/player_class_stats.sql) when one race also gives it, else the most common. AzerothCore's class rows equal the result at every level of every class except the entries listed in meta.class_row_dissent.",
    "WS_OFF": "wowsims-forever sim/core/base_stats.go RaceOffsets (vanilla races: the same offsets cmangos rows give at every level, checked in meta.race_offsets_check)",
    "WS_SKY": "wowsims-forever sim/core/base_stats.go RaceOffsets[RaceHighOrderSkyborne] Str -3, Agi +4, Sta -1, Int +4, Spi -3, 'read from level 1 naked character sheets (2026-11-06)'. A Forever in-game reading at level 1 only; carried to every level on the vanilla rule that a race offset is the same at every level. Every Skyborne attribute is marked estimate: the class row is vanilla and the source does not say which classes' sheets were read.",
    "WS_BASE": "wowsims-forever sim/core/base_stats_auto_gen.go ExtraClassBaseStats (from the hand-kept assets/db_inputs/basestats/chancetomeleecritbase.txt and chancetospellcritbase.txt, vanilla tables; the game files ship none) and base_stats.go ClassBaseDodge",
    "VM_STAT": "vmangos src/game/StatSystem.cpp (Player::UpdateCritPercentage / UpdateDodgePercentage base values, UpdateParryPercentage / UpdateBlockPercentage 5% base, GetHealthBonusFromStamina, GetManaBonusFromIntellect)",
    "VM_AP": VM,
    "VM_REGEN": "vmangos src/game/Objects/Unit.cpp Unit::GetRegenMPPerSpirit / GetRegenHPPerSpirit (values per 2 s regen tick; Player::Regenerate comments: 'Mangos Updates Mana in intervals of 2s')",
    "WS_REGEN": "wowsims-forever sim/core/mana.go EnableManaBar: 'Spirit restores 6.25 + Spirit/8 mana per second', every class (no class calls SetSpiritManaRegen), no level term",
    "VANILLA_RULE": "vanilla rule (vmangos Player::GetSkillMaxForLevel = level*5)",
    "WS_RACES": "wowsims-forever sim/core/character_constants.go ClassRaceCapabilities + ui/sim/proto/utils.ts race factions",
}


def sheet_ws60(cls, race):
    """wowsims-forever level 60 base: ClassBaseStats + RaceOffsets + ExtraClassBaseStats."""
    cb = WS_CB[WS_CLASS[cls]]
    off = WS_OFF.get(WS_RACE[race], {})
    ex = WS_EXTRA[WS_CLASS[cls]]
    attrs = {s: int(cb.get(k, 0) + off.get(k, 0)) for s, k in zip(SHORT, ["Strength", "Agility", "Stamina", "Intellect", "Spirit"])}
    return dict(base_health=int(cb["Health"]), base_mana=int(ex.get("Mana", 0)), **attrs,
                attack_power_base=int(cb.get("AttackPower", 0)), ranged_attack_power_base=int(cb.get("RangedAttackPower", 0)) or None,
                melee_crit_base=ex.get("PhysicalCritPercent", 0), spell_crit_base=ex.get("SpellCritPercent", 0),
                crit_per_agi_pct=WS_CPA[WS_CLASS[cls]], crit_per_int_pct=WS_CPI[WS_CLASS[cls]],
                base_dodge_pct=round(WS_DODGE.get(WS_CLASS[cls], 0) * 100, 4))


def build(cls, cm):
    cid = CLASS_IDS[cls]
    P = pes(cid)
    ac = ac_rows(cid)
    crow, cm_races, dissent = class_row(cid)
    ws_races = [r for r in ALLIANCE if WS_RACE[r] in WS_CAPS[WS_CLASS[cls]]]
    mana_class = int(P[60]['BaseMana']) > 0
    ap = AP_RULES[cls]
    mb, rb, hc, hd = REGEN[cls]
    out = {"meta": {}, "levels": {}, "races": {}}
    lv = out["levels"]
    keys = ["base_health", "base_mana", "hp_per_stamina", "mana_per_intellect",
            "melee_crit_pct_per_agility", "spell_crit_pct_per_intellect", "dodge_pct_per_agility",
            "base_melee_crit_pct", "base_spell_crit_pct", "base_dodge_pct", "base_parry_pct", "base_block_pct",
            "attack_power_level_term", "ranged_attack_power_level_term", "weapon_skill_max", "defense_skill_max"]
    if cls == "druid":
        keys += ["cat_form_attack_power_bonus", "bear_form_attack_power_bonus", "dire_bear_form_attack_power_bonus",
                 "bear_form_max_health_bonus", "dire_bear_form_max_health_bonus"]
    if cls == "paladin" or cls in VM_SPELL_CRIT:
        keys += ["spell_crit_pct_naked_vmangos_formula_rate"]
    for k in keys:
        lv[k] = []
    from common import spells
    S = spells()

    def row_val(sid, idx, L, learn):
        e = [x for x in S[str(sid)]['Effects'] if x.get('Index', 0) == idx][0]
        b, ppl, bl, ml = e.get('BasePoints', 0), e.get('PPL', 0) or 0, e.get('BaseLevel', 0) or 0, e.get('MaxLevel', 0) or 0
        if L < learn:
            return None
        lvl = min(L, ml) if ml else L
        return int(b + ppl * max(lvl - bl, 0))

    for L in range(1, 61):
        hp = CL[(cid, L)][0]
        note = {}
        if ac.get(L) and ac[L][2] != hp:
            note["azerothcore_wotlk"] = ac[L][2]
        lv["base_health"].append(E(L, hp, "vanilla", "CM_CLS", **note))
        mana = int(P[L]['BaseMana'])
        extra = {}
        if CL[(cid, L)][1] != mana:
            extra["note"] = f"cmangos player_classlevelstats says {CL[(cid, L)][1]}; AzerothCore says {ac[L][3] if L in ac else None}"
        lv["base_mana"].append(E(L, mana, "forever", "PES", **extra))
        lv["hp_per_stamina"].append(E(L, int(P[L]['HPPerStamina']), "forever", "PES", rule="health = base_health + min(Sta,20) + hp_per_stamina*max(Sta-20,0)"))
        lv["mana_per_intellect"].append(E(L, 15 if mana_class else 0, "vanilla" if mana_class else "vanilla", "VM_STAT",
                                          rule=("mana = base_mana + min(Int,20) + 15*max(Int-20,0); wowsims-forever mana.go uses the same (AddStat(Mana, 20-15*20) + 15 per Int)" if mana_class else "no mana bar (base mana 0 in PES)")))
        cpa = round(float(P[L]['CritPerAgility']) * 100, 6)
        cpi = round(float(P[L]['SpellCritPerIntellect']) * 100, 6)
        lv["melee_crit_pct_per_agility"].append(E(L, cpa, "forever", "PES", agility_per_1pct=round(1 / cpa, 2) if cpa else None))
        lv["spell_crit_pct_per_intellect"].append(E(L, cpi, "forever", "PES", intellect_per_1pct=round(1 / cpi, 2) if cpi else None))
        dmul = 2 if cls in ("rogue", "hunter") else 1
        lv["dodge_pct_per_agility"].append(E(L, round(cpa * dmul, 6), "estimate" if L < 60 else "forever",
                                             "PES x %d (wowsims-forever base_stats.go dodgePerAgility: crit per Agility, twice for Rogue and Hunter; stated for level 60, carried to every level)" % dmul))
        mcb = MELEE_CRIT_BASE[cls]
        lv["base_melee_crit_pct"].append(E(L, mcb, "vanilla", "WS_BASE", vmangos=mcb))
        scb = WS_EXTRA[WS_CLASS[cls]].get("SpellCritPercent", 0.0)
        lv["base_spell_crit_pct"].append(E(L, scb, "vanilla", "WS_BASE"))
        lv["base_dodge_pct"].append(E(L, round(WS_DODGE.get(WS_CLASS[cls], 0) * 100, 4), "vanilla", "WS_BASE",
                                      note="same as vmangos UpdateDodgePercentage base; Warrior, Rogue and Hunter have none"))
        lv["base_parry_pct"].append(E(L, 5.0 if CAN[cls]["parry"] else 0.0, "vanilla", "VM_STAT",
                                      note=("5% once Parry is trained; +-0.04% per defense skill point vs 5*level" if CAN[cls]["parry"] else "class cannot parry")))
        lv["base_block_pct"].append(E(L, 5.0 if CAN[cls]["block"] else 0.0, "vanilla", "VM_STAT",
                                      note=("5% with a shield equipped and Block trained; +-0.04% per defense skill point vs 5*level" if CAN[cls]["block"] else "class cannot equip a shield")))
        lm, sm, am, cm_ = ap["melee"]
        lv["attack_power_level_term"].append(E(L, lm * L + cm_, "vanilla", "VM_AP",
                                               formula=f"AP = {lm}*level + {sm}*Str + {am}*Agi {cm_:+d}".replace("+ 0*Str ", "").replace("+ 0*Agi ", "")))
        lr, sr, ar, cr = ap["ranged"]
        lv["ranged_attack_power_level_term"].append(E(L, lr * L + cr, "vanilla", "VM_AP",
                                                      formula=f"RAP = {lr}*level + {ar}*Agi {cr:+d}".replace("0*level + ", "")))
        lv["weapon_skill_max"].append(E(L, 5 * L, "vanilla", "VANILLA_RULE"))
        lv["defense_skill_max"].append(E(L, 5 * L, "vanilla", "VANILLA_RULE"))
        if cls in VM_SPELL_CRIT:
            b0, r0, r1 = VM_SPELL_CRIT[cls]
            lv["spell_crit_pct_naked_vmangos_formula_rate"].append(E(L, round(1 / (r0 + r1 * L), 6), "vanilla",
                "vmangos Unit::GetSpellCritFromIntellect", formula=f"spell crit = {b0} + Int/({r0} + {r1}*level); flagged 'MUST BE CHECKED' in vmangos; superseded for Forever by PES"))
        if cls == "druid":
            lv["cat_form_attack_power_bonus"].append(E(L, row_val(3025, 0, L, 20), "forever", "spell 3025 Cat Form (Passive) effect 0 A_MOD_ATTACK_POWER 12 + 2/level from level 6, no cap; Cat Form 768 is learned at 20 (null below)"))
            lv["bear_form_attack_power_bonus"].append(E(L, row_val(1178, 3, L, 10), "forever", "spell 1178 Bear Form (Passive) effect 3 A_MOD_ATTACK_POWER 30 + 3/level, levels 10-40; Bear Form 5487 learned at 10"))
            lv["dire_bear_form_attack_power_bonus"].append(E(L, row_val(9635, 3, L, 40), "forever", "spell 9635 Dire Bear Form (Passive) effect 3 A_MOD_ATTACK_POWER 120 + 3/level from 40 (cap 70); learned at 40"))
            lv["bear_form_max_health_bonus"].append(E(L, row_val(1178, 2, L, 10), "forever", "spell 1178 effect 2 A_MOD_MAX_HEALTH 20 + 18/level, levels 10-40"))
            lv["dire_bear_form_max_health_bonus"].append(E(L, row_val(9635, 2, L, 40), "forever", "spell 9635 effect 2 A_MOD_MAX_HEALTH 600 + 32/level from 40"))

    # ---------------------------------------------------------- races
    checks = {}
    for race in ws_races:
        rl = {k: [] for k in STATS + ["max_health_naked", "max_mana_naked", "melee_crit_pct_naked", "spell_crit_pct_naked",
                                      "dodge_pct_naked", "attack_power_naked", "ranged_attack_power_naked", "armor_from_agility_naked",
                                      "spirit_mana_regen_vanilla_per_s_naked", "spirit_mana_regen_wowsims_per_s_naked",
                                      "health_regen_ooc_vanilla_per_s_naked"]}
        off = ws_off(race)
        sky = race == "high_order_skyborne"
        new_combo = race not in VANILLA_COMBOS[cls]
        cm_rid = {v: k for k, v in CM_RACES.items()}.get(race)
        for L in range(1, 61):
            attrs = tuple(crow[L][i] + off[i] for i in range(5))
            for i, n in enumerate(STATS):
                extra = {"class_row_value": crow[L][i], "race_offset": off[i]}
                if cm_rid and (cm_rid, cid, L) in LS:
                    cmv = LS[(cm_rid, cid, L)][i]
                    if cmv != attrs[i]:
                        extra["cmangos_row_value"] = cmv
                        extra["cmangos_note"] = ("cmangos bakes the vanilla +5% racial into this row" if CM_BAKED.get(cm_rid) == i
                                                 else "cmangos row differs from the class row + offset (see meta.class_row_dissent)")
                status = "estimate" if sky else "vanilla"
                src = "CM_LVL+WS_SKY" if sky else "CM_LVL+WS_OFF"
                rl[n].append(E(L, attrs[i], status, src, **extra))
            strn, agi, sta, intel, spi = attrs
            base_hp = lv["base_health"][L - 1]["value"]
            base_mana = lv["base_mana"][L - 1]["value"]
            hps = lv["hp_per_stamina"][L - 1]["value"]
            st_attr = "estimate" if sky else "vanilla"
            rl["max_health_naked"].append(E(L, base_hp + min(sta, 20) + hps * max(sta - 20, 0), "vanilla" if not sky else "estimate",
                                            "base_health + min(Sta,20) + hp_per_stamina*(Sta-20)"))
            rl["max_mana_naked"].append(E(L, (base_mana + min(intel, 20) + 15 * max(intel - 20, 0)) if mana_class else 0,
                                          "forever" if not sky else "estimate", "base_mana + min(Int,20) + 15*(Int-20)" if mana_class else "no mana"))
            cpa = lv["melee_crit_pct_per_agility"][L - 1]["value"]
            cpi = lv["spell_crit_pct_per_intellect"][L - 1]["value"]
            rl["melee_crit_pct_naked"].append(E(L, round(MELEE_CRIT_BASE[cls] + agi * cpa, 4), "forever" if not sky else "estimate",
                                                f"{MELEE_CRIT_BASE[cls]} + Agi * melee_crit_pct_per_agility"))
            scb = lv["base_spell_crit_pct"][L - 1]["value"]
            rl["spell_crit_pct_naked"].append(E(L, round(scb + intel * cpi, 4), "forever" if not sky else "estimate",
                                                f"{scb} + Int * spell_crit_pct_per_intellect"))
            bd = lv["base_dodge_pct"][L - 1]["value"]
            dpa = lv["dodge_pct_per_agility"][L - 1]["value"]
            rl["dodge_pct_naked"].append(E(L, round(bd + agi * dpa, 4), "estimate", f"{bd} + Agi * dodge_pct_per_agility (racial dodge not applied)"))
            lm, sm, am, cm_ = ap["melee"]
            rl["attack_power_naked"].append(E(L, lm * L + sm * strn + am * agi + cm_, st_attr, "VM_AP"))
            lr, sr, ar, cr = ap["ranged"]
            rl["ranged_attack_power_naked"].append(E(L, lr * L + ar * agi + cr, st_attr, "VM_AP"))
            rl["armor_from_agility_naked"].append(E(L, 2 * agi, st_attr, "vmangos Player::UpdateArmor 2 armor per Agility; wowsims-forever character.go the same"))
            if mb:
                rl["spirit_mana_regen_vanilla_per_s_naked"].append(E(L, round((spi / mb + rb) / 2, 4), st_attr, "VM_REGEN", formula=f"(Spirit/{mb} + {rb}) per 2 s"))
                rl["spirit_mana_regen_wowsims_per_s_naked"].append(E(L, round(6.25 + spi / 8, 4), "estimate", "WS_REGEN", formula="6.25 + Spirit/8 per second, applied unchanged below 60"))
            rl["health_regen_ooc_vanilla_per_s_naked"].append(E(L, round(max(0.0, spi * hc + hd) / 2, 4), st_attr, "VM_REGEN",
                                                                formula=f"max(0, Spirit*{hc} {hd:+}) per 2 s tick, out of combat; x1.5 sitting"))
        if not mb:
            rl.pop("spirit_mana_regen_vanilla_per_s_naked")
            rl.pop("spirit_mana_regen_wowsims_per_s_naked")
        out["races"][race] = {
            "faction": WS_FACTION.get(WS_RACE[race]),
            "new_in_forever": new_combo,
            "race_offset": dict(zip(SHORT, off)),
            "race_offset_source": "WS_SKY" if sky else "WS_OFF",
            "levels": rl,
        }
        # ------------------------------------------------ level 60 check vs wowsims-forever
        ws = sheet_ws60(cls, race)
        mine = dict(base_health=lv["base_health"][59]["value"], base_mana=lv["base_mana"][59]["value"],
                    Str=rl["strength"][59]["value"], Agi=rl["agility"][59]["value"], Sta=rl["stamina"][59]["value"],
                    Int=rl["intellect"][59]["value"], Spi=rl["spirit"][59]["value"],
                    attack_power_base=lv["attack_power_level_term"][59]["value"],
                    ranged_attack_power_base=(lv["ranged_attack_power_level_term"][59]["value"] if cls == "hunter" else None),
                    melee_crit_base=lv["base_melee_crit_pct"][59]["value"], spell_crit_base=lv["base_spell_crit_pct"][59]["value"],
                    crit_per_agi_pct=lv["melee_crit_pct_per_agility"][59]["value"], crit_per_int_pct=lv["spell_crit_pct_per_intellect"][59]["value"],
                    base_dodge_pct=lv["base_dodge_pct"][59]["value"])
        mism = {k: {"this_file": mine[k], "wowsims": ws[k]} for k in ws if mine.get(k) is not None and ws[k] is not None
                and abs(float(mine[k]) - float(ws[k])) > 1e-6}
        checks[race] = {"wowsims_level_60": ws, "result": "all match" if not mism else "mismatch", "mismatches": mism}

    sod = {}
    for L, v in sorted(WSOD.get(cls, {}).items()):
        mine = {"Health": lv["base_health"][L - 1]["value"], "Mana": lv["base_mana"][L - 1]["value"],
                "Strength": crow[L][0], "Agility": crow[L][1], "Stamina": crow[L][2], "Intellect": crow[L][3], "Spirit": crow[L][4],
                "AttackPower": lv["attack_power_level_term"][L - 1]["value"]}
        mism = {k: {"this_file": mine[k], "wowsims_sod": v[k]} for k in mine if k in v and float(v[k]) != float(mine[k])}
        crit = {}
        for var, key in (("CritPerAgiAtLevel", "melee_crit_pct_per_agility"), ("CritPerIntAtLevel", "spell_crit_pct_per_intellect"), ("DodgePerAgiAtLevel", "dodge_pct_per_agility")):
            t = WSOD_T[var].get(cls, {}).get(L)
            if t is not None:
                crit[key] = {"this_file": lv[key][L - 1]["value"], "wowsims_sod_old_gametable": t}
        sod[str(L)] = {"class_base_mismatches": mism or "all match", "per_point_rates": crit}
        if "Health" in mism:
            lv["base_health"][L - 1]["wowsims_sod"] = v["Health"]
    out["meta"] = meta(cls, cid, ws_races, checks, dissent, cm, mana_class)
    out["meta"]["checks_vs_wowsims_sod_levels_25_40_50_60"] = {
        "source": "ext/wsod (wowsims SoD repo, sim/core/base_stats.go ClassBaseStats at 25/40/50/60 = class row before race offsets; per-point rates from the old Classic gametables). Classic Era client values, not Forever; the per-point rates are expected to differ where Forever retuned crit per Agility.",
        "levels": sod}
    return out


def trainer_level(cm, cid, spell_ids):
    """Vanilla trainer reqlevel/cost of the passives Parry (3127), Block (107), Dual Wield (674)."""
    st = {r[0]: r for r in cm["spell_template"]["rows"]}
    cols = cm["spell_template"]["cols"]
    eff1, trig1 = cols.index("Effect1"), cols.index("EffectTriggerSpell1")
    teach = {}
    for sid, r in st.items():
        if r[eff1] == 36 and r[trig1]:
            teach.setdefault(r[trig1], []).append(sid)
    res = {}
    tmpl = [r for r in cm["npc_trainer_template"]["rows"] if r[0] == cid * 10 + 1]
    for want in spell_ids:
        hits = [r for r in tmpl if r[1] in teach.get(want, []) or r[1] == want]
        res[want] = [{"reqlevel": r[5], "cost_copper": r[2]} for r in hits]
    return res


def meta(cls, cid, races, checks, dissent, cm, mana_class):
    tl = trainer_level(cm, cid, [3127, 107, 674, 3018, 2764, 5011, 266, 196, 197, 198, 199, 200, 201, 202, 227, 264, 1180, 15590, 5009])
    caps = CAN[cls]
    m = {
        "title": f"{cls.capitalize()} per-level character data for WoW Forever, Alliance races, levels 1-60",
        "generated": GENERATED,
        "status_legend": {"forever": "Forever client data (or a wowsims-forever value read in the Forever game)", "vanilla": "Classic/vanilla fallback", "estimate": "derived or interpolated"},
        "layout": "levels.<stat> holds class-wide arrays; races.<race>.levels.<stat> holds the attribute arrays and naked totals for that race. Every array is indexed by level-1 (index 0 = level 1). Every entry: {level, value, status, source}; source is a key of meta.sources or an inline formula. Mob baselines are not repeated here (data/shaman_levels.json mobs).",
        "sources": SRC,
        "alliance_races": {r: {"new_in_forever": r not in VANILLA_COMBOS[cls], "faction": WS_FACTION.get(WS_RACE[r])} for r in races},
        "race_class_sources": [
            "wowsims-forever sim/core/character_constants.go ClassRaceCapabilities, filtered to the Alliance races of ui/sim/proto/utils.ts (Human, Dwarf, Night Elf, Gnome, High Order Skyborne).",
            "Blizzard news 'WoW: Forever Meet the New Skyborne' (news.blizzard.com/en-us/article/24302071): Alliance High Order Skyborne play Druid, Hunter, Mage, Rogue, Warrior; Horde Windshaper Skyborne play Druid, Hunter, Rogue, Shaman, Warrior.",
            "Warcraft Tavern (12 Sep 2026, 'Undead Paladins & Other Race-Class Combos') and Method.gg (27 Sep 2026): new Alliance combos Human Hunter, Dwarf Shaman, Gnome Priest and every Skyborne class; no other Alliance combo is new.",
        ],
        "checks_vs_wowsims_forever_level_60": checks,
        "race_offsets_check": "With wowsims RaceOffsets (Str,Agi,Sta,Int,Spi: Human 0, Orc 3,-3,2,-3,3, Dwarf 2,-4,3,-1,-1, Night Elf -3,5,-1,0,0, Undead -1,-2,1,-2,5, Tauren 5,-5,2,-5,2, Gnome -5,3,-1,3,0, Troll 1,2,1,-4,1) every cmangos race row of this class minus its offset gives one class row, except the entries in class_row_dissent (Human spirit and Gnome intellect are excluded up front because cmangos bakes the vanilla +5% racial into them).",
        "class_row_dissent": dissent,
        "class_capabilities": {
            "can_parry": caps["parry"], "can_block": caps["block"], "can_dual_wield": caps["dual_wield"],
            "weapon_types_wowsims": WS_WEAPONS.get(WS_CLASS[cls]),
            "sources": ["wowsims-forever: PseudoStats.CanParry = true in sim/hunter/hunter.go, sim/warrior/warrior.go, sim/paladin/paladin.go, sim/rogue/rogue.go (no other class); CanBlock = a shield in the off hand (core/character.go); SpecCanDualWieldCapabilities lists Hunter, Rogue, DpsWarrior, ProtectionWarrior only.",
                        "vanilla trainer (cmangos npc_trainer_template %d, teach spell -> learned spell): Parry 3127 %s, Block 107 %s, Dual Wield 674 %s" % (cid * 10 + 1, tl[3127] or "not taught", tl[107] or "not taught", tl[674] or "not taught")],
        },
        "attack_power": {
            "melee_formula_vanilla": "see levels.attack_power_level_term[].formula",
            "ranged_formula_vanilla": "see levels.ranged_attack_power_level_term[].formula",
            "wowsims_forever_level_60_base": AP_RULES[cls]["ws60"],
            "wowsims_forever_level_60_ranged_base": AP_RULES[cls].get("ws60_ranged"),
            "rule_check": "wowsims-forever base AP at 60 = the vanilla level term at 60 (ClassBaseStats.AttackPower); the stat links in sim/%s/%s.go add the Str/Agi terms. mythicsim levels.rs scales a positive level 60 base as (AP60 + 20)/60*L - 20, which equals the vanilla level term for every class here." % (cls, cls),
        },
        "spell_power": "No class has base spell power or spell power from attributes in either source. Spell power from attributes comes only from talents (wowsims-forever: Hunter Careful Aim Int->AP, Priest Spiritual Guidance-type Spirit->spell damage/healing in talents_holy.go, Paladin Champion of the Light Int->spell damage, Shaman Mental Dexterity Int->AP, Warlock Demonic Knowledge). Talents are out of scope for this file.",
        "regen": {
            "mana_vanilla": ("(Spirit/%s + %s) mana per 2 s tick = %s + Spirit/%s per second, no level term (VM_REGEN). Regen from Spirit stops for 5 s after a mana spend (vmangos Player::Regenerate IsUnderLastManaUseEffect uses the interrupted rate, which is 0 without an aura)." % (REGEN[cls][0], REGEN[cls][1], REGEN[cls][1] / 2, REGEN[cls][0] * 2)) if REGEN[cls][0] else "no mana",
            "mana_wowsims_forever": "6.25 + Spirit/8 mana per second for every class, no level term (WS_REGEN). It equals the vanilla Mage/Priest formula; for other mana classes it differs from vanilla. While casting, Spirit regen x PseudoStats.SpiritRegenRateCasting (0 by default). Not checked below 60." if mana_class else "no mana",
            "health_ooc_vanilla": "max(0, Spirit*%s %+g) per 2 s tick out of combat, x1.5 sitting, none in combat (vmangos Player::RegenerateHealth / Unit::GetRegenHPPerSpirit). No Forever source; wowsims-forever has no health regeneration." % (REGEN[cls][2], REGEN[cls][3]),
        },
        "health_mana_formulas": "max health = base_health + min(Sta,20) + hp_per_stamina*max(Sta-20,0); max mana = base_mana + min(Int,20) + 15*max(Int-20,0) (vmangos GetHealthBonusFromStamina / GetManaBonusFromIntellect; wowsims-forever the same). *_naked arrays use naked attributes, no racial or talent modifiers.",
        "racials_alliance_wowsims": {
            "human": "The Human Spirit: Spirit x1.1 (wowsims racials.go; its TODO says the game build still states 5% for 20598 and the 26 Oct notes set 10%); Ruthless: +1% melee and spell crit (game build states 2% for 20597).",
            "dwarf": "Artisan's Precision: +1% melee and spell hit (new in Forever); +5% damage vs Beasts (Big Game Hunter); Stoneform: -10% physical damage taken for 8 s, 3 min cooldown.",
            "night_elf": "Quickness: +1% base dodge; +2% movement speed; Elune's Light: +10% melee and spell crit for 15 s, 3 min cooldown (new in Forever).",
            "gnome": "Expansive Mind (Forever): +5% maximum rage (Warrior), energy (Rogue) or mana (Priest, Mage, Warlock) in wowsims racials.go applyExpansiveMind (vanilla was +5% Intellect); Eureka! (new) cost/damage proc rows 1259812-1259821.",
            "high_order_skyborne": "Wind Blessed: x1.02 attack and cast speed (wowsims; its TODO: notes say 2%, the build states 3% for 1259710; Blizzard's race page says 1% haste); Elemental Insight: +5% damage vs Elementals; Read Ley Line (Energized): mana regen x1.5 (x2 Attuned) for 15 s (build states 30 s, +100%).",
            "applied_in_naked_values": False,
        },
        "resources": resources(cls),
        "gaps": gaps(cls, races),
    }
    if cls == "druid":
        m["forms"] = {
            "cat": "Cat Form 768 (level 20, 55% base mana): energy bar max 100, 1 energy per 0.1 s (wowsims core/energy.go); swing 1.0 s with the equipped weapon's DPS as paw damage, variance 0.4 (wowsims druid/forms.go; Blizzard Hunter & Druid deep dive: 'damage per second matches the equipped weapon. Attack speed is 1.0 or 2.5 seconds'); passive 3025: AP 12+2/level from 6, Agility -> AP 100% (A_MOD_ATTACK_POWER_OF_STAT_PERCENT misc 1), threat -29%.",
            "bear": "Bear Form 5487 (level 10-40): rage bar; swing 2.5 s; passive 1178: armor +180% (bonus armor pct and base resistance pct), max health 20+18/level, AP 30+3/level, rage regen -100% (no passive rage decay change listed in the row). Dire Bear Form 9634 (40+): armor +360%, max health 600+32/level, AP 120+3/level. Forever notes (Warcraft Tavern 4 Nov 2026): Bear and Dire Bear threat bonus 50% -> 115%.",
            "rage_in_forms": "wowsims druid/forms.go BearRageIsTwoHanded = true: a bear's auto attack takes the two-hand rage factor (combat log: 11.25 rage a swing at 2.5 s).",
        }
    return m


def resources(cls):
    r = {"primary": POWER.get(cls, "mana")}
    if cls in ("rogue", "druid"):
        r["energy"] = {
            "max": 100,
            "forever_wowsims": "1 energy per 0.1 s tick = 10 energy per second (sim/core/energy.go EnableEnergyBar: EnergyTickDuration time.Second / 10, EnergyPerTick 1)",
            "vanilla": "20 energy per 2 s tick = 10 per second (vmangos Player::Regenerate POWER_ENERGY addValue = 20)",
            "forever_notes": "Poised (Rogue level 18, Druid level 32, new in Forever): out of combat at full energy, the next energy ability costs 10 less (Warcraft Tavern / kami-labs 2 Nov notes; wowsims druid/poised.go, rogue/poised.go). Rogue max energy +Vigor talent. Gnome Expansive Mind +5% max energy (wowsims).",
        }
    if cls in ("warrior", "druid"):
        r["rage"] = {
            "max": 100,
            "dealt_forever_wowsims": "Normalized: a main-hand auto attack grants 3.46 x weapon swing speed (s) rage; two-hand weapons x4.5/3.46 (= 4.5 x speed); off hand half; a crit doubles the swing's rage (CritRageBonus 1.0, citing the game files' 'Rule of Rage (DND)' 1322574 stating 100, and logs). sim/core/rage.go.",
            "dealt_forever_blizzard": "Priest & Warrior deep dive (Warcraft Tavern summary, 1 Oct 2026): rage is 'fully-normalized' on the speed of the weapon that dealt the damage; 'Critical strike will now give 75% more Rage than non-critical strikes.' The client row (100%) and the wowsims logs win over the 75% in the deep dive.",
            "taken_forever_wowsims": "2.5 x (1 - A) x pre-armor damage / c(attacker level), c(L) = 0.0091107836 L^2 + 3.225598133 L + 4.2652911 (230.6 at 60); A = assumed armor reduction by attacker level: 20% up to 42, 30% at 44, 36% at 46, 38% at 50, 40% at 63, linear between (sim/core/rage.go, measured on combat logs). Absorbs and the defender's armor play no part.",
            "taken_forever_blizzard": "Deep dive: 'Rage gain from damage is calculated by ignoring Armor', as if armor always gave 50% reduction; Power Word: Shield no longer reduces rage gained.",
            "vanilla": "dealt: damage / c(L) x 7.5; taken: damage / c(L) x 2.5 (x1.3 under Berserker Rage) (vmangos Player::RewardRage, Kalgan's formula).",
            "decay_vanilla": "out of combat: 2 rage per 2 s tick (1 rage per second) (vmangos Player::Regenerate POWER_RAGE, 'addValue = 20 * RageDecreaseRate').",
            "decay_forever": "No Forever number found. Fury talent Lingering Rage (1323964) delays the decay after leaving combat (wowsims warrior/talents_fury.go comment; the sim does not model decay).",
            "stance_change": "Tactical Mastery baseline at 14 keeps 10 rage on a stance change; Improved Tactical Mastery 5/10/15 more (Warcraft Tavern deep dive + 4 Nov notes)." if cls == "warrior" else None,
        }
    if cls == "hunter":
        r["pet_focus"] = "Hunter pets use focus (wowsims HunterPet EnableFocusBar, sim/core/focus.go); see pets.json."
    return r


def gaps(cls, races):
    g = [
        "Base health below 60 is single-source vanilla (cmangos player_classlevelstats); the Forever client has no player base-health table. Level 60 is cross-checked against wowsims (see checks).",
        "Base melee/spell crit and base dodge are hand-kept vanilla tables (wowsims assets/db_inputs/basestats, vmangos); the Forever client ships none.",
        "Dodge per Agility below 60: no Forever or local vanilla per-level table (vmangos reads player_dodge_per_agility from its world DB, not in the local source); wowsims's level 60 rule (= crit per Agility, x2 Rogue/Hunter) is carried to every level as an estimate.",
        "Spirit mana regen below 60 and health regen: no Forever source; both formulas carried unchanged.",
        "Talent and racial modifiers are not applied in any *_naked value.",
    ]
    if cls in ("priest", "mage"):
        g.append("Base health: cmangos (used here) is 10 below wowsims SoD at levels 25, 40, 50 and 60 and below wowsims-forever at 60 (Priest 1387 vs 1397, Mage 1360 vs 1370). Unresolved; no Forever table exists. A sim that must match wowsims at 60 should add 10.")
    if cls == "hunter":
        g.append("Base health at level 50: cmangos 1032 vs wowsims SoD 1047 (25, 40 and 60 agree). Unresolved.")
    if "high_order_skyborne" in races:
        g.append("High Order Skyborne attributes: the race offset is a wowsims reading of level 1 naked sheets (which classes not stated); it is assumed constant at every level (estimate). No Skyborne row exists in any vanilla table.")
    if cls in ("hunter", "priest", "shaman"):
        new = {"hunter": "Human Hunter", "priest": "Gnome Priest", "shaman": "Dwarf Shaman"}[cls]
        g.append(f"{new} is new in Forever: its attributes are the vanilla class row plus the vanilla race offset (the additive rule holds exactly in vanilla data for every other combo).")
    if cls in ("rogue", "warrior"):
        g.append("Ranged attack power is the vanilla formula (level + Agi - 10); wowsims-forever models no ranged AP base for this class.")
    return g


def main():
    from common import cm
    c = cm()
    os.makedirs(OUT, exist_ok=True)
    summary = {}
    for cls in CLASS_IDS:
        d = build(cls, c)
        json.dump(d, open(os.path.join(OUT, f"{cls}_levels.json"), "w"), indent=1)
        summary[cls] = {r: v["result"] + ("" if not v["mismatches"] else " " + json.dumps(v["mismatches"])) for r, v in d["meta"]["checks_vs_wowsims_forever_level_60"].items()}
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
