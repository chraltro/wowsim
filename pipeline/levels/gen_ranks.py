import json, math, struct, re, sys

R = json.load(open('/home/claude/work/spells_all.json'))
f32 = lambda x: struct.unpack('f', struct.pack('f', float(x)))[0]

def S(i):
    r = R.get(str(i))
    if r is None:
        raise SystemExit(f"missing spell {i}")
    return r

# --- ladders, read from sim/shaman/spell_data_auto_gen.go ---
src = open('/home/claude/data/repos/wowsims-forever/sim/shaman/spell_data_auto_gen.go').read()
LAD = {}
for m in re.finditer(r"^\t(\w+):\s+spelldata\.(Ranked|Talent)\(([^)]*)\)", src, re.M):
    LAD[m.group(1)] = (m.group(2), [int(x) for x in m.group(3).replace(' ', '').split(',')])

BOOK = {25357: "Tablet of Healing Wave X", 29228: "Tablet of Flame Shock VI",
        25361: "Tablet of Strength of Earth Totem V", 25359: "Tablet of Grace of Air Totem III"}
SCHOOL = {1: "physical", 2: "holy", 4: "fire", 8: "nature", 16: "frost", 32: "shadow", 64: "arcane"}

DMG_TYPES = {'E_SCHOOL_DAMAGE', 'E_HEAL', 'E_HEALTH_LEECH', 'E_WEAPON_DAMAGE', 'E_NORMALIZED_WEAPON_DMG', 'E_WEAPON_DAMAGE_NOSCHOOL'}
DMG_AURAS = {'A_PERIODIC_DAMAGE', 'A_PERIODIC_HEAL', 'A_PERIODIC_LEECH', 'A_DAMAGE_SHIELD', 'A_PROC_TRIGGER_DAMAGE'}

def nm(x):
    return x.replace('dbcenums.', '') if isinstance(x, str) else x

def gain(e, L):
    lvl = L
    mx = e.get('MaxLevel', 0) or 0
    if mx > 0 and mx < lvl:
        lvl = mx
    d = lvl - (e.get('BaseLevel', 0) or 0)
    if d < 0:
        d = 0
    return f32(f32(d) * f32(e.get('PPL', 0) or 0))

def dmg_or_heal(e):
    return nm(e.get('Type')) in DMG_TYPES or nm(e.get('Aura')) in DMG_AURAS

def exact(e, L):
    return f32(f32(e.get('BasePoints', 0) or 0) + gain(e, L))

def average(e, L):
    v = exact(e, L)
    return v if dmg_or_heal(e) else math.floor(v)

def spread(e, L):
    V = e.get('Variance', 0) or 0
    if V == 0:
        w = math.floor(exact(e, L)); return w, w
    bp = f32(e.get('BasePoints', 0) or 0)
    side = f32(f32(f32(abs(e.get('BasePoints', 0) or 0)) * f32(V)) / 2)
    g = gain(e, L)
    lo = f32(f32(round_even(f32(bp - side))) + g)
    hi = f32(f32(round_even(f32(bp + side))) + g)
    return math.floor(lo), math.ceil(hi)

def round_even(x):
    return float(round(x))  # Python round() is half-to-even, as math.RoundToEven

def rnd(x, n=4):
    return None if x is None else (int(x) if float(x).is_integer() else round(x, n))

def spell_level_info(r):
    return r.get('SpellLevel', 0), r.get('BaseLevel', 0), r.get('MaxLevel', 0)

def effect_obj(r, e, learn):
    typ, aura = nm(e.get('Type')), nm(e.get('Aura'))
    bp, ppl = e.get('BasePoints', 0) or 0, e.get('PPL', 0) or 0
    o = {"index": e.get('Index', 0), "type": typ}
    if aura: o["aura"] = aura
    o["base_points"] = rnd(bp, 6)
    if ppl: o["points_per_level"] = rnd(f32(ppl), 6)
    o["scaling_base_level"] = e.get('BaseLevel', 0) or 0
    o["scaling_max_level"] = e.get('MaxLevel', 0) or 0
    if e.get('Variance'): o["variance"] = rnd(f32(e['Variance']), 6)
    if e.get('SPCoef') is not None and (dmg_or_heal(e) or typ in ('E_DUMMY',)):
        o["sp_coef"] = rnd(f32(e['SPCoef']), 6)
    if e.get('APCoef'): o["ap_coef"] = rnd(f32(e['APCoef']), 6)
    if e.get('PeriodMs'):
        o["period_ms"] = e['PeriodMs']
        if r.get('DurationMs', 0) > 0:
            o["ticks"] = r['DurationMs'] // e['PeriodMs']
    if e.get('TriggerID'): o["trigger_spell"] = e['TriggerID']
    if e.get('ChainTargets'): o["chain_targets"] = e['ChainTargets']
    if e.get('ChainTargets') and e.get('ChainAmp') not in (None, 1, 1.0): o["chain_amp"] = rnd(f32(e['ChainAmp']), 6)
    if e.get('Misc'): o["misc"] = e['Misc']
    if e.get('RadiusMax'): o["radius_yd"] = rnd(e['RadiusMax'])
    if e.get('PointsPerResource'): o["points_per_resource"] = e['PointsPerResource']
    o["amount_rounding"] = "exact (fractional, damage/heal)" if dmg_or_heal(e) else "floor (whole number)"
    lo_lvl = max(1, learn)
    o["value_at_learn_level"] = rnd(average(e, lo_lvl))
    o["value_at_60"] = rnd(average(e, 60))
    if ppl:
        cap = e.get('MaxLevel', 0) or 60
        top = min(60, cap)
        o["values_by_level"] = {str(L): rnd(average(e, L)) for L in range(lo_lvl, top + 1)}
        o["constant_from_level"] = top if cap <= 60 else None
        if cap > 60:
            o["note_scaling"] = f"keeps scaling past 60 (max_level {cap}); at 60 it has gained {60 - (e.get('BaseLevel',0) or 0)} levels"
    if e.get('Variance'):
        o["tooltip_range_at_learn_level"] = list(spread(e, lo_lvl))
        o["tooltip_range_at_60"] = list(spread(e, 60))
        if typ == 'E_HEAL' or (typ == 'E_SCHOOL_DAMAGE' and r.get('School') != 1):
            o["roll_rule"] = "whole amount (value + sp_coef*bonus) * uniform(1 - variance/2, 1 + variance/2)  [wowsims DirectVariance]"
        else:
            o["roll_rule"] = "base_points +- |base_points|*variance/2, rounded, plus level gain  [wowsims RollAt]"
    return o

def rank_obj(i, role=None):
    r = S(i)
    learn, base, mx = spell_level_info(r)
    o = {"id": i, "name": r['Name']}
    if r.get('Rank'): o["rank"] = r['Rank']
    if role: o["role"] = role
    o["status"] = "forever"
    o["learn_level"] = learn
    o["base_level"] = base
    o["max_level"] = mx
    o["book_rank"] = i in BOOK
    if i in BOOK: o["book_item"] = BOOK[i]
    o["school"] = SCHOOL.get(r.get('School'), r.get('School'))
    for k_src, k_dst in [('CastTimeMs', 'cast_ms'), ('GCDMs', 'gcd_ms'), ('CooldownMs', 'cooldown_ms'),
                         ('CategoryCooldownMs', 'category_cooldown_ms'), ('Category', 'cooldown_category'),
                         ('DurationMs', 'duration_ms'), ('MaxRange', 'range_yd'), ('Speed', 'missile_speed')]:
        if r.get(k_src): o[k_dst] = rnd(r[k_src])
    o.setdefault('cast_ms', 0)
    pw = r.get('Powers') or []
    if pw:
        p = pw[0]
        c = {}
        if p.get('Cost'): c["mana"] = p['Cost']
        if p.get('CostPct'): c["pct_base_mana"] = rnd(f32(p['CostPct']))
        if p.get('CostPerLevel'): c["mana_per_level"] = p['CostPerLevel']
        if p.get('PerSecond'): c["mana_per_second"] = p['PerSecond']
        if p.get('Type'): c["power_type"] = p['Type']
        o["cost"] = c
    else:
        o["cost"] = {"mana": 0}
    proc = {}
    for k_src, k_dst in [('ProcChance', 'chance_column'), ('ProcCharges', 'charges'), ('ICDMs', 'icd_ms'),
                         ('ProcChanceSource', 'chance_source'), ('MaxStack', 'max_stack'), ('RPPM', 'ppm')]:
        if r.get(k_src): proc[k_dst] = r[k_src] if not isinstance(r[k_src], str) else r[k_src].replace('ProcChance', '')
    if r.get('ProcFlags'):
        proc["proc_flags"] = r['ProcFlags']
    if proc: o["proc"] = proc
    if r.get('RefIDs'): o["tooltip_refs"] = r['RefIDs']
    if r.get('_overrides'): o["wowsims_overrides"] = r['_overrides']
    o["effects"] = [effect_obj(r, e, learn) for e in r.get('Effects', [])]
    if role is None and 0 < learn < 20:
        f = 1 - (20 - learn) * 0.0375
        for eo in o["effects"]:
            if eo.get("sp_coef"):
                eo["sp_coef_if_vanilla_sub20_penalty"] = {"value": rnd(eo["sp_coef"] * f, 6), "factor": rnd(f, 6),
                    "status": "vanilla", "applied_by_wowsims_or_mythicsim": False}
    return o

def ladder(key):
    kind, ids = LAD[key]
    if kind == 'Talent':
        return ids[:1]
    return ids

out = {"meta": {}, "spells": {}}

def fam(key, name, notes=None, linked=None, extra=None):
    ids = ladder(key)
    ranks = [rank_obj(i) for i in ids]
    if linked:
        for rk, rid in zip(ranks, ids):
            for role, fn in linked:
                lid = fn(rid)
                if lid is None: continue
                if isinstance(lid, list):
                    rk.setdefault("linked", []).extend(rank_obj(x, role) for x in lid)
                else:
                    rk.setdefault("linked", []).append(rank_obj(lid, role))
    d = {"name": name, "wowsims_ladder": f"spellData.{key} = spelldata.{LAD[key][0]}({', '.join(map(str, LAD[key][1]))})",
         "ranks": ranks}
    if notes: d["notes"] = notes
    if extra: d.update(extra)
    out["spells"][key] = d

ref0 = lambda i: S(i)['RefIDs'][0]
ref1 = lambda i: S(i)['RefIDs'][1]

fam("HealingWave", "Healing Wave", ["Rank 10 (25357) is a book rank: Tablet of Healing Wave X (raid drop), not trainer-taught."])
fam("LesserHealingWave", "Lesser Healing Wave")
fam("ChainHeal", "Chain Heal", ["chain_amp 0.5: each jump heals half the previous target; 3 targets.",
    "mythicsim-forever-engine notes Forever rules: Chain Heal jumps only to players damaged recently (src/classes/shaman/prepare/heals.rs)."])
fam("Riptide", "Riptide", [
    "Restoration talent (tier 7, wowsims talents_restoration.go applyRiptide); the talent teaches rank 1 (408521). Ranks 2/3 learn levels 50/60 from SpellLevels.",
    "Effect 0 is E_DUMMY with base 0: the initial heal is gone in this build. Client 1.60.1.70425 had it as E_HEAL 480 (+3.7/lvl) on rank 1 and 841 (+4.9/lvl) on rank 3; Blizzard's 2 Nov 2026 notes removed it (mythicsim src/prepare/hotfix_113554.rs). Treat the direct part as 0.",
    "Effect 1 is the HoT: 89/115/161 per 3 s tick, 5 ticks, sp_coef 0.1 per tick. Rank 3 tick scales +3.7/level above 60 only.",
    "Effect 2 (A_DUMMY 25): Chain Heal cast directly on the Riptide target heals 25% more.",
    "Category cooldown 12 s (was 6 s in 70425); mana 150/180/230 (was 245/300/385).",
    "wowsims does not implement Riptide (TODO in talents_restoration.go)."])
for rk in out["spells"]["Riptide"]["ranks"]:
    e0 = rk["effects"][0]
    e0["inert_in_forever"] = True
    e0["raw_note"] = "E_DUMMY: the initial heal was removed (2 Nov 2026 notes). base_points/points_per_level/sp_coef are the leftover row values; the heal is 0."
    e0["value_at_learn_level"] = 0
    e0["value_at_60"] = 0
    e0.pop("values_by_level", None); e0.pop("constant_from_level", None); e0.pop("note_scaling", None)
    e0.pop("tooltip_range_at_learn_level", None); e0.pop("tooltip_range_at_60", None); e0.pop("roll_rule", None)
fam("HealingStreamTotem", "Healing Stream Totem", [
    "The totem cast summons an NPC; the heal is the linked aura spell (RefIDs[0]): party area aura A_PERIODIC_HEAL every 2 s within 30 yd while the totem stands (300 s).",
    "Tick heal has no level scaling; sp_coef 0.022 per tick (client SPCoef).",
    "wowsims: registerHealingStreamTotemSpell is commented out (totems.go); mythicsim models it (heals.rs) with these rows."],
    linked=[("periodic_heal_aura", ref0)])
fam("ManaSpringTotem", "Mana Spring Totem", [
    "Linked aura: A_PERIODIC_ENERGIZE mana every 2 s to party within 30 yd, 300 s totem. No level scaling."],
    linked=[("periodic_energize_aura", ref0)])
fam("ManaTideTotem", "Mana Tide Totem", [
    "Restoration talent (tier 4); rank 1 SpellLevel 1 = available when the talent is taken (talent tier gate applies). Ranks 2-4 at 38/48/58. Rank 4 (1325256/1325257) is new in Forever.",
    "Totem lasts 13 s, energize every 3 s -> 4 ticks of 88/133/197/290 mana to the party. 5 min cooldown."],
    linked=[("periodic_energize_aura", ref0)])
fam("WaterShield", "Water Shield", [
    "Restoration talent (tier 3, SpellLevel 20). One rank. No mana cost.",
    "3 globes, 10 min. A hit taken, or one of the shaman's own spell crits (wowsims reading of the tooltip), spends a globe at most once per 3.5 s and restores 408511's 2% of MAXIMUM mana (E_ENERGIZE_PCT 2).",
    "Mana per globe at level L = 0.02 * max_mana(L); no level term in the data."],
    linked=[("mana_per_globe", lambda i: 408511)])
fam("LightningShield", "Lightning Shield", [
    "Forever rows: 3 charges, 10 min, ICD 3.5 s between orb discharges.",
    "The shield's proc effect fires 26545 (a dummy, SPCoef 1); the damage spell is the rank's orb named in RefIDs[0] (wowsims shields.go reads Refs()[0]). Orb damage has no level scaling, sp_coef 0.267, cannot crit (wowsims)."],
    linked=[("orb_damage", ref0)])
fam("LightningBolt", "Lightning Bolt", [
    "Values are the Forever 2 Nov 2026 retune (about 78% of Classic Era per Blizzard's notes, as quoted in mythicsim hotfix_113554.rs); wowsims 125e534 already carries them.",
    "wowsims registers only ranks with SpellLevel >= 44 at level 60 (ranks.go minRankLevel) because of an unquantified in-game downrank effect; see meta.coefficient_penalties."])
fam("ChainLightning", "Chain Lightning", [
    "2.5 s cast, sp_coef 0.714, 6 s category cooldown, 3 targets, each jump 70% of the previous (chain_amp 0.7). Costs are the live 6 Nov 2026 values."])
fam("EarthShock", "Earth Shock", ["Shared shock category 19, 6 s cooldown. duration_ms 2000 is the interrupt lockout."])
fam("FlameShock", "Flame Shock", [
    "Effect 0 direct hit (scales per level), effect 1 DoT: 4 ticks every 3 s over 12 s, tick has no per-level scaling, sp_coef 0.1 per tick.",
    "Rank 6 (29228) is a book rank: Tablet of Flame Shock VI."])
fam("FrostShock", "Frost Shock", ["Effect 0 is the 50% slow (8 s); effect 1 is the damage."])
fam("Stormstrike", "Stormstrike", [
    "Enhancement talent (SpellLevel 40). Effects: normalized weapon damage, then 150% weapon percent damage (E_WEAPON_PERCENT_DAMAGE 150); A_MOD_SPELL_DAMAGE_FROM_CASTER +20% Nature damage taken from the shaman for 12 s, 1 charge (ProcCharges 1).",
    "Cooldown 6 s (8 s in client 70425), cost 8% of base mana."])
fam("WindfuryWeapon", "Windfury Weapon", [
    "Each rank's cast enchants the weapon (E_360, misc = SpellItemEnchantment id, 1800 = 30 min).",
    "The proc roll is the shared passive 439431: 20% chance (ProcChance 20) on main-hand melee hits, ICD 1.5 s. wowsims uses this passive for every rank (weapon_imbues.go).",
    "On proc the rank's triggered spell (RefIDs[0]) grants 2 extra attacks (E_ADD_EXTRA_ATTACKS 2) with +AP (A_MOD_ATTACK_POWER, scales per level up to max_level) for those attacks. Vanilla gave 1 extra attack."],
    linked=[("proc_attack", ref0)],
    extra={"shared_passive": rank_obj(439431, "proc_roll_passive")})
fam("FlametongueWeapon", "Flametongue Weapon", [
    "Passive 436519 (ProcChance 100): every main-hand melee hit casts the Flametongue Attack.",
    "Damage per hit (wowsims weapon_imbues.go newFlametongueImbueSpell) = proc.m1(L) * MH_swing_speed_s / 100 + attack.m1 (0), fire, sp_coef 0.1 (attack spell), can crit.",
    "proc.m1(L) = the linked 'Flametongue Weapon Proc' spell's E_DUMMY value at level L (RefIDs[0]); attack spell = RefIDs[1] (29469, 29470, then 10444 for ranks 3-6).",
    "Tooltip check: rank 6 at 60 is 2498+78*4=2810 -> 36.5 (1.3 s) to 112.4 (4.0 s) per hit."],
    linked=[("proc_value", ref0), ("attack", ref1)],
    extra={"shared_passive": rank_obj(436519, "proc_every_hit_passive")})
fam("RockbiterWeapon", "Rockbiter Weapon", [
    "The linked passive (RefIDs[0], e.g. 10400) applies A_MOD_ATTACK_POWER = base_points + points_per_level*(min(L,max_level)-base_level), floored.",
    "Rank 1 (10400): 29 + 4.1/level from 1 to 6. Rank 7 (16313): 554 + 16.5/level from 54 to 62 (653 at 60).",
    "Threat: every MH hit casts a Rockbiter Weapon Proc (wowsims uses 20871, the top of the 20860-20871 ladder: 72 threat per second of swing). Lower-rank threat procs were not extracted."],
    linked=[("ap_passive", ref0)],
    extra={"threat_proc_top_rank": rank_obj(20871, "threat_proc")})
fam("SearingTotem", "Searing Totem", [
    "Totem attack: linked 'Attack' spell (RefIDs[0]), cast every 2.2 s (its CastTimeMs; wowsims fire_totems.go Period = CastTime), fire, 20 yd, sp_coef 0.017, no level scaling.",
    "Totem duration 30/35/40/45/50/55 s by rank."],
    linked=[("attack", ref0)])


for key in ("HealingStreamTotem", "ManaSpringTotem", "ManaTideTotem", "SearingTotem"):
    for rk in out["spells"][key]["ranks"]:
        dur = rk.get("duration_ms", 0)
        for l in rk.get("linked", []):
            for e in l["effects"]:
                if e.get("period_ms"):
                    e["ticks_over_totem_duration"] = dur // e["period_ms"]
            if key == "SearingTotem" and l.get("cast_ms"):
                l["attack_interval_ms"] = l["cast_ms"]
                l["attacks_over_totem_duration"] = dur // l["cast_ms"]

out["meta"] = {
  "title": "WoW Forever Shaman spell ranks, every level 1-60",
  "generated": "2026-11-08",
  "status_legend": {"forever": "Forever client data (build 1.60.1.70862) as carried by wowsims-forever", "vanilla": "Classic/vanilla fallback", "estimate": "derived or interpolated"},
  "source": {
    "repo": "/home/claude/data/repos/wowsims-forever", "commit": "125e534",
    "client_build": "1.60.1.70862 (latest 'wowf' build on wago.tools, 2026-11-07)",
    "rank_lists": "sim/shaman/spell_data_auto_gen.go (spelldata.Ranked / spelldata.Talent)",
    "records": "sim/core/spelldata/spells_auto_gen.go (generator bakes in tools/database/overrides; any override comment is copied to wowsims_overrides)",
    "book_ranks": "sim/core/spelldata/book_ranks.go"
  },
  "formulas": {
    "value_at_level": "BasePoints + PPL * clamp(min(L, scaling_max_level) - scaling_base_level, 0); scaling_max_level 0 = no cap. Computed in float32 as wowsims Effect.AverageAt does. Damage/heal amounts keep the fraction; every other amount (AP, mana, %) is floored.",
    "roll_heal_or_spell_damage": "(value + sp_coef * spell_power) * uniform(1 - variance/2, 1 + variance/2)",
    "tooltip_range": "wowsims MinAt/MaxAt: base points +- |base|*variance/2 rounded half-to-even, plus the level gain, rounded outward. Checked against Wowhead's Forever tooltips (mythicsim test list, 25 Shaman rows): all within 1 point, 22 of 25 exact.",
    "ticks": "duration_ms // period_ms",
    "cost_pct_base_mana": "cost = pct_base_mana/100 * base_mana(L) (base mana table in shaman_levels.json)",
    "learn_level": "SpellLevels.SpellLevel of the rank. Shaman trainers teach at that level; vanilla trainer data (cmangos npc_trainer_template 61) teaches on levels 1, 4 and every even level 6-60, which is the set of SpellLevels here. Per-spell trainer mapping was not checked (emulator trainer rows list teach-spell ids)."
  },
  "talent_taught": {
    "Riptide": "Restoration tier 7 (rank 1, 408521); ranks 2/3 learn at 50/60",
    "ManaTideTotem": "Restoration tier 4 (rank 1 SpellLevel 1 = usable once the talent is taken); ranks 2-4 at 38/48/58",
    "WaterShield": "Restoration tier 3 (SpellLevel 20)",
    "Stormstrike": "Enhancement (SpellLevel 40)",
    "tier_gate": "vanilla rule: talent tier N needs 5*(N-1) points in the tree, first point at level 10, so tier N opens at level 5N+5 (estimate for Forever: not checked in client data)"
  },
  "book_ranks_in_this_file": {"25357": "Healing Wave Rank 10 - Tablet of Healing Wave X", "29228": "Flame Shock Rank 6 - Tablet of Flame Shock VI"},
  "coefficient_penalties": {
    "finding": "Neither wowsims-forever nor mythicsim-forever-engine applies the vanilla sub-20 penalty (1 - (20 - spellLevel)*0.0375) or any downrank coefficient penalty. Whether the Forever server applies one is unverified.",
    "client_data": "The client rows carry unpenalized coefficients on low ranks: Healing Wave R1 (level 1) 0.429 = 1.5/3.5, R2 (level 6) 0.571 = 2.0/3.5, R4 (level 18) 0.857 = 3.0/3.5; Lightning Bolt R1 0.429, R2 0.571.",
    "wowsims_code": [
      "resolve_spell.go: config.BonusCoefficient = damage.Coeff() (the client SPCoef, unchanged); spell_result.go adds BonusCoefficient * spell power. No level term anywhere in that path.",
      "sim/shaman/ranks.go: const minRankLevel = 44, comment: 'In game a rank deals less damage once the caster is far enough past the level it is taught at; at level 60 a rank taught at 44 or later is clear of that.' TODO: cutoff believed 42 or 43. castableRanks() registers only Lightning Bolt, Chain Lightning and the shock ranks with SpellLevel >= 44. It avoids the effect by dropping ranks; it implements no formula.",
      "sim/core/racials.go (Touch of the Grave): 'The drain takes no downrank scaling from a low-level trigger' - a comment only."
    ],
    "mythicsim_code": "docs/levels.md, Open: 'Spell coefficients below level 20: Classic scaled a low-level spell's coefficient down; whether Forever keeps it is unchecked.' src/prepare/spelldata/effect.rs uses only the per-level points; no coefficient scaling.",
    "in_this_file": "sp_coef is the client value (what both sims use). Ranks learned below 20 also carry sp_coef_if_vanilla_sub20_penalty, so the sim can switch the vanilla rule on. Neither sim applies it."
  },
  "forever_vs_vanilla_notes": [
    "Lightning Bolt, Chain Lightning and the shocks carry the 2-4 Nov 2026 retune (mythicsim hotfix_113554.rs lists the old values); Chain Lightning is 2.5 s, 0.714 coefficient.",
    "Riptide has no initial heal in 70862 (E_DUMMY base 0); 12 s cooldown.",
    "Windfury Weapon grants 2 extra attacks at 20% (passive 439431, 1.5 s ICD); Rockbiter grants attack power; Flametongue procs on every hit.",
    "Lightning Shield and Water Shield hold 3 charges, 3.5 s ICD.",
    "Healing Stream / Mana Spring totem rows last 300 s."
  ],
  "gaps": [
    "Riptide's removed initial heal: no Forever number exists to use; treat it as 0.",
    "Rockbiter threat procs below the top rank (20860-20870) not extracted; wowsims uses 20871 for every rank.",
    "Windfury Weapon: wowsims assumes every rank's enchant uses passive 439431 (20%, 1.5 s). The enchantment rows (misc 283/284/525/1669) were not read.",
    "Talent tier unlock levels for Forever trees not confirmed from client data."
  ]
}

json.dump(out, open(sys.argv[1], 'w'), indent=1)
print("families", len(out["spells"]))
