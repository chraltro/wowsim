import json, re, csv, sys, statistics as st
sys.path.insert(0, '/home/claude/work/scripts')

CM = open('/home/claude/ext/cmangos_tables/inserts.sql').read()
def ins(table):
    m = re.search(r"INSERT INTO `%s` VALUES (.*);" % table, CM)
    return [tuple(map(int, t.split(','))) for t in re.findall(r"\(([\d,]+)\)", m.group(1))]
classlevel = {(r[0], r[1]): (r[2], r[3]) for r in ins('player_classlevelstats')}
levelstats = {(r[0], r[1], r[2]): r[3:] for r in ins('player_levelstats')}

ORC, TAUREN, TROLL = 2, 6, 8
OFF = {ORC: (3, -3, 2, -3, 3), TAUREN: (5, -5, 2, -5, 2), TROLL: (1, 2, 1, -4, 1)}
DWARF = (2, -4, 3, -1, -1)  # wowsims-forever sim/core/base_stats.go RaceOffsets[Dwarf]; cmangos dwarf-orc deltas agree
class_row = {}
for L in range(1, 61):
    rows = {tuple(levelstats[(race, 7, L)][i] - OFF[race][i] for i in range(5)) for race in OFF}
    assert len(rows) == 1, (L, rows)
    class_row[L] = rows.pop()

pes = {int(r['Level']): r for r in csv.DictReader(open('/home/claude/ext/wago/PlayerExpectedStat_70862.csv')) if r['ClassID'] == '7' and r['ContentSetID'] == '0'}
es = {int(r['Lvl']): r for r in csv.DictReader(open('/home/claude/ext/wago/ExpectedStat_70862.csv')) if r['ContentSetID'] == '0'}
esm = list(csv.DictReader(open('/home/claude/ext/wago/ExpectedStatMod_70862.csv')))
ac = {}
for t in re.findall(r"\((7,\d+,[\d,]+)\)", open('/home/claude/ext/ac/player_class_stats.sql').read()):
    v = tuple(map(int, t.split(','))); ac[v[1]] = v

SRC = {
  "PES": "Forever client DB2 PlayerExpectedStat (ClassID 7, ContentSetID 0), build 1.60.1.70862, wago.tools CSV fetched 2026-11-08 (/home/claude/ext/wago/PlayerExpectedStat_70862.csv). Same table wowsims-forever tools/base_stats_parser.py reads for its level 60 values.",
  "ES": "Forever client DB2 ExpectedStat (ContentSetID 0, ExpansionID -2), build 1.60.1.70862, wago.tools CSV (/home/claude/ext/wago/ExpectedStat_70862.csv). wowsims-forever takes its level 60 CreatureHealthMaxLevel 4365 / CreatureArmorMaxLevel 3566 / CreatureAutoAttackDpsMaxLevel 60.4529 from the same table.",
  "CM_CLS": "cmangos classic-db Full_DB/ClassicDB_1_12_1_z2815.sql.gz, player_classlevelstats class 7 (vanilla 1.12 base health/mana)",
  "CM_LVL": "cmangos classic-db player_levelstats class 7: the Orc, Tauren and Troll rows minus their race offsets give one identical class row at all 60 levels; same row as AzerothCore player_class_stats class 7 (azerothcore-wotlk master) at all 60 levels",
  "DWARF": "Dwarf offset Str +2, Agi -4, Sta +3, Int -1, Spi -1 (wowsims-forever sim/core/base_stats.go RaceOffsets; cmangos Dwarf-minus-Orc rows give the same offset at every level for Warrior and Hunter)",
  "WS_BASE": "wowsims-forever sim/core/base_stats_auto_gen.go / base_stats.go (hand-kept chancetomeleecritbase / chancetospellcritbase, ClassBaseDodge)",
  "VM_AP": "vmangos src/game/StatSystem.cpp Player::GetAttackPowerFromStrengthAndAgility: CLASS_SHAMAN val2 = level*2 + strength*2 - 20",
  "VM_REGEN": "vmangos src/game/Objects/Unit.cpp Unit::GetRegenMPPerSpirit: CLASS_SHAMAN (Spirit/5 + 17) per 2 s tick, no level term",
  "WS_REGEN": "wowsims-forever sim/core/mana.go: spiritRegenBase 6.25, spiritRegenPerSpirit 1/8, per second, every class, no level term",
  "CM_MOB": "cmangos classic-db creature_template: creatures with MinLevel = MaxLevel, combat types (beast, dragonkin, demon, elemental, giant, undead, humanoid, mechanical, not specified), no NPC flags, not civilian, UnitClass 1 (warrior)",
  "VANILLA_RULE": "vanilla rule (vmangos Player::GetSkillMaxForLevel = level*5)",
}

def E(L, v, status, source, **kw):
    d = {"level": L, "value": v, "status": status, "source": source}
    d.update(kw)
    return d

WS60 = {"base_mana": 1520, "str": 87, "agi": 51, "sta": 98, "int": 89, "spi": 99, "base_health": 1280}
out = {"meta": {}, "levels": {}, "mobs": {}}
lv = out["levels"]
names = ["strength", "agility", "stamina", "intellect", "spirit"]
for k in ["base_health", "base_mana", *names, "max_health_naked", "max_mana_naked", "hp_per_stamina",
          "melee_crit_pct_per_agility", "spell_crit_pct_per_intellect", "base_melee_crit_pct", "base_spell_crit_pct",
          "base_dodge_pct", "melee_crit_pct_naked", "spell_crit_pct_naked",
          "attack_power_level_term", "attack_power_naked", "weapon_skill_max",
          "spirit_regen_vanilla_per_s_naked", "spirit_regen_wowsims_per_s_naked"]:
    lv[k] = []

for L in range(1, 61):
    hp = classlevel[(7, L)][0]
    lv["base_health"].append(E(L, hp, "vanilla", "CM_CLS"))
    mana = int(pes[L]['BaseMana'])
    extra = {}
    if classlevel[(7, L)][1] != mana:
        extra["note"] = f"cmangos player_classlevelstats says {classlevel[(7, L)][1]}; AzerothCore says {ac[L][3]}"
    lv["base_mana"].append(E(L, mana, "forever", "PES", **extra))
    attrs = tuple(class_row[L][i] + DWARF[i] for i in range(5))
    for i, n in enumerate(names):
        lv[n].append(E(L, attrs[i], "vanilla", "CM_LVL+DWARF", class_row_value=class_row[L][i]))
    sta, intel, spi, strn, agi = attrs[2], attrs[3], attrs[4], attrs[0], attrs[1]
    hps = int(pes[L]['HPPerStamina'])
    lv["hp_per_stamina"].append(E(L, hps, "forever", "PES"))
    lv["max_health_naked"].append(E(L, hp + min(sta, 20) + hps * max(sta - 20, 0), "vanilla", "base_health + min(Sta,20) + hp_per_stamina*(Sta-20)"))
    lv["max_mana_naked"].append(E(L, mana + min(intel, 20) + 15 * max(intel - 20, 0), "forever", "base_mana + min(Int,20) + 15*(Int-20) (wowsims-forever mana.go: AddStat(Mana, 20-15*20) + 15 per Int)"))
    cpa = round(float(pes[L]['CritPerAgility']) * 100, 6)
    cpi = round(float(pes[L]['SpellCritPerIntellect']) * 100, 6)
    lv["melee_crit_pct_per_agility"].append(E(L, cpa, "forever", "PES", agility_per_1pct=round(100 / (cpa * 100), 2)))
    lv["spell_crit_pct_per_intellect"].append(E(L, cpi, "forever", "PES", intellect_per_1pct=round(100 / (cpi * 100), 2)))
    lv["base_melee_crit_pct"].append(E(L, 1.7, "vanilla", "WS_BASE"))
    lv["base_spell_crit_pct"].append(E(L, 2.3, "vanilla", "WS_BASE"))
    lv["base_dodge_pct"].append(E(L, 1.7, "vanilla", "WS_BASE", note="dodge per agility = melee_crit_pct_per_agility for Shaman (wowsims dodgePerAgility)"))
    lv["melee_crit_pct_naked"].append(E(L, round(1.7 + agi * cpa, 4), "forever", "1.7 + Agi * melee_crit_pct_per_agility"))
    lv["spell_crit_pct_naked"].append(E(L, round(2.3 + intel * cpi, 4), "forever", "2.3 + Int * spell_crit_pct_per_intellect"))
    lv["attack_power_level_term"].append(E(L, 2 * L - 20, "vanilla", "VM_AP", note="AP = 2*level - 20 + 2*Str (no Agility term); level 60 gives 100, wowsims-forever ClassBaseStats AttackPower 100"))
    lv["attack_power_naked"].append(E(L, 2 * L - 20 + 2 * strn, "vanilla", "VM_AP"))
    lv["weapon_skill_max"].append(E(L, 5 * L, "vanilla", "VANILLA_RULE"))
    lv["spirit_regen_vanilla_per_s_naked"].append(E(L, round(8.5 + spi / 10, 4), "vanilla", "VM_REGEN", formula="(Spirit/5 + 17)/2 per second"))
    lv["spirit_regen_wowsims_per_s_naked"].append(E(L, round(6.25 + spi / 8, 4), "estimate", "WS_REGEN", formula="6.25 + Spirit/8 per second, applied unchanged below 60"))

# checks against wowsims-forever level 60
L60 = {n: lv[n][59]["value"] for n in lv}
assert L60["base_mana"] == WS60["base_mana"] and L60["base_health"] == WS60["base_health"]
assert (L60["strength"], L60["agility"], L60["stamina"], L60["intellect"], L60["spirit"]) == (87, 51, 98, 89, 99)
assert abs(L60["melee_crit_pct_per_agility"] - 0.0508) < 1e-6 and abs(L60["spell_crit_pct_per_intellect"] - 0.0169) < 1e-6

# ---------------- mobs ----------------
cols = open('/home/claude/work/ct_cols.txt').read().split()
d = json.load(open('/home/claude/work/cmangos_parsed.json'))
ct = [dict(zip(cols, r)) for r in d['creature_template']]
def ok(c):
    return (c['MinLevel'] == c['MaxLevel'] and c['CreatureType'] in (1, 2, 3, 4, 5, 6, 7, 9, 10) and c['NpcFlags'] == 0
            and c['MinLevelHealth'] > 0 and c['MaxMeleeDmg'] > 0 and c['Civilian'] == 0 and c['UnitClass'] == 1 and 1 <= c['MinLevel'] <= 63)
mobs = [c for c in ct if ok(c)]
def mdps(c):
    return (c['MinMeleeDmg'] + c['MaxMeleeDmg']) / 2 * c['DamageMultiplier'] / (c['MeleeBaseAttackTime'] / 1000)
def ratio(c):
    e = es[c['MinLevel']]
    return c['MinLevelHealth'] / float(e['CreatureHealth']), mdps(c) / float(e['CreatureAutoAttackDps'])

def elite_ratio(L):
    Lc = min(max(L, 10), 60)
    w = [ratio(c) for c in mobs if c['Rank'] == 1 and abs(c['MinLevel'] - Lc) <= 3 and c['MinLevel'] <= 60]
    return round(st.median(x[0] for x in w), 2), round(st.median(x[1] for x in w), 2), len(w), Lc

mob_levels = []
for L in range(1, 64):
    e = es[L]
    normal = [c for c in mobs if c['Rank'] == 0 and c['MinLevel'] == L]
    hr, dr, n_el, Lc = elite_ratio(L)
    row = {
        "level": L,
        "normal": {
            "health": E(L, int(e['CreatureHealth']), "forever", "ES"),
            "auto_attack_dps": E(L, round(float(e['CreatureAutoAttackDps']), 4), "forever", "ES"),
            "armor": E(L, int(e['CreatureArmor']), "forever", "ES"),
            "spell_damage": E(L, round(float(e['CreatureSpellDamage']), 3), "forever", "ES", note="ExpectedStat.CreatureSpellDamage; how the server uses it is not checked"),
        },
        "armor_constant_attacker_level": E(L, int(e['ArmorConstant']), "forever", "ES", note="= 400 + 85*L; damage reduction = armor / (armor + constant of the ATTACKER's level)"),
        "elite": {
            "health": E(L, round(int(e['CreatureHealth']) * hr), "estimate", "ES x CM_MOB elite median ratio", multiplier=hr, sample=n_el, window_center=Lc),
            "auto_attack_dps": E(L, round(float(e['CreatureAutoAttackDps']) * dr, 2), "estimate", "ES x CM_MOB elite median ratio", multiplier=dr, sample=n_el, window_center=Lc),
            "armor": E(L, int(e['CreatureArmor']), "estimate", "ES (elite armor taken equal to normal: cmangos elites carry the same armor per level)"),
        },
    }
    if normal:
        row["vanilla_reference_normal"] = {
            "median_health": E(L, round(st.median(c['MinLevelHealth'] for c in normal)), "vanilla", "CM_MOB", sample=len(normal)),
            "median_auto_attack_dps": E(L, round(st.median(mdps(c) for c in normal), 2), "vanilla", "CM_MOB", sample=len(normal), note="weapon damage only, without the creature's MeleeAttackPower"),
        }
    mob_levels.append(row)

out["mobs"] = {
    "levels_1_to_63": mob_levels,
    "expected_stat_mod": {
        "rows": esm,
        "status": "forever", "source": "Forever client DB2 ExpectedStatMod, build 1.60.1.70862 (wago.tools)",
        "reading": "estimate: ID 1 (dps x0.73, armor x0.51) matches the vanilla mage-class creature ratio in cmangos (median dps/ES 0.73), ID 2 (dps x0.93, armor x0.81) the paladin-class ratio (0.92-0.93), ID 3 = warrior/rogue (x1). Health mods are 1 in all rows, though cmangos mage/paladin mobs carry 0.6-0.8x health. Which ID the server applies to which creature is not in client data."
    },
    "notes": [
        "ExpectedStat normal values match vanilla (cmangos) warrior-class mobs on auto attack dps (cmangos/ES ratio 0.98-1.00 at levels 7-54; 1.3 at 1-6) and on armor. Health differs: cmangos median / ES is 0.95-1.0 at levels 1-15, 0.77-0.88 at 16-45 and 0.92-0.95 at 46-57, so ES health runs up to 30% above vanilla mobs in the middle levels.",
        "Elite multipliers: median over cmangos rank-1 (elite) warrior-class creatures within +-3 levels (levels 1-9 use the level 10 window, 61-63 the level 60 window). Spread is wide (interquartile hp ratio about 2.3-4.6x, dps 1.7-4.9x at 20-49); 58-60 is dominated by dungeon/raid trash.",
        "Bosses are not covered: cmangos has under 10 rank-3 creatures at fixed levels below 58.",
        "wowsims-forever level 60 constants: CreatureHealthMaxLevel 4365, CreatureArmorMaxLevel 3566, CreatureAutoAttackDpsMaxLevel 60.45291519165039 = the level 60 rows here. A level 63 raid boss's 3731 armor (mythicsim) = ExpectedStat level 63 armor.",
        "mythicsim-forever-engine targets a levelling character at its own level to +3 (src/prepare/levels.rs target_levels); its app worker uses a dungeon boss two levels up (docs/levels.md)."
    ]
}

out["meta"] = {
    "title": "Dwarf Shaman per-level character data and mob baselines for WoW Forever, levels 1-60",
    "generated": "2026-11-08",
    "status_legend": {"forever": "Forever client data", "vanilla": "Classic/vanilla fallback", "estimate": "derived or interpolated"},
    "layout": "levels.<stat> is an array indexed by level-1 (index 0 = level 1). Every entry: {level, value, status, source}; source is a key of meta.sources or an inline formula.",
    "sources": SRC,
    "checks_vs_wowsims_forever_level_60": {"base_mana": 1520, "base_health": 1280, "str": 87, "agi": 51, "sta": 98, "int": 89, "spi": 99,
        "crit_per_agi_pct": 0.0508, "spell_crit_per_int_pct": 0.0169, "result": "all match"},
    "dwarf_shaman_note": "Dwarf Shaman did not exist in vanilla. Attributes are the vanilla Shaman class row plus the Dwarf race offset. That additive rule holds exactly in vanilla data (three Shaman races give one class row at all 60 levels), and its level 60 result equals wowsims-forever's Dwarf Shaman.",
    "base_mana_note": "The Forever client table (PES) differs from cmangos at levels 1, 22, 26, 30 and 52 (55 vs 53, 421 vs 456, 535 vs 579, 665 vs 718, 1323 vs 1313). AzerothCore agrees with PES at every level, so the cmangos rows are errors.",
    "base_health_note": "Base health is vanilla (cmangos). The Forever client has no player base-health column (PlayerExpectedStat carries BaseMana, HPPerStamina, the two crit slopes and one unnamed column, Field_1_60_1_69876_006, identical for every class: 1 at level 1, 68 at 20, 287 at 60; not identified). AzerothCore (WotLK) values are higher at every level (1423 at 60) and do not apply. mythicsim-forever-engine solves base health from the character sheet below 60 rather than from a table.",
    "crit_note": "Crit per Agility and per Intellect by level are Forever client values (PlayerExpectedStat). Forever retuned crit-per-agility for 7 of 9 classes (wowsims base_stats_parser.py). The old gtChanceToMeleeCrit / gtChanceToSpellCrit tables in wowsims/sod assets give 31.25 Agi and 57.1 Int per 1% at 60 for Shaman, which is wrong for Forever. vmangos uses the old mangos spell formula 3.54 + Int/(11.51 + 0.8*L), flagged 'MUST BE CHECKED' in its source. Base crit (1.7% melee, 2.3% spell) has no level term in any source; the Forever client ships no base-crit table.",
    "spirit_regen_note": "Neither formula has a level term. vanilla (vmangos): Shaman (Spirit/5 + 17) per 2 s = 8.5 + Spirit/10 per second. wowsims-forever: 6.25 + Spirit/8 per second for every class, no source cited in code. The two cross at Spirit 90. Scaling the wowsims formula below 60 = using it unchanged (estimate). With naked Dwarf spirit (21 at level 1, 99 at 60): wowsims 8.88 to 18.63 mana/s, vanilla 10.6 to 18.4 mana/s.",
    "attack_power_note": "Shaman melee AP = 2*level - 20 + 2*Str (vmangos); wowsims-forever adds 2 AP per Str on a level 60 base of 100 (= 2*60 - 20). mythicsim levels.rs scales the base as (AP60 + 20)/60 * L - 20 = 2L - 20.",
    "health_mana_formulas": "max health = base_health + min(Sta,20) + 10*max(Sta-20,0); max mana = base_mana + min(Int,20) + 15*max(Int-20,0). The *_naked arrays use naked Dwarf attributes.",
    "gaps": [
        "Base health below 60 is single-source vanilla (cmangos); only level 60 is confirmed for Forever (wowsims 1280).",
        "Base crit and base dodge come from hand-kept vanilla tables (no Forever source).",
        "Spirit regen below 60: no Forever source; wowsims formula carried down unchanged.",
        "Elite mob health/dps are estimates from vanilla emulator data; bosses not covered.",
        "Talent and racial modifiers are not applied in any *_naked value."
    ]
}

json.dump(out, open(sys.argv[1], 'w'), indent=1)
print("ok")
