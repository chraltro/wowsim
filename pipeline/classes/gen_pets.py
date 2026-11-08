"""Hunter pets and Warlock demons for WoW Forever, levels 1-60: wowsim/data/classes/pets.json.

Forever model: wowsims-forever sim/hunter/pets.go, pet_families_auto_gen.go, sim/warlock/pets.go (read as
data), the client ExpectedStat table (wago 70862) the model is built on, and the client spell rows.
Vanilla reference: cmangos pet_levelstats / pet_familystats / creature_template / petcreateinfo_spell.
"""
import csv
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, P, WS_REPO, E, cm, rnd, spells  # noqa: E402
import families as FAM  # noqa: E402
import gen_class_ranks as GR  # noqa: E402

S = spells()
CM = cm()
ES = {int(r['Lvl']): r for r in csv.DictReader(open(P("ext/wago/ExpectedStat_70862.csv"))) if r['ContentSetID'] == '0'}
PL = {}
for r in CM["pet_levelstats"]["rows"]:
    PL.setdefault(r[0], {})[r[1]] = dict(zip(CM["pet_levelstats"]["cols"], r))
CT = {r[0]: dict(zip(CM["creature_template"]["cols"], r)) for r in CM["creature_template"]["rows"]}

SRC = {
    "ES": "Forever client DB2 ExpectedStat (ContentSetID 0), build 1.60.1.70862, wago.tools CSV (ext/wago/ExpectedStat_70862.csv)",
    "WS_HPET": "wowsims-forever sim/hunter/pets.go: a tamed pet's own health and armor are the creature values for its level (ExpectedStat), its own attack power is 30% of the creature dps as attack power (x14), i.e. floor(4.2 x creature dps): 'on the sheets of a level 11 Carrion Bird, a level 17 Cat and a level 30 pet' 36, 61, 103. Swing 2.0 s, average (creature dps - AP/14) x 2, +-20%. Happiness x1.25 damage.",
    "WS_DEMON": "wowsims-forever sim/warlock/pets.go petModels: health and armor are fixed shares of the creature values for the demon's level ('The shares are read at levels 20 and 30 (the Voidwalker's at 30 only), not yet at 60'); attributes, mana and conversions are level 60 values from 'the team's pet model sheet'.",
    "CM_PET": "cmangos classic-db pet_levelstats (vanilla 1.12): creature_entry 1 = hunter pets, 416 Imp, 1860 Voidwalker, 1863 Succubus, 417 Felhunter",
    "CM_FAM": "cmangos classic-db pet_familystats. Column order caution: the table's columns are named (healthModifier, damageModifier, armorModifier), but the values match the vanilla family modifiers as (health, armor, damage) (e.g. Cat 0.98/1.00/1.10, Bear 1.08/1.05/0.91, Boar 1.04/1.09/0.90); read here as health, armor, damage.",
}

FAMILY_IDS = {1: "Wolf", 2: "Cat", 3: "Spider", 4: "Bear", 5: "Boar", 6: "Crocilisk", 7: "Carrion Bird", 8: "Crab",
              9: "Gorilla", 11: "Raptor", 12: "Tallstrider", 20: "Scorpid", 21: "Turtle", 24: "Bat", 25: "Hyena",
              26: "Owl (Bird of Prey)", 27: "Wind Serpent"}


def es(L, k):
    return float(ES[L][k])


def hunter_families():
    src = open(os.path.join(WS_REPO, "sim/hunter/pet_families_auto_gen.go")).read()
    out = {}
    for m in re.finditer(r'"(\w+)":\s+\{Name: "([^"]+)", Passive: spelldata\.Ranked\((\d+)\), Abilities: \[\]spelldata\.Ladder\{([^}]*)\}\}', src):
        key, name, passive, abil = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        r = S[str(passive)]
        mods = {}
        for e in r["Effects"]:
            a = GR.nm(e.get("Aura"))
            v = e.get("BasePoints", 0) or 0
            if a == "A_MOD_DAMAGE_PERCENT_DONE":
                mods["damage_pct"] = v
            elif a == "A_MOD_BASE_RESISTANCE_PCT":
                mods["armor_pct"] = v
            elif a == "A_MOD_INCREASE_HEALTH_PERCENT":
                mods["health_pct"] = v
        out[key] = {"name": name, "tamed_pet_passive": passive, "modifiers": mods, "status": "forever",
                    "source": f"client spell {passive} 'Tamed Pet Passive (DND)' effects 0-2 (wowsims pet_families_auto_gen.go)",
                    "abilities_pet_side_ladders": [x.strip().replace("spellData.", "") for x in abil.split(",") if x.strip()]}
    famstats = {r[0]: r for r in CM["pet_familystats"]["rows"]}
    for key, f in out.items():
        for fid, fname in FAMILY_IDS.items():
            if fname.split(" (")[0].replace(" ", "").lower() == f["name"].replace(" ", "").lower() or (fid == 26 and key == "BirdOfPrey"):
                r = famstats.get(fid)
                if r:
                    f["vanilla_cmangos_pet_familystats"] = {"family_id": fid, "health": r[1], "armor": r[2], "damage": r[3], "source": "CM_FAM"}
    out["Wolf"]["note"] = out["Fox"]["note"] = "wowsims gives Fox and Wolf the same Tamed Pet Passive row (17223); Fox is new in Forever."
    return out


def hunter_levels():
    rows = []
    for L in range(1, 61):
        dps = es(L, "CreatureAutoAttackDps")
        ap = math.floor(4.2 * dps)
        avg = (dps - (0.3 * 14 * dps) / 14) * 2
        st = "forever" if L in (11, 17, 30) else "estimate"
        v = PL[1].get(L, {})
        rows.append({
            "level": L,
            "health": E(L, int(ES[L]["CreatureHealth"]), "estimate", "ES via WS_HPET",
                        note="wowsims TODO: one reading only (550 health with Great Stamina 2 at 35 owner Stamina); creature health kept"),
            "armor": E(L, int(ES[L]["CreatureArmor"]), "estimate", "ES via WS_HPET"),
            "attack_power": E(L, ap, st, "floor(4.2 x ES creature dps) (WS_HPET)", creature_dps=rnd(dps, 4)),
            "swing": E(L, {"speed_s": 2.0, "average": rnd(avg, 3), "min": rnd(avg * 0.8, 3), "max": rnd(avg * 1.2, 3)}, "estimate",
                       "WS_HPET (creature dps - AP/14) x 2 +-20%, before AP, happiness and family damage"),
            "vanilla_cmangos": E(L, {k: v.get(k) for k in ("hp", "armor", "str", "agi", "sta", "inte", "spi")}, "vanilla", "CM_PET"),
        })
    return rows


DEMONS = {  # wowsims petModels, Imp / Voidwalker / Succubus / Felhunter
    "imp": {"entry": 416, "health_share": 0.359, "armor_share": 0.325, "attrs_60": dict(Str=122, Agi=35, Sta=86, Int=264, Spi=260),
            "mana_60": 576, "health_per_stamina": 0, "mana_per_intellect": 5, "ap_per_strength": 2, "mp5_per_owner_intellect": 0.30,
            "melee": None, "damage_mod": 1, "summon": "SummonImp",
            "abilities": ["Firebolt", "BloodPact", "FireShield", "PhaseShift"]},
    "voidwalker": {"entry": 1860, "health_share": 1.400, "armor_share": 1.352, "attrs_60": dict(Str=129, Agi=85, Sta=234, Int=70, Spi=150),
                   "mana_60": 1066, "health_per_stamina": 0, "mana_per_intellect": 11.5, "ap_per_strength": 0, "ap_60": 186,
                   "mp5_per_owner_intellect": 0.10, "melee": {"avg_share_of_creature_dps": 0.494, "spread": 0.264, "speed_s": 2.0},
                   "damage_mod": 0.5, "summon": "SummonVoidwalker", "abilities": ["Torment", "Sacrifice", "Suffering", "ConsumeShadows"]},
    "succubus": {"entry": 1863, "health_share": 0.699, "armor_share": 0.630, "attrs_60": dict(Str=129, Agi=85, Sta=234, Int=70, Spi=150),
                 "mana_60": 1066, "health_per_stamina": 0, "mana_per_intellect": 11.5, "ap_per_strength": 0, "ap_60": 186,
                 "mp5_per_owner_intellect": 0.10, "melee": {"avg_share_of_creature_dps": 0.698, "spread": 0.215, "speed_s": 2.0},
                 "damage_mod": 1, "summon": "SummonSuccubus", "abilities": ["LashOfPain", "Seduction", "SoothingKiss", "LesserInvisibility"]},
    "felhunter": {"entry": 417, "health_share": 0, "armor_share": 0, "attrs_60": dict(Str=129, Agi=85, Sta=234, Int=70, Spi=150),
                  "mana_60": 1066, "health_per_stamina": 9.5, "mana_per_intellect": 11.55, "ap_per_strength": 2,
                  "mp5_per_owner_intellect": 0.10, "melee": {"min_60": 70, "max_60": 97, "speed_s": 2.0}, "damage_mod": 0.8,
                  "summon": "SummonFelhunter", "abilities": ["DevourMagic", "TaintedBlood", "SpellLock", "Paranoia"]},
}


def demon_levels(d):
    rows = []
    v = PL.get(d["entry"], {})
    for L in range(1, 61):
        ch, ca, dps = int(ES[L]["CreatureHealth"]), int(ES[L]["CreatureArmor"]), es(L, "CreatureAutoAttackDps")
        st = "forever" if L in (20, 30) and d["health_share"] else "estimate"
        row = {"level": L}
        if d["health_share"]:
            row["own_health"] = E(L, round(d["health_share"] * ch), st, f"{d['health_share']} x ES creature health (WS_DEMON)")
            row["own_armor"] = E(L, round(d["armor_share"] * ca), st, f"{d['armor_share']} x ES creature armor (WS_DEMON)")
        else:
            row["own_health"] = E(L, None, "estimate", "WS_DEMON: Felhunter health = 9.5 per point of its Stamina; its Stamina below 60 is not in any Forever source (vanilla Stamina in vanilla_cmangos)")
            row["own_armor"] = E(L, 0, "estimate", "WS_DEMON: 'the Felhunter has no armor of its own'")
        if d["melee"] and "avg_share_of_creature_dps" in d["melee"]:
            avg = d["melee"]["avg_share_of_creature_dps"] * dps * d["melee"]["speed_s"]
            sp = d["melee"]["spread"]
            row["melee_swing"] = E(L, {"speed_s": 2.0, "average": rnd(avg, 3), "min": rnd(avg * (1 - sp), 3), "max": rnd(avg * (1 + sp), 3),
                                       "damage_multiplier": d["damage_mod"]}, "estimate", "WS_DEMON share x ES creature dps x 2 s")
        if L == 60:
            row["level_60_model"] = E(L, {"attributes": d["attrs_60"], "base_mana": d["mana_60"], "attack_power": d.get("ap_60")}, "forever",
                                      "WS_DEMON (wowsims level 60 pet model sheet)")
        vv = v.get(L, {})
        row["vanilla_cmangos"] = E(L, {k: vv.get(k) for k in ("hp", "mana", "armor", "str", "agi", "sta", "inte", "spi")}, "vanilla", "CM_PET")
        rows.append(row)
    return rows


def pet_trainer_map():
    """vanilla hunter pet trainers (creature_template TrainerType 3): learned pet spell -> reqlevel, cost."""
    trainers = {e for e, c in CT.items() if c["TrainerType"] == 3}
    out = {}
    for r in CM["npc_trainer"]["rows"]:
        if r[0] not in trainers:
            continue
        for learned in GR.TEACH.get(r[1], {r[1]}):
            o = out.setdefault(learned, {"reqlevel": set(), "cost_copper": set()})
            o["reqlevel"].add(r[5])
            o["cost_copper"].add(r[2])
    return {k: {kk: sorted(vv) for kk, vv in v.items()} for k, v in out.items()}


def annotate(fams, trainer, starting, kind):
    for key, f in fams.items():
        for rk in f["ranks"]:
            ids = {rk["id"]} | set(GR.TEACH.get(rk["id"], set()))
            hit = next((trainer[i] for i in ids if i in trainer), None)
            if hit:
                rk["learned_from"]["source"] = "vanilla pet trainer"
                rk["learned_from"]["vanilla_pet_trainer"] = hit
            if rk["id"] in starting:
                rk["learned_from"]["source"] = "known on summon (vanilla petcreateinfo_spell)"
        if kind == "hunter":
            f.setdefault("notes", []).append("Vanilla rule: a hunter pet learns abilities a pet trainer does not teach from tamed beasts that know them (Beast Training); hunter-side ladders are the teaching spells, '...Triggered' ladders the pet's own spell.")
        else:
            f.setdefault("notes", []).append("Vanilla: demon abilities above the starting one come from Grimoires sold by demon trainers; kami-labs (2 Nov notes): Forever training costs are reduced by what the Grimoires would cost.")


def main():
    hctx = GR.Ctx("hunter")
    wctx = GR.Ctx("warlock")
    hfam = hunter_families()
    pet_abil = {}
    for key in sorted(FAM.PET["hunter"]):
        if key in hctx.L:
            pet_abil[key] = GR.family(hctx, key)
    demon_abil = {}
    for key in sorted(FAM.PET["warlock"]):
        if key in wctx.L:
            demon_abil[key] = GR.family(wctx, key)
    starting = {sp for r in CM["petcreateinfo_spell"]["rows"] for sp in r[1:] if sp}
    annotate(pet_abil, pet_trainer_map(), starting, "hunter")
    annotate(demon_abil, {}, starting, "warlock")
    out = {
        "meta": {
            "title": "WoW Forever Hunter pets and Warlock demons, levels 1-60",
            "generated": "2026-11-08",
            "status_legend": {"forever": "Forever client data, or a wowsims-forever value read in the Forever game", "vanilla": "Classic/vanilla fallback", "estimate": "derived or interpolated"},
            "sources": SRC,
            "layout": "hunter.levels[] / warlock.<demon>.levels[] indexed by level-1; entries {level, value, status, source}. Ability families use the <class>_ranks.json rank schema.",
            "forever_changes": [
                "Hunter pets: 'Pets now get increased stats based on their Hunter's gear' and 'can no longer receive player stat buffs'; every family can learn Bite or Claw and Dive or Dash plus one unique ability; Foxes are new (Trickster's Dance) (Blizzard Hunter & Druid deep dive).",
                "Hunter pets keep their attack speed passives when untrained (kami-labs, 2 Nov notes).",
                "Warlock demons scale from the warlock's stats (Rogue & Warlock deep dive, Warcraft Tavern 7 Oct); 2 Nov notes: demons get 2 health per point of the warlock's Stamina (was 7.5).",
                "Warlock: training costs reduced by what the pets' Grimoires would cost (kami-labs 2 Nov), i.e. demon abilities still come from Grimoires.",
            ],
            "gaps": [
                "Hunter pet health below and at 60: wowsims keeps the creature health (one in-game reading); the share of the owner's Stamina is unread (wowsims uses 2 per point, TODO).",
                "Hunter pet attack power is measured at levels 11, 17 and 30 only; other levels follow the same rule (estimate).",
                "Demon health/armor shares are read at levels 20 and 30 (Voidwalker at 30 only); other levels follow the shares (estimate). Demon attributes exist only at 60 in Forever data; per-level attributes are vanilla (cmangos).",
                "Felhunter: no Forever health share; its health is 9.5 per point of its own Stamina, known only at 60.",
                "Felguard (Demonology) and Incubus: not modelled by wowsims; no Forever numbers here.",
                "Pet crit, hit and spell power inheritance shares are wowsims's (partly unverified, see the TODOs quoted).",
            ],
        },
        "hunter": {
            "model": {
                "base_stats_per_level": "levels[] (health and armor = ExpectedStat creature values for the pet's level; AP = floor(4.2 x creature dps))",
                "inheritance_from_hunter": {"health": "2 per point of the hunter's Stamina (wowsims TODO: unread)", "armor": "30% of the hunter's armor",
                                            "attack_power": "10% of the higher of the hunter's melee and ranged AP", "crit": "the hunter's higher of melee/ranged crit (minus 0.04% per weapon skill point under max)",
                                            "hit": "the hunter's ranged hit; spell hit = 17/8 of it", "expertise": "the hunter's", "when": "snapshot on summon and on any pet action, at most every 2 s",
                                            "source": "wowsims-forever sim/hunter/pets.go makeStatInheritance ('Hunter Pet Scaling (415429) states every inherited stat without an amount')", "status": "forever (wowsims reading, partly unverified)"},
                "happiness_damage_multiplier": 1.25,
                "focus": {"max": 100, "regen": "25 per 5 s (5 per second) x Bestial Discipline (wowsims core/focus.go EnableFocusBar)"},
                "attack_speed_passives": "Faster Attack I-VII / Slower Attack II-III rows (ability_families); wowsims normalizes damage so dps is unchanged by the speed",
            },
            "levels": hunter_levels(),
            "families": hfam,
            "ability_families": pet_abil,
        },
        "warlock": {
            "inheritance_from_warlock": {
                "health": "2 per point of the warlock's Stamina (2 Nov notes; wowsims TODO: confirm on live)",
                "mp5": "per point of the warlock's Intellect: Imp 0.30, Voidwalker/Succubus 0.10 (read at level 30), Felhunter 0.10 assumed",
                "armor": "35% of the warlock's armor", "attack_power": "17% of the warlock's spell damage (better of Shadow/Fire)",
                "spell_damage": "10% of the warlock's spell damage (measured on the Sayaad)", "hit": "spell hit whole; melee hit = 8/17 of it",
                "crit": "the warlock's spell crit as melee and spell crit (wowsims TODO: not live yet)",
                "source": "wowsims-forever sim/warlock/pets.go petStatInheritance ('Warlock Pet Scaling (416189) names the stats it inherits ... but states no amounts')",
                "status": "forever (wowsims reading, partly unverified)"},
            "demons": {name: {"vanilla_creature_entry": d["entry"], "model_60": {k: v for k, v in d.items() if k not in ("entry", "abilities", "summon")},
                              "summon_family_in_warlock_ranks": d["summon"], "ability_families": d["abilities"],
                              "levels": demon_levels(d)} for name, d in DEMONS.items()},
            "ability_families": demon_abil,
        },
    }
    json.dump(out, open(os.path.join(OUT, "pets.json"), "w"), indent=1)
    print("pets: hunter families", len(hfam), "pet ability families", len(pet_abil), "demon ability families", len(demon_abil))


if __name__ == "__main__":
    main()
