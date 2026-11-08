"""Every spell rank a levelling and dungeon sim needs, per class, for WoW Forever.

Writes wowsim/data/classes/<class>_ranks.json. Same per-rank schema as data/shaman_ranks.json (gen_ranks.py),
extended with: cost in the right resource (rage, energy, combo points, health), the vanilla trainer level and
cost, the talent that teaches a rank, and a per-rank comparison with the vanilla 1.12 row (cmangos spell_template).

Inputs: work/classes/spells_all.json (parse_spells.py over wowsims-forever spells_auto_gen.go), the class ladders
(sim/<class>/spell_data_auto_gen.go), ui/sim/talents/trees/<class>.json, sim/core/spelldata/book_ranks.go,
work/classes/cm_tables.json (extract_cmangos.py). Notes: families.py, wowsims code comments.
"""
import glob
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import CLASS_IDS, OUT, P, WS_REPO, cm, f32, ladders, rnd, spells  # noqa: E402
import families as FAM  # noqa: E402

GENERATED = "2026-11-08"
S = spells()
CM = cm()
SCHOOL = {1: "physical", 2: "holy", 4: "fire", 8: "nature", 16: "frost", 32: "shadow", 64: "arcane"}
DMG_TYPES = {'E_SCHOOL_DAMAGE', 'E_HEAL', 'E_HEALTH_LEECH', 'E_WEAPON_DAMAGE', 'E_NORMALIZED_WEAPON_DMG', 'E_WEAPON_DAMAGE_NOSCHOOL'}
DMG_AURAS = {'A_PERIODIC_DAMAGE', 'A_PERIODIC_HEAL', 'A_PERIODIC_LEECH', 'A_DAMAGE_SHIELD', 'A_PROC_TRIGGER_DAMAGE'}
WEAPON_TYPES = {'E_WEAPON_DAMAGE', 'E_NORMALIZED_WEAPON_DMG', 'E_WEAPON_DAMAGE_NOSCHOOL', 'E_WEAPON_PERCENT_DAMAGE'}
POWER = {0: "mana", 1: "rage", 2: "focus", 3: "energy", 4: "combo_points", -2: "health"}

# ---------------------------------------------------------------- book ranks (wowsims list)
BOOK = {}
for m in re.finditer(r"(\d+): true, // (.*)", open(os.path.join(WS_REPO, "sim/core/spelldata/book_ranks.go")).read()):
    BOOK[int(m.group(1))] = m.group(2).strip()

# ---------------------------------------------------------------- cmangos (vanilla 1.12) spell rows and trainers
ST_COLS = CM["spell_template"]["cols"]
ST = {r[0]: dict(zip(ST_COLS, r)) for r in CM["spell_template"]["rows"]}
TEACH = {}
for sid, r in ST.items():
    for k in (1, 2, 3):
        if r["Effect%d" % k] == 36 and r["EffectTriggerSpell%d" % k]:
            TEACH.setdefault(sid, set()).add(r["EffectTriggerSpell%d" % k])
CT_COLS = CM["creature_template"]["cols"]
CT = {r[0]: dict(zip(CT_COLS, r)) for r in CM["creature_template"]["rows"]}
TR_COLS = CM["npc_trainer"]["cols"]


def trainer_map(cid):
    """learned spell id -> {reqlevel, cost} from the class trainer template (class*10+1) and every class
    trainer of that class (creature_template TrainerType 0, TrainerClass = class) with its own rows."""
    rows = [r for r in CM["npc_trainer_template"]["rows"] if r[0] == cid * 10 + 1]
    trainers = {e for e, c in CT.items() if c["TrainerClass"] == cid and c["TrainerType"] == 0}
    rows += [r for r in CM["npc_trainer"]["rows"] if r[0] in trainers]
    out = {}
    for r in rows:
        teach, cost, lvl = r[1], r[2], r[5]
        for learned in TEACH.get(teach, {teach}):
            o = out.setdefault(learned, {"reqlevel": set(), "cost_copper": set(), "teach_spell": set()})
            o["reqlevel"].add(lvl)
            o["cost_copper"].add(cost)
            o["teach_spell"].add(teach)
    return {k: {kk: sorted(vv) for kk, vv in v.items()} for k, v in out.items()}


_EN = open(os.path.join(WS_REPO, "sim/core/dbcenums/effects.go")).read()
_AN = open(os.path.join(WS_REPO, "sim/core/dbcenums/auras.go")).read()
EFF_NUM = {k: int(v) for k, v in re.findall(r"^\s+(E_\w+)\s+SpellEffectType = (\d+)", _EN, re.M)}
AURA_NUM = {k: int(v) for k, v in re.findall(r"^\s+(A_\w+)\s+EffectAuraType = (\d+)", _AN, re.M)}
EFF_NAME = {v: k for k, v in EFF_NUM.items()}
AURA_NAME = {v: k for k, v in AURA_NUM.items()}

QT_COLS = CM["quest_template"]["cols"]


def quest_map(cid):
    """learned spell id -> vanilla quests that teach it (RewSpell / RewSpellCast, through effect 36)."""
    out = {}
    for r in CM["quest_template"]["rows"]:
        q = dict(zip(QT_COLS, r))
        if q["RequiredClasses"] and not (q["RequiredClasses"] & (1 << (cid - 1))):
            continue
        for sp in (q["RewSpell"], q["RewSpellCast"]):
            if not sp:
                continue
            for learned in TEACH.get(sp, {sp}):
                out.setdefault(learned, []).append({"quest": q["entry"], "title": q["Title"], "min_level": q["MinLevel"],
                                                    "required_races_mask": q["RequiredRaces"]})
    return out


REV = {}
for _r in S.values():
    for _ref in _r.get("RefIDs", []) or []:
        REV.setdefault(_ref, []).append(_r["ID"])
    for _e in _r.get("Effects", []):
        if _e.get("TriggerID"):
            REV.setdefault(_e["TriggerID"], []).append(_r["ID"])


def nm(x):
    return x.replace('dbcenums.', '') if isinstance(x, str) else x


def gain(e, L):
    lvl = L
    mx = e.get('MaxLevel', 0) or 0
    if 0 < mx < lvl:
        lvl = mx
    d = max(lvl - (e.get('BaseLevel', 0) or 0), 0)
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
        w = math.floor(exact(e, L))
        return w, w
    bp = f32(e.get('BasePoints', 0) or 0)
    side = f32(f32(f32(abs(bp)) * f32(V)) / 2)
    g = gain(e, L)
    lo = f32(f32(float(round(f32(bp - side)))) + g)
    hi = f32(f32(float(round(f32(bp + side)))) + g)
    return math.floor(lo), math.ceil(hi)


def effect_obj(r, e, learn, role):
    typ, aura = nm(e.get('Type')), nm(e.get('Aura'))
    bp, ppl = e.get('BasePoints', 0) or 0, e.get('PPL', 0) or 0
    o = {"index": e.get('Index', 0), "type": typ}
    if aura:
        o["aura"] = aura
    o["base_points"] = rnd(bp, 6)
    if ppl:
        o["points_per_level"] = rnd(f32(ppl), 6)
    o["scaling_base_level"] = e.get('BaseLevel', 0) or 0
    o["scaling_max_level"] = e.get('MaxLevel', 0) or 0
    if e.get('Variance'):
        o["variance"] = rnd(f32(e['Variance']), 6)
    weapon = typ in WEAPON_TYPES
    if weapon:
        o["weapon_effect"] = ("percent of weapon damage" if typ == 'E_WEAPON_PERCENT_DAMAGE' else
                              "flat damage added to a weapon hit (normalized speed)" if typ == 'E_NORMALIZED_WEAPON_DMG' else
                              "flat damage added to a weapon hit")
    elif e.get('SPCoef') is not None and (dmg_or_heal(e) or typ == 'E_DUMMY' or aura in ('A_SCHOOL_ABSORB', 'A_DUMMY')):
        o["sp_coef"] = rnd(f32(e['SPCoef']), 6)
        if r.get('School') == 1 and typ == 'E_SCHOOL_DAMAGE':
            o["sp_coef_note"] = "physical school damage: wowsims applies this as the coefficient on flat physical damage bonuses, not spell power (resolve_spell.go)"
    if e.get('APCoef'):
        o["ap_coef"] = rnd(f32(e['APCoef']), 6)
    if e.get('PeriodMs'):
        o["period_ms"] = e['PeriodMs']
        if r.get('DurationMs', 0) > 0:
            o["ticks"] = r['DurationMs'] // e['PeriodMs']
    for k_src, k_dst in (('TriggerID', 'trigger_spell'), ('ChainTargets', 'chain_targets'), ('Misc', 'misc'),
                         ('Misc2', 'misc2'), ('PointsPerResource', 'points_per_combo_point')):
        if e.get(k_src):
            o[k_dst] = e[k_src]
    if e.get('ChainTargets') and e.get('ChainAmp') not in (None, 1, 1.0):
        o["chain_amp"] = rnd(f32(e['ChainAmp']), 6)
    if e.get('RadiusMax'):
        o["radius_yd"] = rnd(e['RadiusMax'])
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
            o["note_scaling"] = f"keeps scaling past 60 (max_level {cap})"
    if e.get('Variance'):
        o["tooltip_range_at_learn_level"] = list(spread(e, lo_lvl))
        o["tooltip_range_at_60"] = list(spread(e, 60))
        if typ == 'E_HEAL' or (typ == 'E_SCHOOL_DAMAGE' and r.get('School') != 1):
            o["roll_rule"] = "whole amount (value + sp_coef*bonus) * uniform(1 - variance/2, 1 + variance/2)  [wowsims DirectVariance]"
        else:
            o["roll_rule"] = "base_points +- |base_points|*variance/2, rounded, plus level gain  [wowsims RollAt]"
    if role is None and 0 < learn < 20 and o.get("sp_coef") and r.get('School') != 1 and dmg_or_heal(e):
        f = 1 - (20 - learn) * 0.0375
        o["sp_coef_if_vanilla_sub20_penalty"] = {"value": rnd(o["sp_coef"] * f, 6), "factor": rnd(f, 6), "status": "vanilla",
                                                 "applied_by_wowsims_or_mythicsim": False}
    return o


def cost_obj(r):
    pw = r.get('Powers') or []
    if not pw:
        return {"mana": 0}
    c = {}
    for p in pw:
        t = p.get('Type', 0)
        name = POWER.get(t, f"power_{t}")
        if name == "combo_points":
            c["combo_points_min"] = p.get('Cost', 1)
            continue
        if p.get('Cost'):
            c[name] = p['Cost'] / 10 if name == "rage" else p['Cost']
        if p.get('CostPct'):
            c["pct_base_" + ("mana" if name == "mana" else name)] = rnd(f32(p['CostPct']))
        if p.get('PerSecond'):
            c[name + "_per_second"] = p['PerSecond']
        if "power_type" not in c:
            c["power_type"] = name
    if "power_type" not in c:
        c["power_type"] = POWER.get(pw[0].get('Type', 0))
    if c.get("power_type") == "rage":
        c["rage_note"] = "rage costs are stored x10 in the row; shown here in rage"
    return c


def vanilla_compare(i, learn, effects_forever):
    v = ST.get(i)
    if v is None:
        return {"in_vanilla_data": False, "note": "no row with this id in cmangos 1.12 spell_template: new or re-numbered in Forever"}
    out = {"in_vanilla_data": True, "vanilla_name": v["SpellName"], "vanilla_rank": v["Rank1"] or None,
           "vanilla_spell_level": v["SpellLevel"]}
    ch = []
    if v["SpellLevel"] != learn and v["SpellLevel"] != 0:
        ch.append(f"learn level {v['SpellLevel']} -> {learn}")
    r = S[str(i)]
    pw = (r.get('Powers') or [{}])[0]
    if v["PowerType"] == pw.get('Type', 0):
        if v["ManaCost"] and pw.get('Cost') and v["ManaCost"] != pw.get('Cost'):
            k = POWER.get(v["PowerType"])
            div = 10 if k == "rage" else 1
            ch.append(f"{k} cost {v['ManaCost'] / div:g} -> {pw['Cost'] / div:g}")
        if v["ManaCostPercentage"] and pw.get('CostPct') and v["ManaCostPercentage"] != round(pw['CostPct']):
            ch.append(f"cost {v['ManaCostPercentage']}% -> {rnd(pw['CostPct'])}% of base mana")
        if (v["ManaCost"] and not pw.get('Cost') and pw.get('CostPct')):
            ch.append(f"cost flat {v['ManaCost']} -> {rnd(pw['CostPct'])}% of base mana")
    for kv, kf in (("RecoveryTime", "CooldownMs"), ("CategoryRecoveryTime", "CategoryCooldownMs")):
        a, b = v[kv] or 0, r.get(kf, 0) or 0
        if a != b:
            ch.append(f"{'cooldown' if kv == 'RecoveryTime' else 'category cooldown'} {a / 1000:g} s -> {b / 1000:g} s")
    vfx = []
    for k in (1, 2, 3):
        if not v["Effect%d" % k]:
            continue
        bp, ds = v["EffectBasePoints%d" % k], v["EffectDieSides%d" % k]
        lo = bp + 1
        hi = bp + (ds if ds > 1 else 1)
        rpl = v["EffectRealPointsPerLevel%d" % k] or 0
        vfx.append({"index": k - 1, "effect": EFF_NAME.get(v["Effect%d" % k], v["Effect%d" % k]),
                    "aura": AURA_NAME.get(v["EffectApplyAuraName%d" % k], v["EffectApplyAuraName%d" % k]) if v["EffectApplyAuraName%d" % k] else None,
                    "range_at_base_level": [lo, hi], "points_per_level": rnd(rpl, 4), "trigger": v["EffectTriggerSpell%d" % k] or None})
        fe = next((e for e in effects_forever if e["index"] == k - 1), None)
        if fe is None:
            continue
        ve, va = v["Effect%d" % k], v["EffectApplyAuraName%d" % k]
        fe_e, fe_a = EFF_NUM.get(fe["type"]), AURA_NUM.get(fe.get("aura")) if fe.get("aura") else 0
        if ve != fe_e or (va or 0) != (fe_a or 0):
            ch.append(f"effect {k - 1} layout {EFF_NAME.get(ve, ve)}/{AURA_NAME.get(va, va) if va else '-'} -> {fe['type']}/{fe.get('aura') or '-'}")
            continue
        if bp == 0 and ds <= 1 and not rpl:
            continue
        rng = fe.get("tooltip_range_at_learn_level") or [fe["value_at_learn_level"], fe["value_at_learn_level"]]
        try:
            flo, fhi = float(rng[0]), float(rng[1])
        except (TypeError, ValueError):
            continue
        # compare at the rank's own base level: vanilla adds points per level from its base level too
        if (abs(flo - lo) > 1 or abs(fhi - hi) > 1) and not (abs(abs(flo) - abs(lo)) <= 1 and abs(abs(fhi) - abs(hi)) <= 1):
            ch.append(f"effect {k - 1} amount {lo}-{hi} -> {rng[0]}-{rng[1]} at learn level")
        if rpl and abs((fe.get("points_per_level") or 0) - rpl) > 1e-3:
            ch.append(f"effect {k - 1} points per level {rnd(rpl, 3)} -> {fe.get('points_per_level') or 0}")
    out["vanilla_effects"] = vfx
    out["changes_vs_vanilla"] = ch
    return out


def is_passive(r):
    a = r.get('Attr') or {}
    return bool(a.get('0', 0) & 0x40)


class Ctx:
    def __init__(self, cls):
        self.cls = cls
        self.cid = CLASS_IDS[cls]
        self.L = ladders(cls)
        self.trainer = trainer_map(self.cid)
        tree = json.load(open(os.path.join(WS_REPO, 'ui/sim/talents/trees', cls + '.json')))
        self.talents = {t['spellId']: {"tree": tr['name'], "row": t['location']['rowIdx'], "max_points": t['maxPoints'],
                                       "talent_name": t['fancyName']} for tr in tree for t in tr['talents']}
        self.code = code_index(cls)
        pc = CM["playercreateinfo_spell"]
        self.starting = {r[2] for r in pc["rows"] if r[1] == self.cid}
        self.quests = quest_map(self.cid)
        self.ladder_ids = {i for k, (kind, ids) in self.L.items() for i in (ids[:1] if kind == "Talent" else ids)}


def rank_obj(ctx, i, role=None):
    r = S.get(str(i))
    if r is None:
        return {"id": i, "status": None, "gap": "id named by the ladder or a reference is not in the wowsims spell store"}
    learn, base, mx = r.get('SpellLevel', 0), r.get('BaseLevel', 0), r.get('MaxLevel', 0)
    o = {"id": i, "name": r['Name']}
    if r.get('Rank'):
        o["rank"] = r['Rank']
    if role:
        o["role"] = role
    o["status"] = "forever"
    o["learn_level"] = learn
    o["base_level"] = base
    o["max_level"] = mx
    o["book_rank"] = i in BOOK
    if i in BOOK:
        o["book_item"] = BOOK[i]
    o["passive"] = is_passive(r)
    o["school"] = SCHOOL.get(r.get('School'), r.get('School'))
    for k_src, k_dst in [('CastTimeMs', 'cast_ms'), ('GCDMs', 'gcd_ms'), ('CooldownMs', 'cooldown_ms'),
                         ('CategoryCooldownMs', 'category_cooldown_ms'), ('Category', 'cooldown_category'),
                         ('DurationMs', 'duration_ms'), ('MaxRange', 'range_yd'), ('MinRange', 'min_range_yd'),
                         ('Speed', 'missile_speed'), ('MaxTargets', 'max_targets'), ('FlatThreat', 'flat_threat'),
                         ('MaxStack', 'max_stack'), ('StanceMask', 'required_stance_mask'), ('StanceExclude', 'excluded_stance_mask'),
                         ('Reagents', 'reagents')]:
        if r.get(k_src):
            o[k_dst] = rnd(r[k_src]) if isinstance(r[k_src], (int, float)) else r[k_src]
    o.setdefault('cast_ms', 0)
    o["cost"] = cost_obj(r)
    proc = {}
    for k_src, k_dst in [('ProcChance', 'chance_column'), ('ProcCharges', 'charges'), ('ICDMs', 'icd_ms'),
                         ('ProcChanceSource', 'chance_source'), ('RPPM', 'ppm'), ('ProcFlags', 'proc_flags')]:
        if r.get(k_src):
            proc[k_dst] = r[k_src] if not isinstance(r[k_src], str) else r[k_src].replace('ProcChance', '')
    if proc:
        o["proc"] = proc
    if r.get('RefIDs'):
        o["tooltip_refs"] = r['RefIDs']
    if r.get('_overrides'):
        o["wowsims_overrides"] = r['_overrides']
    o["effects"] = [effect_obj(r, e, learn, role) for e in r.get('Effects', [])]
    # how it is learned
    how = {}
    if i in BOOK:
        how["source"] = "book"
        how["item"] = BOOK[i]
    if i in ctx.talents:
        t = ctx.talents[i]
        how["source"] = "talent"
        how.update({"tree": t["tree"], "talent": t["talent_name"], "row_index": t["row"], "max_points": t["max_points"],
                    "earliest_level_vanilla_rule": 10 + 5 * t["row"]})
    if i in ctx.starting:
        how.setdefault("source", "starting spell")
        how["vanilla_starting_spell"] = True
    tr = ctx.trainer.get(i)
    if tr:
        how.setdefault("source", "trainer")
        how["vanilla_trainer"] = {"reqlevel": tr["reqlevel"], "cost_copper": tr["cost_copper"]}
    if ctx.quests.get(i):
        how.setdefault("source", "quest")
        how["vanilla_quests"] = ctx.quests[i][:4]
    parents = sorted({p for p in REV.get(i, []) if p != i and p in ctx.ladder_ids})
    if parents:
        how.setdefault("source", "triggered by another spell")
        how["triggered_or_referenced_by"] = [{"id": p, "name": S[str(p)]["Name"], "rank": S[str(p)].get("Rank")} for p in parents[:8]]
    if not how:
        how["source"] = ("unknown: not in vanilla 1.12 data, not a book rank wowsims lists, not a talent in the wowsims tree (new in Forever; trainer not confirmed)"
                         if str(i) and i not in ST else
                         "unknown: in vanilla 1.12 data but no vanilla trainer, quest, book or talent row teaches it")
    o["learned_from"] = how
    o["vanilla"] = vanilla_compare(i, learn, o["effects"])
    return o


# ---------------------------------------------------------------- wowsims code comments per ladder
def code_index(cls):
    files = [f for f in glob.glob(os.path.join(WS_REPO, "sim", cls, "**", "*.go"), recursive=True)
             if not f.endswith("_test.go") and not f.endswith("spell_data_auto_gen.go")]
    return {f: open(f).read().split("\n") for f in files}


def snake(key):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()


def code_notes(ctx, key, display):
    """Comments wowsims writes at the code that builds this ladder: the doc comment of each function or
    var that names spellData.<key>, kept when the function's name or the comment names the spell, plus the
    comment lines inside that function up to the reference."""
    pat = re.compile(r"spellData\.%s\b" % key)
    want = {key.lower(), display.lower().replace(" ", "").replace(":", "").replace("'", "")}
    out, seen = [], set()
    files = sorted(ctx.code, key=lambda f: (os.path.basename(f)[:-3] not in (snake(key), snake(key).split("_")[-1] + "s"), f))
    for f in files:
        lines = ctx.code[f]
        stem = os.path.basename(f)[:-3]
        sk = snake(key)
        own_file = stem == sk or stem == sk.split("_")[-1] + "s"
        if own_file:
            # the spell's own file: every comment in it, trailing ones with the code they sit on
            parts, coded = [], []
            for ln in lines:
                st = ln.strip()
                if st.startswith("//"):
                    parts.append(st[2:].strip())
                elif "//" in st and not st.startswith("\"") and "http" not in st.split("//")[0]:
                    code, _, com = st.partition("//")
                    coded.append(f"[{code.strip()[:90]}] {com.strip()}")
            # comments sitting on code (usually a number and where it came from) first
            text = " | ".join(c for c in coded if c) + (" || " if coded else "") + " ".join(p for p in parts if p)
            if text:
                seen.add(text)
                out.append({"file": os.path.relpath(f, WS_REPO), "comment": text[:2200], "scope": "whole file"})
            continue
        for idx, ln in enumerate(lines):
            if not pat.search(ln):
                continue
            j = idx
            while j > 0 and not re.match(r"^(func|var|const|type) ", lines[j]):
                j -= 1
            doc = []
            k = j - 1
            while k >= 0 and lines[k].startswith("//"):
                doc.insert(0, lines[k][2:].strip())
                k -= 1
            body = [x.strip()[2:].strip() for x in lines[j + 1: idx + 1] if x.strip().startswith("//")]
            text = " ".join(doc + body).strip()
            head = lines[j].lower().replace("_", "")
            squashed = text.lower().replace(" ", "").replace(":", "").replace("'", "")
            relevant = any(w in head for w in want) or any(w in squashed for w in want)
            if text and relevant and text not in seen:
                seen.add(text)
                out.append({"file": os.path.relpath(f, WS_REPO), "comment": text[:900]})
    return out[:4]


# ---------------------------------------------------------------- selection
SUFFIXES = ("Triggered", "Effect", "Bleed")


def base_of(key, L):
    for s in SUFFIXES:
        if key.endswith(s) and key[: -len(s)] in L:
            return key[: -len(s)]
    if key.endswith("2Triggered") and key[:-10] in L:
        return key[:-10]
    return None


def select(ctx):
    L = ctx.L
    util = FAM.COMMON_UTILITY | FAM.UTILITY.get(ctx.cls, set())
    pet = FAM.PET.get(ctx.cls, set())
    decision = {}

    def ids_of(k):
        kind, ids = L[k]
        return ids[:1] if kind == "Talent" else ids

    def passive_all(k):
        rows = [S.get(str(i)) for i in ids_of(k)]
        rows = [x for x in rows if x]
        return bool(rows) and all(is_passive(x) for x in rows)

    for k in L:
        if base_of(k, L):
            continue
        if k in pet:
            decision[k] = "pet ability: pets.json"
        elif k in util:
            decision[k] = "out-of-combat utility / crowd control / dispel"
        elif passive_all(k):
            decision[k] = "passive (talent, racial passive or class passive): talents are out of scope"
        else:
            decision[k] = "in"
    for k in L:
        b = base_of(k, L)
        if not b:
            continue
        if k in pet:
            decision[k] = "pet ability: pets.json"
        elif k in util:
            decision[k] = "out-of-combat utility / crowd control / dispel"
        elif decision.get(b) == "in":
            decision[k] = "in"
        else:
            decision[k] = f"triggered/effect ladder of {b}, which is excluded ({decision.get(b)})"
    return decision


def family(ctx, key):
    kind, ids = ctx.L[key]
    rank_ids = ids[:1] if kind == "Talent" else ids
    ranks = [rank_obj(ctx, i) for i in rank_ids]
    own = set(rank_ids)
    for rk in ranks:
        for ref in rk.get("tooltip_refs", []) or []:
            if ref in own or str(ref) not in S:
                continue
            rk.setdefault("linked", []).append(rank_obj(ctx, ref, "ref"))
    d = {"name": ranks[0].get("name") if ranks else key,
         "wowsims_ladder": f"spellData.{key} = spelldata.{kind}({', '.join(map(str, ids))})",
         "ranks": ranks}
    b = base_of(key, ctx.L)
    if b:
        d["triggered_or_effect_of"] = b
    if kind == "Talent":
        d["talent_ladder_note"] = f"spelldata.Talent(id, {ids[1] if len(ids) > 1 else '?'}): one spell whose effects scale with talent points; only the row is listed"
    notes = FAM.NOTES.get(ctx.cls, {}).get(key)
    if notes:
        d["notes"] = list(notes)
    cn = code_notes(ctx, key, d["name"] or key)
    if cn:
        d["wowsims_code_notes"] = cn
    changed = sorted({c for rk in ranks for c in rk["vanilla"].get("changes_vs_vanilla", [])})
    new = [rk["id"] for rk in ranks if not rk["vanilla"]["in_vanilla_data"]]
    d["forever_vs_vanilla_summary"] = {"ranks_not_in_vanilla_data": new, "rank_changes": {str(rk["id"]): rk["vanilla"]["changes_vs_vanilla"] for rk in ranks if rk["vanilla"].get("changes_vs_vanilla")}}
    return d


FOREVER_CLASS_NOTES = {
    "warrior": ["Rage (deep dive 1 Oct 2026, Warcraft Tavern summary): fully normalized on weapon speed; crits +75% rage (the client 'Rule of Rage' row and wowsims logs say +100%: client wins); rage from damage taken ignores armor. See warrior_levels.json meta.resources.",
                "New baseline: Victory Rush (20). Thunder Clap 6 s cooldown and AP scaling, usable in Defensive Stance. Recklessness/Retaliation/Shield Wall cooldowns split; Retaliation and Shield Wall 15 min.",
                "4 Nov notes: Defensive Stance threat 80% (was 30%); Slam cooldown 15 s."],
    "paladin": ["Holy Strike (6), Blessing of Kings and Consecration (20) baseline; Righteous Fury at 10; Judgement keeps the seal; Judgement debuffs 40 s; 5-minute blessings and Greater Blessings last 1 hour; Blessing of Might rank 7 133 AP; Seal of Fury new (Warcraft Tavern 21 Sep, 4 Nov notes).",
                "Removed in Forever: Blessing of Light, Blessing of Salvation, Greater Blessing of Salvation/Light, Revoke (4 Nov notes)."],
    "hunter": ["Aimed Shot baseline at 20; Arcane Shot and Aimed Shot cooldowns split, Multi-Shot shares Aimed Shot's; traps usable in combat, shared 30 s cooldown; Aspect of the Beast grants melee AP; Scorpid Sting -2% hit (Blizzard Hunter & Druid deep dive).",
               "2 Nov notes: Aimed Shot +110% bonus damage, Arcane Shot +30% and AP coefficient 0.15, Serpent Sting +20% and 5% AP per tick, Aspect of the Hawk 20/35/50/70/90/110 RAP, Trueshot Aura 20/35/50/75/100."],
    "rogue": ["Poisons: more charges, stack with stones; Deadly Poison AP coefficient 0.009, Instant Poison 0.01 (2 Nov notes). New: Shank (24, rank 2 44), Poised passive (18). One-handed axes usable. Feint threat doubled, Sap no longer breaks stealth, Expose Armor stronger (deep dive)."],
    "priest": ["Baseline for every Priest: Fear Ward and Devouring Plague (20), Divine Spirit (30), Shadow Word: Death (32). Renew stacks across priests; Prayer of Healing hits the target's party; Fade threat doubled (deep dive 1 Oct). Racial priest spells: Human Divine Grace (10) + Feedback, Dwarf Chastise (new) + Desperate Prayer, Gnome Confounding Flash (10) + Contingency Plan (20), Night Elf Elune's Grace + Starshards."],
    "mage": ["Frostfire Bolt baseline at 40; Mage Armor's spirit regen bonus increased; Cone of Cold shorter (deep dive 7 Oct). 2 Nov notes: Arcane Blast stack cost +100%; downrank penalty kept on Arcane Concentration, Frostbite and Fingers of Frost procs (rank learned 12+ levels below the caster)."],
    "warlock": ["Curse of Agony and Curse of Doom are Banes; Curse of the Elements covers all magic; Curse of Shadows removed; Life Tap scales with Spirit; demons scale from the warlock's stats (deep dive 7 Oct). 2 Nov notes: demon health 2 per point of warlock Stamina (was 7.5); Spellstone Shadow damage only; Drain Soul shard chance cut."],
    "druid": ["Nature's Grasp baseline (10), Revive (12), Omen of Clarity baseline (20), Lacerate baseline (42); forms keep weapon DPS (cat 1.0 s, bear 2.5 s), consumables and weapon enchants work in form; Tiger's Fury removed (deep dive).",
              "2 Nov notes: Bear threat 115%, Shred 200% / Claw 140% / Ravage 435% weapon damage, Rip/Rake/Bite/Pounce +25%, Starfire +40%, new Ferocious Bite rank 1 at 24, Poised at 32."],
    "shaman": ["See data/shaman_ranks.json notes (copied into the families it covers) and the Mage & Shaman deep dive: totems 1.0 s GCD, persistent totems 5 min, weapon imbues 60 min, Windfury and Flametongue totems are party buffs, Fire Nova Totem replaced by the Fire Nova spell, Totemic Recall, Call of the Elements/Spirits/Ancestors. 2 Nov notes: Lightning Bolt max rank +80%, Chain Lightning 2.5 s, shocks back to Classic Era base damage, Stormstrike 150% / 6 s."],
}


CLASS_GAPS = {
    "warlock": ["Dark Pact (vanilla Affliction talent) is not in the wowsims spell store or ladders; its Forever state is unknown.",
                "Felguard: the store has a 'Summon Felguard' row (427733, SpellLevel 10) but wowsims has no ladder, pet model or ability rows for it; no Forever numbers here.",
                "Incubus: Summon Incubus 713 is listed; wowsims models no Incubus (pets.json has none)."],
    "paladin": ["Blessing of Sanctuary (vanilla Protection talent) is not in the wowsims spell store; its Forever state is unknown. Crusader Strike / Divine Storm rows in the store are Season of Discovery rune ids (SpellLevel 1) with no Forever ladder and are left out."],
    "druid": ["Tiger's Fury: removed in Forever and replaced by the Shifting Power talent (Blizzard Hunter & Druid deep dive); no row."],
    "hunter": ["Pet abilities (Bite, Claw, Dash, Dive, family abilities, resistances, Great Stamina, Natural Armor) are in pets.json, not here."],
    "rogue": ["Poisons: the rows here are the weapon-imbue effects (the damage/debuff spells); vanilla taught poison crafting through the Poisons skill after a level 20 quest, so the vanilla trainer rows do not list these ids. The AP coefficients (0.009 Deadly, 0.01 Instant) are wowsims's ('Confirmed by Zirene'), not client columns."],
}


def build(cls):
    ctx = Ctx(cls)
    dec = select(ctx)
    out = {"meta": {}, "spells": {}}
    for key, d in dec.items():
        if d == "in":
            out["spells"][key] = family(ctx, key)
    n_ranks = sum(len(f["ranks"]) for f in out["spells"].values())
    out["meta"] = {
        "title": f"WoW Forever {cls.capitalize()} spell ranks, every level 1-60",
        "generated": GENERATED,
        "status_legend": {"forever": "Forever client data (build 1.60.1.70862) as carried by wowsims-forever", "vanilla": "Classic/vanilla fallback", "estimate": "derived or interpolated"},
        "source": {
            "repo": "data/repos/wowsims-forever", "commit": "125e534",
            "client_build": "1.60.1.70862",
            "rank_lists": f"sim/{cls}/spell_data_auto_gen.go (spelldata.Ranked / spelldata.Talent)",
            "records": "sim/core/spelldata/spells_auto_gen.go (wowsims's generator bakes in tools/database/overrides; any override comment is copied to the rank's wowsims_overrides: those fields are wowsims's in-game measurements, not client rows)",
            "book_ranks": "sim/core/spelldata/book_ranks.go",
            "talents": f"ui/sim/talents/trees/{cls}.json (talent spell ids and rows)",
            "vanilla": "cmangos classic-db spell_template (1.12) for vanilla_* fields, npc_trainer_template %d + npc_trainer rows of class %d trainers for vanilla_trainer (teach spell -> learned spell through effect 36 LEARN_SPELL)" % (CLASS_IDS[cls] * 10 + 1, CLASS_IDS[cls]),
        },
        "counts": {"families": len(out["spells"]), "ranks": n_ranks},
        "formulas": {
            "value_at_level": "BasePoints + PPL * clamp(min(L, scaling_max_level) - scaling_base_level, 0); scaling_max_level 0 = no cap. Computed in float32 as wowsims Effect.AverageAt. Damage/heal amounts keep the fraction; every other amount is floored.",
            "roll_heal_or_spell_damage": "(value + sp_coef * spell_power) * uniform(1 - variance/2, 1 + variance/2)",
            "ticks": "duration_ms // period_ms",
            "cost": "cost.mana flat; cost.pct_base_mana = pct of base mana (base_mana table in <class>_levels.json); cost.rage in rage (row value / 10); cost.energy; cost.combo_points_min = the finisher needs at least that many; cost.health (Life Tap row has none: wowsims spends amount + Spirit).",
            "learn_level": "SpellLevels.SpellLevel of the rank (client). learned_from.vanilla_trainer gives the vanilla 1.12 trainer level and cost for comparison. 2 Nov notes: training every class ability 1-60 costs 206-207 gold in Forever, so vanilla costs are not Forever costs.",
            "vanilla_compare": "vanilla.changes_vs_vanilla compares learn level, flat cost, cooldowns and each effect's amount at the learn level (vanilla BasePoints+1 .. BasePoints+DieSides, Forever tooltip range) with the 1.12 row of the same id. A difference of 1 point or less is ignored. Cast times and durations are not compared (the 1.12 rows store index ids into tables not in the local data).",
            "required_stance_mask": "client StanceMask bit field (1 << (form id - 1)); e.g. warrior Battle 17, Defensive 18, Berserker 19; druid Cat 1, Bear 5, Dire Bear 8, Moonkin 31.",
        },
        "coefficient_penalties": {
            "finding": "Neither wowsims-forever nor mythicsim-forever-engine applies the vanilla sub-20 penalty (1 - (20 - spellLevel)*0.0375) or a downrank coefficient penalty. Ranks learned below 20 carry sp_coef_if_vanilla_sub20_penalty so a sim can switch the vanilla rule on.",
            "forever_notes": "kami-labs summary of the 2 Nov 2026 notes: the low-rank penalty was removed from several chance-based talents and stays on Arcane Concentration, Frostbite and Fingers of Frost (proc less often when the rank was learned more than 12 levels below the caster). Nothing in the notes speaks to damage/heal coefficients of low ranks.",
        },
        "forever_class_notes": FOREVER_CLASS_NOTES.get(cls, []),
        "notes_sources": [
            "Warcraft Tavern summaries of Blizzard's Forever class deep dives: Priest & Warrior (1 Oct 2026, Blizzard news 24301514), Mage & Shaman (7 Oct, 24302097), Rogue & Warlock (7 Oct, 24310968); 'All Changes to Paladins' (21 Sep 2026); 'WoW Forever Pre-Launch Class Changes & Bug Fixes' (4 Nov 2026, from Kaivax's Beta Development Notes updated 2 Nov).",
            "Blizzard news 'World of Warcraft: Forever Class Deep Dives - Hunter and Druid' (news.blizzard.com/en-us/article/24301515).",
            "kami-labs 'WoW Forever November 2 patch: 223 changes before launch' (datamined items marked).",
            "The Blizzard forum dev-notes thread itself could not be fetched here (needs approval); its content is taken from the summaries above.",
            "Where a note and a client row disagree, the row wins; the row values are the ones in ranks[].",
        ],
        "excluded_ladders": {k: v for k, v in dec.items() if v != "in"},
        "gaps": [
            "Talents (passive) and talent procs are not included; talent-taught active abilities are (learned_from.source = talent).",
            "Cast times, durations, cooldowns and costs are the client rows as wowsims carries them; server-side scripts (e.g. Life Tap's Spirit term, Seal of Righteousness's per-swing damage formula) are only in wowsims_code_notes where wowsims states them.",
            "learned_from.vanilla_trainer is vanilla 1.12 data; Forever trainer levels are the client SpellLevel (learn_level), Forever costs are not in local data.",
            "Ranks not in vanilla data and not a talent or book carry learned_from.source 'unknown' unless the trainer data names them.",
        ] + CLASS_GAPS.get(cls, []),
    }
    return out


def merge_shaman(out):
    """Carry the hand-verified notes and special fields of data/shaman_ranks.json into the new file."""
    old = json.load(open(P("wowsim/data/shaman_ranks.json")))
    for key, fam in old["spells"].items():
        if key not in out["spells"]:
            continue
        new = out["spells"][key]
        if fam.get("notes"):
            new["notes"] = fam["notes"] + new.get("notes", [])
        for extra in ("shared_passive", "threat_proc_top_rank"):
            if extra in fam:
                new[extra] = fam[extra]
        if key == "Riptide":
            for rk in new["ranks"]:
                e0 = rk["effects"][0]
                e0["inert_in_forever"] = True
                e0["raw_note"] = "E_DUMMY: the initial heal was removed (2 Nov 2026 notes). base_points/points_per_level/sp_coef are the leftover row values; the heal is 0."
                e0["value_at_learn_level"] = 0
                e0["value_at_60"] = 0
                for k in ("values_by_level", "constant_from_level", "note_scaling", "tooltip_range_at_learn_level", "tooltip_range_at_60", "roll_rule"):
                    e0.pop(k, None)
    out["meta"]["shaman_file_merge"] = "Notes, Riptide's inert effect 0, Windfury/Flametongue shared passives and Rockbiter's threat proc are copied from data/shaman_ranks.json (gen_ranks.py) for the 19 families it covers; the other families are new here."
    out["meta"]["meta_from_data_shaman_ranks"] = {k: old["meta"][k] for k in ("talent_taught", "book_ranks_in_this_file", "forever_vs_vanilla_notes", "gaps") if k in old["meta"]}


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = {}
    for cls in CLASS_IDS:
        out = build(cls)
        if cls == "shaman":
            merge_shaman(out)
        json.dump(out, open(os.path.join(OUT, f"{cls}_ranks.json"), "w"), indent=1)
        summary[cls] = out["meta"]["counts"]
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
