"""Build /home/claude/data/shaman_forever.json from the wowsims/forever spell store.

Usage: python3 -I build_json.py <wowsims repo root> <output json>
"""
import json
import re
import sys

ROOT = sys.argv[1]
OUT = sys.argv[2]
STORE = ROOT + "/sim/core/spelldata/spells_auto_gen.go"
STORE_REL = "data/repos/wowsims-forever/sim/core/spelldata/spells_auto_gen.go"
LEVEL = 60

# ---------- parse the store ----------
blocks, lines_of = {}, {}
cur, buf = None, []
with open(STORE) as f:
    for n, line in enumerate(f, 1):
        m = re.match(r"^\t\{ID: (\d+), ", line)
        if m:
            if cur is not None:
                blocks[cur] = buf
            cur, buf = int(m.group(1)), [line]
            lines_of[cur] = n
        elif cur is not None:
            buf.append(line)
if cur is not None:
    blocks[cur] = buf

NUM = r"(-?[0-9.]+(?:e-?\d+)?)"


def field(text, name, default=None, cast=float):
    m = re.search(r"\b" + name + r": " + NUM, text)
    return cast(m.group(1)) if m else default


def parse(sid):
    b = blocks[sid]
    head = b[0]
    spell = {
        "id": sid,
        "name": re.search(r'Name: "([^"]*)"', head).group(1),
        "rank": (re.search(r'Rank: "([^"]*)"', head) or [None, None])[1],
        "spell_level": field(head, "SpellLevel", 0, int),
        "base_level": field(head, "BaseLevel", 0, int),
        "max_level": field(head, "MaxLevel", 0, int),
        "cast_ms": field(head, "CastTimeMs", 0, int),
        "duration_ms": field(head, "DurationMs", 0, int),
        "cooldown_ms": field(head, "CooldownMs", 0, int),
        "category_cooldown_ms": field(head, "CategoryCooldownMs", 0, int),
        "gcd_ms": field(head, "GCDMs", 0, int),
        "icd_ms": field(head, "ICDMs", 0, int),
        "proc_chance": field(head, "ProcChance", None, int),
        "proc_charges": field(head, "ProcCharges", None, int),
        "line": lines_of[sid],
        "effects": [],
    }
    txt = "".join(b)
    pw = re.search(r"Powers: \[\]Power\{\{([^}]*)\}", txt)
    spell["mana"] = None
    spell["mana_pct_base"] = None
    if pw:
        c = re.search(r"\bCost: (\d+)", pw.group(1))
        cp = re.search(r"CostPct: ([0-9.]+)", pw.group(1))
        typ = re.search(r"Type: (\d+)", pw.group(1))
        if typ is None or typ.group(1) == "0":
            spell["mana"] = int(c.group(1)) if c else None
            spell["mana_pct_base"] = float(cp.group(1)) if cp else None
    for line in b[1:]:
        if "SpellID:" not in line:
            continue
        e = {
            "index": field(line, "Index", 0, int),
            "type": (re.search(r"Type: dbcenums\.(\w+)", line) or [None, None])[1],
            "aura": (re.search(r"Aura: dbcenums\.(\w+)", line) or [None, None])[1],
            "base_points": field(line, "BasePoints", 0.0),
            "ppl": field(line, "PPL", 0.0),
            "variance": field(line, "Variance", 0.0),
            "sp_coef": field(line, "SPCoef", 0.0),
            "ap_coef": field(line, "APCoef", 0.0),
            "period_ms": field(line, "PeriodMs", 0, int),
            "chain_targets": field(line, "ChainTargets", 0, int),
            "chain_amp": field(line, "ChainAmp", 1.0),
            "base_level": field(line, "BaseLevel", 0, int),
            "max_level": field(line, "MaxLevel", 0, int),
        }
        spell["effects"].append(e)
    return spell


def at60(e):
    lvl = LEVEL
    if e["max_level"] and e["max_level"] < lvl:
        lvl = e["max_level"]
    gain = max(0, lvl - e["base_level"]) * e["ppl"]
    return e["base_points"] + gain


def rnd(x, n=3):
    return None if x is None else round(x, n)


def src(sid):
    return f"{STORE_REL}:{lines_of[sid]} (spell {sid})"


TOOLTIP = "https://wowforevertalents.com/abilities/shaman/ (client 1.60.1.70862 + 7 Nov 2026 hotfix cache)"
NOTES_NOV2 = "https://us.forums.blizzard.com/en/wow/t/wow-forever-beta-development-notes/2360696 (2 Nov 2026 notes, posted 3 Nov)"
MYTHIC_HOTFIX = "data/repos/mythicsim-forever-engine/src/prepare/hotfix_113554.rs"


def direct(spell, eff_idx, kind):
    e = spell["effects"][eff_idx]
    mean = at60(e)
    v = e["variance"]
    out = {
        "mean_at_60": rnd(mean, 2),
        "min": round(mean * (1 - v / 2)) if v else round(mean),
        "max": round(mean * (1 + v / 2)) if v else round(mean),
        "variance_full_width": rnd(v, 5),
        "variance_rule": "game rolls the whole amount incl. bonus: (mean + coef*bonus) * U(1-v/2, 1+v/2) (wowsims core/spell_result.go CalcDamage/CalcHealing)" if v else None,
        "base_points": e["base_points"],
        "points_per_level": rnd(e["ppl"], 3),
        "effect_level_range": [e["base_level"], e["max_level"]],
        "coefficient": rnd(e["sp_coef"], 4),
        "coefficient_applies_to": kind,
    }
    return out


def periodic(spell, eff_idx, kind):
    e = spell["effects"][eff_idx]
    tick = at60(e)
    period = e["period_ms"] / 1000
    dur = spell["duration_ms"] / 1000 if spell["duration_ms"] > 0 else None
    ticks = int(round(dur / period)) if dur else None
    return {
        "per_tick_at_60": rnd(tick, 2),
        "tick_period_s": period,
        "duration_s": dur,
        "ticks": ticks,
        "total": rnd(tick * ticks, 1) if ticks else None,
        "coefficient_per_tick": rnd(e["sp_coef"], 4),
        "coefficient_total": rnd(e["sp_coef"] * ticks, 4) if ticks else None,
        "coefficient_applies_to": kind,
    }


def common(spell):
    cd = max(spell["cooldown_ms"], spell["category_cooldown_ms"]) / 1000 or None
    return {
        "spell_id": spell["id"],
        "rank": spell["rank"],
        "learned_level": spell["spell_level"],
        "cast_time_s": spell["cast_ms"] / 1000 if spell["cast_ms"] else 0.0,
        "mana": spell["mana"],
        "mana_pct_of_base_mana": spell["mana_pct_base"],
        "cooldown_s": cd,
        "duration_s": spell["duration_ms"] / 1000 if spell["duration_ms"] > 0 else None,
        "gcd_s": spell["gcd_ms"] / 1000 if spell["gcd_ms"] else None,
    }


S = {}

# ---------------- healing ----------------
hw9, hw10 = parse(10396), parse(25357)
S["Healing Wave"] = {
    **common(hw9), **direct(hw9, 0, "bonus healing"),
    "max_trainable": True,
    "status": "forever-confirmed",
    "source": [src(10396), TOOLTIP + " (Rank 9: 1275 to 1457)"],
    "notes": "Rank 9 is the highest trainer rank. Rank 10 (25357) is taught by the AQ20 book Tablet of Healing Wave X "
             "(data/repos/wowsims-forever/sim/core/spelldata/book_ranks.go:21; data/repos/mythicsim-forever-engine/src/prepare/spelldata/book_ranks.rs:52). "
             "Forever values are lower than Classic Era (Era R10 1620-1850).",
    "rank_10_book": {**common(hw10), **direct(hw10, 0, "bonus healing"), "status": "forever-confirmed",
                     "source": [src(25357), TOOLTIP + " (Rank 10: 1508 to 1722)"]},
}
lhw = parse(10468)
S["Lesser Healing Wave"] = {**common(lhw), **direct(lhw, 0, "bonus healing"), "status": "forever-confirmed",
                            "source": [src(10468), TOOLTIP + " (775 to 865)"]}
ch = parse(10623)
e = ch["effects"][0]
S["Chain Heal"] = {**common(ch), **direct(ch, 0, "bonus healing"),
                   "targets": e["chain_targets"], "jump_multiplier": e["chain_amp"],
                   "jump_rule": "each jump heals 50% of the previous target's heal (bonus healing included); target 2 = 0.5, target 3 = 0.25",
                   "status": "forever-confirmed",
                   "source": [src(10623), TOOLTIP + " (473 to 540, 'Each jump is 50% as effective as the previous target')"],
                   "notes": "Riptide on the primary target: +25% to that target only (Riptide effect 3). Under MythicSim's Forever rules jumps go only to recently damaged party members "
                            "(data/repos/mythicsim-forever-engine/src/classes/shaman/prepare/heals.rs)."}
rt = parse(1239243)
S["Riptide"] = {**common(rt), **periodic(rt, 1, "bonus healing"),
                "direct_heal": None,
                "chain_heal_bonus_pct": rt["effects"][2]["base_points"],
                "talent": "Restoration 31-point talent (rank 1 at 40, rank 2 at 50, rank 3 at 60)",
                "status": "forever-confirmed",
                "source": [src(1239243), TOOLTIP + " (Rank 3: 805 over 15 sec, 230 mana, 12 sec cooldown)", NOTES_NOV2, MYTHIC_HOTFIX],
                "notes": "Since the 2 Nov 2026 notes: no initial heal, cooldown 12 s (was 6), mana -40% (was 385). The row's former direct heal is an inert E_DUMMY. "
                         "Sept 24 notes: Riptide can crit; whether HoT ticks crit is not stated."}
hst, hstt = parse(10463), parse(10461)
p = periodic(hstt, 0, "bonus healing")
p["duration_s"] = hst["duration_ms"] / 1000
p["ticks"] = int(p["duration_s"] / p["tick_period_s"])
p["total"] = None
p["coefficient_total"] = None
S["Healing Stream Totem"] = {**common(hst), **p, "targets": "party members within 30 yd",
                             "status": "forever-confirmed",
                             "source": [src(10463), src(10461), TOOLTIP + " (11 every 2 seconds, 5 min, 80 mana)"],
                             "notes": "Era: 14 per 2 s for 1 min. Restorative Totems +50% at 5/5 (applies to the whole tick incl. bonus since Oct 16)."}
ms, mst = parse(10497), parse(10494)
S["Mana Spring Totem"] = {**common(ms), "mana_per_tick": mst["effects"][0]["base_points"], "tick_period_s": mst["effects"][0]["period_ms"] / 1000,
                          "mp5_equivalent": mst["effects"][0]["base_points"] * 2.5, "targets": "party members within 30 yd",
                          "status": "forever-confirmed",
                          "source": [src(10497), src(10494), TOOLTIP + " (10 mana every 2 seconds, 5 min, 100 mana)"]}
mt, mtt = parse(1325256), parse(1325257)
tick = mtt["effects"][0]["base_points"]
S["Mana Tide Totem"] = {**common(mt), "mana_per_tick": tick, "tick_period_s": 3.0, "ticks": 4, "total_mana_per_target": tick * 4,
                        "duration_s_row": mt["duration_ms"] / 1000, "duration_s_tooltip": 12,
                        "talent": "Restoration 16-point talent; ranks at 25, 38, 48, 58",
                        "status": "forever-confirmed",
                        "source": [src(1325256), src(1325257), TOOLTIP + " (Rank 4, level 58: 290 mana every 3 seconds for 12 sec, 60 mana, 5 min cooldown)"],
                        "rank_3": {"spell_id": 17359, "learned_level": 48, "mana_per_tick": parse(17360)["effects"][0]["base_points"], "mana": parse(17359)["mana"]}}
ws, wst = parse(408510), parse(408511)
S["Water Shield"] = {**common(ws), "globes": ws["proc_charges"], "mana_per_globe_pct_max_mana": wst["effects"][0]["base_points"],
                     "internal_cooldown_s": ws["icd_ms"] / 1000, "cooldown_s": None,
                     "triggers": "a spell/melee/ranged hit taken, or any critical spell (damage or heal) the shaman casts",
                     "talent": "Restoration 11-point talent",
                     "status": "forever-confirmed",
                     "source": [src(408510), src(408511),
                                "https://forever.warcraftdb.com/api/v1/talents/shaman (talent text)",
                                "data/repos/wowsims-forever/sim/shaman/shields.go",
                                "data/repos/mythicsim-forever-engine/src/classes/shaman/prepare/shields.rs"],
                     "notes": "No mana cost on the row. 15 s cooldown removed in client 70532 (Oct 8 notes: it 'didn't have one'). Oct 16 notes: any critical spell triggers (was only critical heals). "
                              "Effect 2 (A_DUMMY 1) has no known use. Exclusive with Lightning Shield."}
ls_, lso = parse(10432), parse(26363)
S["Lightning Shield"] = {**common(ls_), "orbs": ls_["proc_charges"], "damage_per_orb": lso["effects"][0]["base_points"],
                         "coefficient": rnd(lso["effects"][0]["sp_coef"], 4), "coefficient_applies_to": "bonus damage (nature)",
                         "internal_cooldown_s": ls_["icd_ms"] / 1000, "can_crit": False,
                         "status": "forever-confirmed",
                         "source": [src(10432), src(26363), TOOLTIP + " (Rank 7: 178 Nature damage, 370 mana)", "data/repos/wowsims-forever/sim/shaman/shields.go"],
                         "notes": "Era R7 198. Orb fires on being hit, one per 3.5 s."}

# ---------------- damage ----------------
lb = parse(15208)
S["Lightning Bolt"] = {**common(lb), **direct(lb, 0, "bonus damage (nature)"), "status": "forever-confirmed",
                       "source": [src(15208), TOOLTIP + " (342 to 381, 220 mana, 2.5 sec cast)", MYTHIC_HOTFIX + " SHAMAN_ROWS_20261104"],
                       "notes": "Base raised by the 2 Nov notes (was 196 base, 1.2/level). Ranks 4+ are 2.5 s casts with coefficient 0.714 (Shaman deep dive)."}
cl = parse(10605)
e = cl["effects"][0]
S["Chain Lightning"] = {**common(cl), **direct(cl, 0, "bonus damage (nature)"), "targets": e["chain_targets"], "jump_multiplier": e["chain_amp"],
                        "status": "forever-confirmed",
                        "source": [src(10605), TOOLTIP + " (494 to 552, 495 mana, 2.5 sec cast, 6 sec cooldown)", MYTHIC_HOTFIX],
                        "notes": "Each jump -30%. 2 Nov notes: cast 2.5 s, primary damage and mana raised. Coefficient 0.714 per mythicsim CHAIN_LIGHTNING_COEFFICIENTS_20261102."}
es = parse(10414)
S["Earth Shock"] = {**common(es), **direct(es, 0, "bonus damage (nature)"), "status": "forever-confirmed",
                    "source": [src(10414), TOOLTIP + " (517 to 545, 450 mana, 6 sec cooldown)"],
                    "notes": "Shocks share one 6 s cooldown (category 19). 2 Nov notes reverted shock base damage to Classic Era. Interrupt 2 s lockout."}
fs6, fs5 = parse(29228), parse(10448)
S["Flame Shock"] = {**common(fs6), "direct": direct(fs6, 0, "bonus damage (fire)"), "dot": periodic(fs6, 1, "bonus damage (fire)"),
                    "status": "forever-confirmed",
                    "source": [src(29228), TOOLTIP + " (292 immediately and 320 over 12 sec, 410 mana)"],
                    "notes": "Rank 6 trainability disputed: wowsims book_ranks.go:22 lists 29228 as 'Tablet of Flame Shock VI' (yet still sims it); mythicsim's AQ20 book list and the wowforevertalents trainer list do not. "
                             "Rank 5 below.",
                    "rank_5": {**common(fs5), "direct": direct(fs5, 0, "bonus damage (fire)"), "dot": periodic(fs5, 1, "bonus damage (fire)"), "source": [src(10448)]}}
frs = parse(10473)
S["Frost Shock"] = {**common(frs), **direct(frs, 1, "bonus damage (frost)"), "slow_pct": 50, "status": "forever-confirmed",
                    "source": [src(10473), TOOLTIP + " (495 to 524, 430 mana)"]}
ss = parse(17364)
S["Stormstrike"] = {**common(ss), "weapon_damage_pct": ss["effects"][2]["base_points"], "weapon_damage_kind": "normalized (2.4 one-hand, 3.3 two-hand, 1.7 dagger)",
                    "debuff": {"nature_damage_taken_from_caster_pct": ss["effects"][1]["base_points"], "affects": "Lightning Bolt, Chain Lightning, Earth Shock",
                               "duration_s": 12, "charges": ss["proc_charges"], "consumed_only_if_spell_lands": True},
                    "talent": "Enhancement 16-point talent",
                    "status": "forever-confirmed",
                    "source": [src(17364), NOTES_NOV2 + " (150% normalized, cooldown 8 to 6 s)", "data/repos/wowsims-forever/sim/shaman/stormstrike.go"],
                    "notes": "Mana 8% of base mana (Oct 16 notes); 1520 base -> 121.6."}
wfc, wfb, wfp = parse(16362), parse(16361), parse(439431)
S["Windfury Weapon"] = {**common(wfc), "duration_s": 3600, "proc_chance_pct": wfp["proc_chance"], "proc_icd_s": wfp["icd_ms"] / 1000,
                        "extra_attacks": int(wfb["effects"][1]["base_points"]), "extra_attack_power": rnd(at60(wfb["effects"][0]), 1),
                        "extra_attack_rules": "each extra swing = main-hand weapon damage with +333 AP; rolls the special-attack table (no glancing); counts as white for procs; spends no Flurry charge (wowsims)",
                        "status": "forever-confirmed",
                        "source": [src(16362), src(16361), src(439431), TOOLTIP + " (20% chance of 2 extra attacks with 333 extra AP, 60 min, 165 mana)",
                                   "data/repos/wowsims-forever/sim/shaman/weapon_imbues.go"],
                        "notes": "Main-hand imbue disables your own Windfury Totem benefit. 1.5 s ICD is the passive row's."}
ftc, ftp, fta = parse(16342), parse(16344), parse(10444)
per100 = at60(ftp["effects"][0])
S["Flametongue Weapon"] = {**common(ftc), "duration_s": 3600, "proc_chance_pct": 100,
                           "damage_per_hit_formula": f"{per100:.0f} * weapon_speed / 100 (+ {fta['effects'][0]['sp_coef']:.2f} * bonus fire damage)",
                           "damage_at_speed": {"2.6": rnd(per100 * 2.6 / 100, 2), "3.6": rnd(per100 * 3.6 / 100, 2)},
                           "coefficient": rnd(fta["effects"][0]["sp_coef"], 3), "coefficient_applies_to": "bonus damage (fire)",
                           "status": "forever-confirmed",
                           "source": [src(16342), src(16344), src(10444), TOOLTIP + " (35.49 to 112.4 per hit by weapon speed)", "data/repos/wowsims-forever/sim/shaman/weapon_imbues.go"],
                           "notes": "Every main-hand melee hit (passive 436519, no roll). Spell hit/crit table. Does not stack with Flametongue Totem."}
rbc, rbp = parse(16316), parse(16313)
S["Rockbiter Weapon"] = {**common(rbc), "duration_s": 3600, "attack_power": rnd(at60(rbp["effects"][0]), 1), "threat": "extra threat on hits (20871: 72 threat per second of swing)",
                         "status": "forever-confirmed",
                         "source": [src(16316), src(16313), TOOLTIP + " (Rank 7: +653 melee AP, 150 mana)"]}
st, sta = parse(10438), parse(10436)
S["Searing Totem"] = {**common(st), **direct(sta, 0, "bonus damage (fire)"), "attack_interval_s": sta["cast_ms"] / 1000,
                      "status": "forever-confirmed",
                      "source": [src(10438), src(10436), TOOLTIP + " (Rank 6: 40 to 54, 55 sec, 170 mana)", "data/repos/wowsims-forever/sim/shaman/fire_totems.go"]}

# ---------------- utility ----------------
cote, tc, tr = parse(66842), parse(437009), parse(36936)
S["Call of the Elements"] = {**common(cote), "status": "forever-confirmed", "source": [src(66842), "https://news.blizzard.com/en-us/article/24302097"],
                             "notes": "Summons the four pre-set totems; costs the sum of their mana. Call of the Spirits (66844, lvl 40 row) and Call of the Ancestors (66843, lvl 30 row) are the 2nd/3rd sets; the deep dive gives the opposite levels."}
S["Totemic Call"] = {**common(tc), "status": "forever-confirmed", "source": [src(437009), NOTES_NOV2],
                     "notes": "Renamed from Totemic Projection; moves your totems to you; 30 s cooldown; 25% of base mana."}
S["Totemic Recall"] = {**common(tr), "mana_refund_pct": tr["effects"][0]["base_points"], "status": "forever-confirmed", "source": [src(36936)]}

# ---------------- formulas ----------------
WS = "data/repos/wowsims-forever/"
MS = "data/repos/mythicsim-forever-engine/"
F = {
    "level": 60,
    "base_stats_dwarf_shaman_60": {
        "value": {"health": 1280, "mana": 1520, "strength": 87, "agility": 51, "stamina": 98, "intellect": 89, "spirit": 99, "attack_power": 100,
                  "spell_crit_pct": 2.3, "melee_crit_pct": 1.7, "dodge_pct_base": 1.7},
        "status": "mixed: base mana and race offsets forever-confirmed; class attributes/health from sim tables; base crit vanilla fallback",
        "source": [WS + "sim/core/base_stats.go (ClassBaseStats, RaceOffsets, ClassBaseDodge)", WS + "sim/core/base_stats_auto_gen.go (ExtraClassBaseStats)",
                   MS + "data/go-tables.json (base_stats.ClassShaman.RaceDwarf, identical)",
                   "https://github.com/wowsims/forever PR #619 (Forever confirmed original race offsets, ClassicWoWCommunity/forever-bugs#414)"],
        "notes": "Dwarf offsets Str +2, Agi -4, Sta +3, Int -1, Spi -1 on class base Str 85/Agi 55/Sta 95/Int 90/Spi 100. Base crit comes from hand-kept vanilla tables (tools/base_stats_parser.py)."},
    "health_per_stamina": {"value": "first 20 Stamina give 1 HP each, every point above 20 gives 10 HP", "status": "vanilla fallback (sim model)", "source": [WS + "sim/core/base_stats.go comment on ClassBaseStats"]},
    "mana_per_intellect": {"value": "first 20 Int give 1 mana each, every point above 20 gives 15 mana (mana = base + 20 + 15*(Int-20))", "status": "vanilla fallback (sim model)", "source": [WS + "sim/core/mana.go EnableManaBarWithModifier", MS + "src/prepare/character.rs:502-505"]},
    "spell_crit_per_intellect_pct": {"value": 0.0169, "int_per_1pct": round(1 / 0.0169, 1), "status": "forever-confirmed (PlayerExpectedStat, Forever game files)", "source": [WS + "sim/core/base_stats_auto_gen.go CritPerIntMaxLevel", MS + "data/go-tables.json"]},
    "melee_crit_per_agility_pct": {"value": 0.0508, "agi_per_1pct": round(1 / 0.0508, 1), "status": "forever-confirmed (PlayerExpectedStat)", "source": [WS + "sim/core/base_stats_auto_gen.go CritPerAgiMaxLevel", WS + "sim/shaman/shaman.go:34"],
                                   "notes": "Dodge per Agility is the same 0.0508%."},
    "base_spell_crit_pct": {"value": 2.3, "status": "vanilla fallback (hand-kept table; no Forever game file ships it)", "source": [WS + "sim/core/base_stats_auto_gen.go ExtraClassBaseStats", WS + "tools/base_stats_parser.py"]},
    "base_melee_crit_pct": {"value": 1.7, "status": "vanilla fallback", "source": [WS + "sim/core/base_stats_auto_gen.go ExtraClassBaseStats"]},
    "attack_power": {"value": "AP = 100 + 2*Strength (Agility gives no AP to a Shaman); Mental Dexterity adds 50/100/150% of Int", "status": "vanilla fallback (sim model) + forever talent",
                     "source": [WS + "sim/shaman/shaman.go:37 (Str->AP 2.0)", WS + "sim/core/base_stats.go (AttackPower 100)", NOTES_NOV2]},
    "ap_to_dps": {"value": 14.0, "formula": "weapon damage + weapon_speed * AP / 14; specials use normalized speed (2.4 1H, 3.3 2H, 1.7 dagger)", "status": "vanilla fallback (sim model)", "source": [WS + "sim/core/constants.go DefaultAttackPowerPerDPS", WS + "sim/core/attack.go"]},
    "combat_ratings_at_60": {"value": {"hit_rating_per_1pct": 10, "crit_rating_per_1pct": 14, "haste_rating_per_1pct": 10, "expertise_rating_per_1pct": 10, "dodge": 12, "parry": 15, "block": 5, "defense_per_skill": 1},
                             "status": "forever-confirmed (CombatRatings gametable from the Forever client)", "source": [WS + "assets/db_inputs/basestats-forever/CombatRatings.txt (row 60)", WS + "sim/core/base_stats_auto_gen.go"]},
    "hit_and_crit_merged": {"value": "one Hit Rating feeds melee, ranged and spell hit; one Crit Rating feeds melee, ranged and spell crit. Agility still gives melee crit and Intellect spell crit separately.",
                            "status": "forever-confirmed (Blizzard) / sim model for the split", "source": ["https://worldofwarcraft.blizzard.com/news/24303313 ('Spell, melee, and ranged hit chance are combined')", WS + "sim/core/unit.go RatingChannelTable"]},
    "bonus_healing_to_damage": {"value": "Applied on items: a 'bonus healing' item row also states spell damage of about 1/3 of it, rounded (e.g. Benediction 195 healing / 65 damage). The sim keeps HealingPower and SpellDamage as two stats; heals use HealingPower x coefficient, damage spells use SpellDamage (+ school damage) x coefficient.",
                                "status": "forever-confirmed (Blizzard text + item data)", "source": ["https://worldofwarcraft.blizzard.com/news/24303313 ('Bonus healing now also includes one third as much bonus damage')", WS + "assets/database/db.json (stat 4 HealingPower, stat 5 SpellDamage)", WS + "sim/core/spell_result.go HealingPower/CalcHealing"],
                                "notes": "A few items (e.g. Pure Elementium Band 19382, Rejuvenating Gem 19395) carry healing with no damage in the current data."},
    "spirit_mana_regen": {"value": "6.25 + Spirit/8 mana per second (= 2.5*(12.5 + Spirit/4) per 5 s), for every class", "status": "forever-measured (community, in-game tooltips across classes)",
                          "source": [WS + "sim/core/mana.go:76", "https://github.com/wowsims/forever/pull/299 ('all mana classes were moved to the formula that was just for Mage/Priests')"],
                          "disagreement": "mythicsim (frozen Go reference) uses 7.5 + Spirit/10 per second for Shaman: " + MS + "src/prepare/character.rs:518-522. Vanilla fallback for Shaman: 17 + Spirit/5 per 2 s tick (8.5 + Spirit/10 per second)."},
    "five_second_rule": {"value": "Spirit regen stops for 5 s after any mana spend (or until a hard cast ends, whichever is later); MP5 continues. Mindfulness lets 50% continue while casting; Improved Stormstrike 50% for 15 s.",
                         "status": "sim model (vanilla rule retained; no Forever statement found)", "source": [WS + "sim/core/mana.go SpendCost (FiveSecondRuleRefreshTime) and creditManaRegen", "https://forever.warcraftdb.com/api/v1/talents/shaman (Mindfulness)"]},
    "mp5": {"value": "MP5/5 mana per second, continuous, unaffected by the 5-second rule", "status": "sim model", "source": [WS + "sim/core/mana.go MP5ManaRegenPerSecond"]},
    "regen_tick": {"value": "about 2.02 s per-player tick in combat logs; wowsims credits regen continuously every 100 ms", "status": "forever-measured (community)", "source": ["https://github.com/wowsims/forever/pull/655", WS + "sim/core/mana.go manaTickDuration"]},
    "crit_multipliers": {"value": {"spell_damage": 1.5, "heal": 1.5, "melee_ranged": 2.0}, "status": "vanilla fallback (sim model)", "source": [WS + "sim/core/spell.go:955 CritDamageMultiplier", MS + "src/core/fight/healing.rs:222"],
                         "notes": "Elemental Fury 5/5: +100% crit bonus for Fire/Frost/Nature spells and fire totems (2.0x). Dwarf Earth Fury (2% crit damage) removed 26 Oct; Tauren 2% crit bonus removed."},
    "spell_hit_table": {"value": {"miss_vs_60_pct": 4, "miss_vs_61_pct": 5, "miss_vs_62_pct": 6, "miss_vs_63_pct": 17, "minimum_miss_pct": 0},
                        "status": "vanilla fallback for the level table; 'no 1% floor' is a wowsims Forever rule without a cited source",
                        "source": [WS + "sim/core/target.go spellMissChance", WS + "sim/core/spell_result.go spellChanceToMiss", "wowsims commit 0301ba3421 'No 1% spell miss floor in Forever'"]},
    "melee_hit_table_vs_63": {"value": {"miss_pct_1h_special_or_2h": 8.0, "miss_pct_dual_wield_white": 27.0, "dodge_pct": 6.5, "parry_pct_front": 14.0, "glance_chance_pct": 40, "glance_damage_pct": "55-75 (avg 65)", "crit_suppression_pct": 3.0, "aura_crit_suppression_pct": 1.8},
                              "assumes": "300 weapon skill (60 x 5)", "status": "vanilla fallback (sim model)", "source": [WS + "sim/core/target.go newAttackTableHand, NewAttackTable", WS + "sim/core/spell_outcome.go:546 (DW +19%)"]},
    "melee_hit_table_vs_60": {"value": {"miss_pct": 5.0, "miss_pct_dual_wield_white": 24.0, "dodge_pct": 5.0, "parry_pct": 5.0, "glance_chance_pct": 10, "glance_damage_pct": "91-99"},
                              "status": "vanilla fallback (sim model)", "source": [WS + "sim/core/target.go newAttackTableHand"]},
    "dwarf_racials": {"value": "Artisan's Precision +1% hit with spells and attacks; Stoneform -10% physical damage taken 8 s, 3 min cd; Earth Fury removed", "status": "forever-confirmed", "source": [NOTES_NOV2 + " (26 Oct racial post)", WS + "sim/core/racials.go:14-16"]},
    "gcd": {"value": {"spells_s": 1.5, "totems_s": 1.0, "min_s": 1.0}, "status": "forever-confirmed (row GCDMs; Shaman deep dive 'All totems now have a 1.0 second global cooldown')",
            "source": ["https://news.blizzard.com/en-us/article/24302097", STORE_REL + " (GCDMs 1000 on every totem row)", WS + "sim/core/constants.go"], "notes": "wowsims lets spell haste shorten the GCD down to 1.0 s (sim model)."},
}

worked = {}
str_, agi, sta, int_, spi = 87, 51, 98, 89, 99
worked["naked_dwarf_shaman_60"] = {
    "max_mana": 1520 + 20 + 15 * (int_ - 20),
    "max_health": 1280 + 20 + 10 * (sta - 20),
    "spell_crit_pct": round(2.3 + int_ * 0.0169, 3),
    "melee_crit_pct": round(1.7 + agi * 0.0508, 3),
    "attack_power": 100 + 2 * str_,
    "spirit_regen_mp_per_s_wowsims": round(6.25 + spi / 8, 3),
    "spirit_regen_mp5_wowsims": round(5 * (6.25 + spi / 8), 2),
    "status": "derived from the formulas above",
}

data = {
    "generated": "2026-11-08",
    "game": "World of Warcraft: Forever, level 60 Shaman (Dwarf)",
    "primary_data": "wowsims/forever @ 125e534 (2026-11-08), spell store regenerated from the live client (1.60.1.70862 and its hotfix cache); cross-checked against wowforevertalents.com tooltips (same build) and mythicsim-forever-engine @ b3c5eb6",
    "value_conventions": "mean_at_60 = BasePoints + PointsPerLevel*(min(60, MaxLevel) - BaseLevel). min/max = mean*(1 -/+ variance/2), rounded; the game applies the roll after adding bonus healing/damage. Coefficients are EffectBonusCoefficient (per tick for periodic effects).",
    "spells": S,
    "formulas": F,
    "worked_examples": worked,
    "gaps": [
        "Healing Wave / Lesser Healing Wave / Chain Heal: no Blizzard note explains why Forever values are below Classic Era; the numbers are client data.",
        "Riptide HoT tick crits: not stated anywhere checked.",
        "Spirit regen formula: wowsims (6.25+Spi/8 per s, measured) and mythicsim (7.5+Spi/10 per s) disagree; no Blizzard statement.",
        "Five-second rule and attack tables (glancing, crit suppression, DW penalty) are vanilla rules kept by the sims; no Forever-specific confirmation found.",
        "Base spell/melee crit (2.3% / 1.7%) and class base attributes/health come from hand-kept tables, not Forever game files.",
        "Flame Shock rank 6 trainer vs book: sources disagree.",
        "No 1% spell-miss floor: wowsims rule, evidence not cited in the commit.",
        "Mana Tide row duration 13 s vs tooltip 12 s; 4 ticks assumed.",
    ],
}

with open(OUT, "w") as f:
    json.dump(data, f, indent=2)
print("wrote", OUT, len(S), "spells")
