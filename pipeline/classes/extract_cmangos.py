"""Pull the vanilla tables the class generators read out of the cmangos classic-db dump.

Input:  ext/cmangos-classic-db/Full_DB/ClassicDB_1_12_1_z2815.sql.gz (decompressed to work/classes/full_db.sql)
Output: work/classes/cm_tables.json  {table: {"cols": [...], "rows": [[...], ...]}}
"""
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "levels"))
from common import P, WORK, CM_JSON  # noqa: E402
from sqlvals import parse_values  # noqa: E402

GZ = P("ext/cmangos-classic-db/Full_DB/ClassicDB_1_12_1_z2815.sql.gz")
SQL = os.path.join(WORK, "full_db.sql")

TABLES = ["spell_template", "npc_trainer", "npc_trainer_template", "pet_levelstats", "pet_familystats",
          "creature_template", "creature_template_spells", "spell_threat", "spell_chain", "spell_bonus_data",
          "petcreateinfo_spell", "playercreateinfo_spell", "playercreateinfo_skills", "quest_template"]

SPELL_COLS = ["Id", "School", "Category", "Mechanic", "Attributes", "Stances", "CastingTimeIndex", "RecoveryTime",
              "CategoryRecoveryTime", "ProcFlags", "ProcChance", "ProcCharges", "MaxLevel", "BaseLevel", "SpellLevel",
              "DurationIndex", "PowerType", "ManaCost", "ManaCostPerlevel", "ManaPerSecond", "RangeIndex",
              "Effect1", "Effect2", "Effect3", "EffectDieSides1", "EffectDieSides2", "EffectDieSides3",
              "EffectBaseDice1", "EffectBaseDice2", "EffectBaseDice3",
              "EffectRealPointsPerLevel1", "EffectRealPointsPerLevel2", "EffectRealPointsPerLevel3",
              "EffectBasePoints1", "EffectBasePoints2", "EffectBasePoints3",
              "EffectApplyAuraName1", "EffectApplyAuraName2", "EffectApplyAuraName3",
              "EffectAmplitude1", "EffectAmplitude2", "EffectAmplitude3",
              "EffectMiscValue1", "EffectMiscValue2", "EffectMiscValue3",
              "EffectTriggerSpell1", "EffectTriggerSpell2", "EffectTriggerSpell3",
              "SpellName", "Rank1", "ManaCostPercentage", "SpellFamilyName", "SpellFamilyFlags", "DmgClass"]


def columns(sql, table):
    m = re.search(r"CREATE TABLE `%s` \((.*?)\n\) ENGINE" % table, sql, re.S)
    return re.findall(r"^\s+`(\w+)`", m.group(1), re.M)


def main():
    if not os.path.exists(SQL):
        with gzip.open(GZ, "rt", encoding="utf-8", errors="replace") as f, open(SQL, "w") as o:
            o.write(f.read())
    sql = open(SQL, encoding="utf-8", errors="replace").read()
    out = {}
    for t in TABLES:
        cols = columns(sql, t)
        rows = []
        for m in re.finditer(r"^INSERT INTO `%s`(?: \([^)]*\))? VALUES\s*(.*?);\s*$" % t, sql, re.M | re.S):
            rows.extend(parse_values(m.group(1)))
        if t == "spell_template":
            idx = [cols.index(c) for c in SPELL_COLS]
            rows = [[r[i] for i in idx] for r in rows]
            cols = SPELL_COLS
        if t == "creature_template":
            keep = ["Entry", "Name", "SubName", "MinLevel", "MaxLevel", "Family", "CreatureType", "UnitClass", "Rank",
                    "HealthMultiplier", "PowerMultiplier", "DamageMultiplier", "ArmorMultiplier", "MinLevelHealth",
                    "MaxLevelHealth", "MinLevelMana", "MaxLevelMana", "MinMeleeDmg", "MaxMeleeDmg", "Armor",
                    "MeleeAttackPower", "MeleeBaseAttackTime", "PetSpellDataId", "SpellList", "NpcFlags", "TrainerType",
                    "TrainerClass", "TrainerTemplateId", "Faction"]
            idx = [cols.index(c) for c in keep]
            rows = [[r[i] for i in idx] for r in rows]
            cols = keep
        if t == "quest_template":
            keep = ["entry", "MinLevel", "QuestLevel", "RequiredClasses", "RequiredRaces", "Title", "RewSpell", "RewSpellCast"]
            idx = [cols.index(c) for c in keep]
            rows = [[r[i] for i in idx] for r in rows if r[cols.index("RewSpell")] or r[cols.index("RewSpellCast")]]
            cols = keep
        out[t] = {"cols": cols, "rows": rows}
        print(t, len(rows))
    json.dump(out, open(CM_JSON, "w"))


if __name__ == "__main__":
    main()
