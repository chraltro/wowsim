// What to do next, from one character export: gear upgrades by how you get them, quests to pick up, professions.
// Everything is computed with the same code and data the site uses: the Shaman Sim's engine (src/engine.js) scores gear,
// Craft Profits' core (src/crafts/core.js) prices recipes, and the item files in src/ say what exists and where it comes from.
(function (root) {
'use strict';

const RACE_BIT = { 'Human': 1, 'Orc': 2, 'Dwarf': 4, 'Night Elf': 8, 'Undead': 16, 'Tauren': 32, 'Gnome': 64, 'Troll': 128 };
const CLASS_BIT = { warrior: 1, paladin: 2, hunter: 4, rogue: 8, priest: 16, shaman: 64, mage: 128, warlock: 256, druid: 1024 };
const SLOT_LABEL = { head: 'Head', neck: 'Neck', shoulder: 'Shoulder', back: 'Back', chest: 'Chest', wrist: 'Wrist', hands: 'Hands', waist: 'Waist',
  legs: 'Legs', feet: 'Feet', finger1: 'Ring', finger2: 'Ring', trinket1: 'Trinket', trinket2: 'Trinket', mainhand: 'Main hand', offhand: 'Off hand', relic: 'Totem' };
const SLOTS = Object.keys(SLOT_LABEL);
const MAIL_AT = 40;              // Shamans learn Mail at 40 in Forever
const CUT = 0.95;                // the auction house keeps 5%
const GATHERING = { Herbalism: 1, Skinning: 1, Mining: 1 };
const STAT_LABEL = { int: 'Int', spi: 'Spi', sta: 'Sta', str: 'Str', agi: 'Agi', healing: 'Healing', spellDamage: 'Spell dmg', mp5: 'Mp5', critRating: 'Crit', hitRating: 'Hit', ap: 'AP', armor: 'Armor' };

function coins(c) {
  if (c == null || !isFinite(c)) return '?';
  let v = Math.round(Math.abs(c));
  const g = Math.floor(v / 10000); v -= g * 10000;
  const s = Math.floor(v / 100), k = v - s * 100;
  const p = [];
  if (g) p.push(g + 'g'); if (s) p.push(s + 's'); if (k || (!g && !s)) p.push(k + 'c');
  return (c < 0 ? '-' : '') + p.join(' ');
}
const pct = (v) => (v >= 0 ? '+' : '') + v.toFixed(1) + '%';
const statText = (it) => Object.entries(it.s || {}).filter(([k]) => STAT_LABEL[k]).map(([k, v]) => (k === 'armor' ? '' : '+') + v + ' ' + STAT_LABEL[k]).join(', ') +
  (it.w ? (it.s && Object.keys(it.s).length ? ', ' : '') + it.w.min + '-' + it.w.max + ' @ ' + it.w.speed : '');

// deps: { Engine, DATA, ITEMS, SETS, TALENT_META, Parse, MCGear, ITEMS_ALL, crafts: { core, D }, quests, prices }
//   quests: local/cache/quests.json or null.  prices: a parsed AHledger price table or null.
function makeAdvisor(deps) {
  const { Engine, DATA, SETS, TALENT_META, Parse } = deps;
  const talentByName = new Map((TALENT_META || []).map((t) => [t.name.toLowerCase(), t]));

  function report(ch, opts) {
    opts = opts || {};
    const notes = [...ch.warnings];
    const L = ch.level;
    const isShaman = ch.cls === 'shaman';

    // ---- prices: the export's own scan first (what is really listed right now), AHledger's scan for everything else
    const price = (id) => {
      if (ch.ah && ch.ah.prices.has(id)) { const p = ch.ah.prices.get(id); return { min: p.min, qty: p.qty, from: 'scan' }; }
      if (ch.ah && !ch.ah.gearOnly) return null;                 // a full scan that lacks the item: it is not listed
      const p = deps.prices && deps.prices.map.get(id);
      return p && p.min != null && p.qty > 0 ? { min: p.min, qty: p.qty, from: 'ahledger' } : null;
    };
    const priceSource = ch.ah ? 'your own scan of ' + ch.ah.time + (ch.ah.gearOnly ? ' (gear only, the rest from AHledger)' : '')
      : deps.prices ? 'AHledger\'s scan of ' + new Date(deps.prices.ts).toISOString().slice(0, 16).replace('T', ' ') + ' UTC' : null;
    if (!priceSource) notes.push('No auction prices: no scan in the export and AHledger could not be reached. Auction advice is left out.');

    // ---- items: the site's item file, plus anything in the export it does not know (read from its tooltip)
    const ITEMS = isShaman ? Object.create(deps.ITEMS) : Object.create(null);
    const known = (id) => (isShaman ? deps.ITEMS[id] : null);
    const learn = (x, slotKey) => {
      if (!x || !x.id || ITEMS[x.id]) return;
      const t = Parse.tooltipStats(x.lines);
      const kind = slotKey ? slotKey.replace(/[12]$/, '') : null;
      ITEMS[x.id] = { n: x.name, sl: kind, rl: x.req || 1, il: x.ilvl, s: t.s, w: t.w || undefined, two: t.two ? 1 : undefined, wt: t.wt || undefined, at: t.at || undefined, fromTooltip: true };
    };
    const gear = {};
    for (const k of SLOTS) if (ch.gear[k]) { learn(ch.gear[k], k); gear[k] = ch.gear[k].id; }
    const guessSlot = (x) => {
      const tags = x.tags.join(' ');
      const map = [['Two-Hand', 'mainhand'], ['One-Hand', 'mainhand'], ['Main Hand', 'mainhand'], ['Off Hand', 'offhand'], ['Held In Off-hand', 'offhand'],
        ['Head', 'head'], ['Neck', 'neck'], ['Shoulder', 'shoulder'], ['Back', 'back'], ['Chest', 'chest'], ['Wrist', 'wrist'], ['Hands', 'hands'],
        ['Waist', 'waist'], ['Legs', 'legs'], ['Feet', 'feet'], ['Finger', 'finger'], ['Trinket', 'trinket'], ['Relic', 'relic']];
      for (const [t, s] of map) if (tags.indexOf(t) >= 0) return s;
      return null;
    };
    const have = new Map();           // item id -> where it is
    const count = new Map();          // item id -> how many, bags and bank together
    for (const [where, list] of [['bags', ch.bags], ['bank', ch.bank]]) for (const x of list) {
      if (!have.has(x.id)) have.set(x.id, where);
      count.set(x.id, (count.get(x.id) || 0) + x.count);
      if (!known(x.id) && x.lines.length) { const sl = guessSlot(x); if (sl) learn(x, sl); }
    }
    for (const q of ch.quests) for (const x of q.choices) if (!known(x.id)) { const sl = guessSlot(x); if (sl) learn(x, sl); }

    // ---- scoring
    const talents = {};
    for (const [name, t] of Object.entries(ch.talents)) { const m = talentByName.get(name.toLowerCase()); if (m) talents[m.id] = t.rank; else if (isShaman) notes.push('Talent "' + name + '" is not in the sim and is ignored.'); }
    const needLvl = (it) => Math.max(it.rl || 1, it.at === 'Mail' && isShaman ? MAIL_AT : 1);
    const canWear = (it) => needLvl(it) <= L;
    const wearable = (g) => { const o = {}; for (const k in g) { const it = ITEMS[g[k]]; if (it && canWear(it)) o[k] = g[k]; } return o; };
    let makeScore, weights, scoreNote;
    if (isShaman) {
      const capO = { horizon: 300, mix: { HW: 0.7, CH: 0.3 }, chainEff: 0.8, healEff: 0.85, hstTargets: 3, hitsPerSec: 0.1, potions: true };
      const soloO = { mobDiff: 0, lightningShield: true };
      const tp = ch.talentPoints || {};
      const resto = (tp.Restoration || 0) >= Math.max(tp.Enhancement || 0, tp['Elemental Combat'] || 0, tp.Elemental || 0);
      weights = opts.mode === 'heal' ? [1, 0] : opts.mode === 'quest' ? [0, 1] : resto ? [0.5, 0.5] : [0.2, 0.8];
      const charFor = (g) => { const x = Engine.sumGear(wearable(g), ITEMS, SETS); return Engine.character({ level: L, gearStats: x.s, mh: x.mh, oh: x.oh, talents, buffs: {}, extra: {} }, DATA); };
      const raw = (g) => { const c = charFor(g); const solo = Engine.solo(c, DATA, soloO); return { heal: Engine.capacity(c, DATA, capO).total, quest: solo && solo.best ? solo.best.perHour : 0, style: solo && solo.best ? solo.best.name : null }; };
      const base = raw(gear);
      makeScore = (g0) => { const b = raw(g0); return (g) => { const r = raw(g); const h = b.heal ? (r.heal - b.heal) / b.heal * 100 : 0, q = b.quest ? (r.quest - b.quest) / b.quest * 100 : 0; return { v: weights[0] * h + weights[1] * q, h, q }; }; };
      scoreNote = 'Gear is scored by the Shaman Sim engine with your level, talents and worn gear: ' + Math.round(weights[0] * 100) + '% healing over a 5 minute fight, ' +
        Math.round(weights[1] * 100) + '% kills per hour while questing alone. Now: ' + Math.round(base.heal).toLocaleString('en-US') + ' healing, ' + Math.round(base.quest) + ' kills per hour' + (base.style ? ' (' + base.style.toLowerCase() + ')' : '') + '.';
    } else {
      // Other classes: the Group Sim's rough stat values per role. No engine run from here, so this is a ranking, not a sim.
      const G = deps.MCGear, styleOf = (G.STYLE_OF[ch.cls] || {});
      const style = G.STYLE[Object.values(styleOf)[0] || 'melee'];
      const val = (it) => { let v = 0; for (const k in it.s) v += (style[k] || 0) * it.s[k]; if (it.w) v += ((it.w.min + it.w.max) / 2 / it.w.speed) * (style.str ? 3 : style.agi ? 2.5 : 0.3) * (it.two ? 1.4 : 1); return v; };
      const total = (g) => Object.values(wearable(g)).reduce((t, id) => t + val(ITEMS[id]), 0);
      makeScore = (g0) => { const b = total(g0) || 1; return (g) => { const v = (total(g) - b) / b * 100; return { v, h: v, q: v }; }; };
      scoreNote = 'This class has no engine run from the command line yet, so gear is ranked by the Group Sim\'s rough stat values for the role. Use the Group Sim page for real numbers.';
      notes.push('Upgrade search for ' + ch.cls + ' only covers items in the export (bags, bank, quest rewards).');
    }

    // Gain from putting item id on, in its best slot, against the gear set ref.
    let ref = gear, scoreGear = makeScore(gear);
    const tryItem = (id) => {
      const it = ITEMS[id]; if (!it || !it.sl || !canWear(it)) return null;
      let best = null;
      for (const sk of SLOTS) {
        if (sk.replace(/[12]$/, '') !== it.sl || ref[sk] === +id) continue;
        if (sk === 'offhand' && ref.mainhand && ITEMS[ref.mainhand] && ITEMS[ref.mainhand].two) continue;
        const g = Object.assign({}, ref); g[sk] = +id;
        if (sk === 'mainhand' && it.two) delete g.offhand;
        const r = scoreGear(g); r.slot = sk; r.gear = g;
        if (!best || r.v > best.v) best = r;
      }
      return best;
    };
    const describe = (id, r) => {
      const it = ITEMS[id], cur = ITEMS[ref[r.slot]];
      return { id: +id, name: it.n, slot: SLOT_LABEL[r.slot], replaces: cur ? cur.n : null, stats: statText(it), healGain: r.h, questGain: r.q, value: r.v, fx: it.fx ? it.fx[0] : null };
    };

    const up = { own: [], rewards: [], ah: [], craft: [], quest: [], vendor: [], farm: [] };

    // 1. Already yours. Put the best one on, look again, until nothing in the bags or bank helps. Everything after this
    //    is compared with that set: a purchase has to beat what you would be wearing anyway.
    for (let round = 0; round < SLOTS.length; round++) {
      let best = null;
      for (const [id, where] of have) {
        if (Object.values(ref).indexOf(id) >= 0) continue;
        const r = tryItem(id);
        if (r && r.v > 0.05 && (!best || r.v > best.r.v)) best = { id, r, where };
      }
      if (!best) break;
      up.own.push(Object.assign(describe(best.id, best.r), { where: best.where }));
      ref = best.r.gear; scoreGear = makeScore(ref);
    }
    const afterOwn = up.own.length > 0;
    // 2. Reward choices of quests in the log
    for (const q of ch.quests) {
      if (!q.choices.length) continue;
      const rows = q.choices.map((x) => { const r = tryItem(x.id); return { x, r }; });
      const good = rows.filter((o) => o.r && o.r.v > 0.05).sort((a, b) => b.r.v - a.r.v);
      const sell = q.choices.slice().sort((a, b) => (b.vendor || 0) - (a.vendor || 0))[0];
      up.rewards.push({ quest: q.title, complete: q.complete, pick: good[0] ? describe(good[0].x.id, good[0].r) : null,
        others: good.slice(1).map((o) => describe(o.x.id, o.r)), cantWear: rows.filter((o) => !o.r).map((o) => o.x.name),
        vendorPick: !good[0] && sell && sell.vendor ? { name: sell.name, vendor: sell.vendor } : null });
    }

    // quests (computed before the wider gear search, which wants to know which reward quests are open)
    const quests = questAdvice(ch, notes);

    // The level you can realistically get an item at, as on the site: its requirement, the level of the quest or dungeon
    // it comes from, and item level minus 5 for items with neither.
    const srcLevel = (it) => { let lv = null; (it.src || []).forEach((s) => { const m = s.lv ? String(s.lv).match(/\d+/) : null; if (m && (lv === null || +m[0] < lv)) lv = +m[0]; }); return lv; };
    const reachLvl = (it) => { const sl = srcLevel(it); return Math.max(needLvl(it), sl || ((it.rl || 0) <= 1 ? Math.max(1, (it.il || 1) - 5) : 1)); };
    const inRef = new Set(Object.values(ref));
    const BUY_MIN = 0.5;             // a purchase or a trip has to add at least this much
    if (isShaman) {
      const openQuestNames = new Map(quests.open.map((q) => [q.name, q]));
      const myProfs = Object.keys(ch.skills);
      const craftsCtx = craftContext(ch, price, count);
      for (const id of Object.keys(deps.ITEMS)) {
        const it = ITEMS[id];
        if (inRef.has(+id) || have.has(+id) || !canWear(it) || reachLvl(it) > L + 2) continue;
        const p = price(+id);
        const src = it.src || [];
        const qsrc = src.filter((s) => s.t === 'quest' && openQuestNames.has(s.q));
        const csrc = src.filter((s) => s.t === 'crafted' && myProfs.indexOf(s.prof) >= 0);
        const vsrc = src.filter((s) => s.t === 'vendor');
        const fsrc = src.filter((s) => (s.t === 'npc' || s.t === 'dungeon') && s.p >= 10);
        if (!p && !qsrc.length && !csrc.length && !vsrc.length && !fsrc.length) continue;
        const r = tryItem(id);
        if (!r || r.v < BUY_MIN) continue;
        const d = describe(id, r);
        if (p) up.ah.push(Object.assign({}, d, { price: p.min, listed: p.qty, from: p.from, afford: p.min <= ch.gold, share: ch.gold ? p.min / ch.gold : null }));
        for (const s of qsrc) { const q = openQuestNames.get(s.q); up.quest.push(Object.assign({}, d, { quest: q.name, questLevel: q.lv, zone: q.zoneName, start: q.startText })); }
        for (const s of csrc) {
          const made = craftsCtx && craftsCtx.costOf(+id, s.prof);
          if (made && made.learn <= (ch.skills[s.prof] || {}).rank) up.craft.push(Object.assign({}, d, { prof: s.prof, skill: made.learn, cost: made.cost, mats: made.mats, held: made.held, recipe: made.name, known: made.known, pattern: made.pattern }));
        }
        if (vsrc.length) {
          const near = vsrc.find((s) => s.z && ch.zone && s.z.toLowerCase() === ch.zone.toLowerCase()) || vsrc[0];
          up.vendor.push(Object.assign({}, d, { npc: near.npc, zone: near.z, others: vsrc.length - 1, cost: craftsCtx ? craftsCtx.vendorBuy(+id) : null }));
        }
        if (!p && !qsrc.length && !csrc.length && !vsrc.length) for (const s of fsrc.slice(0, 1)) up.farm.push(Object.assign({}, d, { npc: s.npc, zone: s.z, chance: s.p, dungeon: s.t === 'dungeon', lv: s.lv }));
      }
    }
    // Rank: yours and rewards by gain, bought things by gain per coin spent, with what you cannot afford last.
    const byValue = (a, b) => b.value - a.value;
    up.own.sort(byValue);
    up.ah.sort((a, b) => (b.afford - a.afford) || (b.value / Math.max(100, b.price) - a.value / Math.max(100, a.price)));
    const blocked = (u) => (u.known === false && u.pattern ? 1 : 0);   // a pattern you do not own comes after what you can make today
    up.craft.sort((a, b) => (blocked(a) - blocked(b)) || (b.value / Math.max(100, b.cost == null ? 1e9 : b.cost) - a.value / Math.max(100, a.cost == null ? 1e9 : a.cost)));
    up.quest.sort(byValue); up.vendor.sort(byValue); up.farm.sort((a, b) => b.value * b.chance - a.value * a.chance);
    // The auction list answers "what is the best buy per slot", so keep the two best per slot.
    const perSlot = {}; up.ahAll = up.ah.length;
    up.ah = up.ah.filter((x) => { perSlot[x.slot] = (perSlot[x.slot] || 0) + 1; return perSlot[x.slot] <= 2; });
    const bestPerSlot = (list) => { const seen = {}; return list.filter((x) => { if (seen[x.slot + x.quest]) return false; seen[x.slot + x.quest] = 1; return true; }); };
    up.quest = bestPerSlot(up.quest);

    const professions = professionAdvice(ch, price, count, notes);
    const bags = bagAdvice(ch, price, professions, up);
    return { afterOwn, character: { name: ch.name, level: L, race: ch.race, cls: ch.cls, zone: ch.zone, subzone: ch.subzone, gold: ch.gold, exported: ch.exported, addon: ch.addon },
      scoreNote, weights, priceSource, upgrades: up, quests, professions, bags, notes };
  }

  // ---------------------------------------------------------------- quests
  function questAdvice(ch, notes) {
    const Q = deps.quests;
    const out = { open: [], soon: [], byZone: [], hasData: !!Q, total: 0 };
    if (!Q) { notes.push('No quest data on this machine. Run: python tools/fetch_quests.py (once), then check again.'); return out; }
    const L = ch.level;
    const raceBit = RACE_BIT[ch.race] || 0, classBit = CLASS_BIT[ch.cls] || 0;
    const inLog = new Set(ch.quests.map((q) => q.id).filter(Boolean));
    let done = ch.completed;
    if (!done) {
      // An export from an addon older than 1.4 has no list of finished quests. Work back from the log: whatever a quest
      // in the log needed first is done. That misses everything else, so the list below can name quests already done.
      done = new Set();
      const walk = (id) => { const q = Q.quests[id]; if (!q) return; for (const p of [].concat(q.pre || [], q.preAll || [])) if (!done.has(p)) { done.add(p); walk(p); } };
      inLog.forEach(walk);
      notes.push('This export has no list of finished quests (addon older than 1.4), so some quests named below may already be done. Update the addon.');
    }
    const zoneName = (z, q) => (z > 0 ? Q.zones[z] : Q.sorts && Q.sorts[z]) || (q && q.start && q.start.zone && Q.zones[q.start.zone]) || (z ? 'Zone ' + z : 'Unknown');
    const dungeons = new Set(Q.dungeons || []);
    const hereId = Object.keys(Q.zones).find((z) => Q.zones[z].toLowerCase() === String(ch.zone || '').toLowerCase());
    const nameCount = {};
    for (const [id, q] of Object.entries(Q.quests)) {
      const qid = +id;
      if (done.has(qid) || inLog.has(qid)) continue;
      if ((q.special || 0) & 1) continue;                               // repeatable
      if (q.min == null || q.min > L || q.lv == null || q.lv <= 0) continue;
      if (q.max && q.max < L) continue;
      if (q.lv < L - 5 || q.lv > L + 3) continue;                       // grey-ish below, too hard above
      if (q.races && raceBit && !(q.races & raceBit)) continue;         // JS keeps the low 32 bits, where the classic races are
      if (q.classes && classBit && !(q.classes & classBit)) continue;
      if (q.start && q.start.side && q.start.side.indexOf('A') < 0 && ch.faction === 'Alliance') continue;
      if (q.start && q.start.side && q.start.side.indexOf('H') < 0 && ch.faction === 'Horde') continue;
      if ((q.excl || []).some((x) => done.has(x) || inLog.has(x))) continue;
      if (q.skill && Array.isArray(q.skill)) continue;                  // profession quests: not judged here
      if (!q.start) continue;                                           // nobody known to give it
      if (q.z < 0 && !(q.classes && classBit && (q.classes & classBit))) continue; // class and profession categories, unless it is our class
      const pre = q.pre || [], preAll = q.preAll || [];
      const ok = (!pre.length || pre.some((p) => done.has(p))) && preAll.every((p) => done.has(p));
      const rec = { id: qid, name: q.n, lv: q.lv, min: q.min, zone: q.z, zoneName: q.z < 0 ? 'Class quests' : zoneName(q.z, q), dungeon: dungeons.has(q.z), cls: q.z < 0, xpClassic: q.xpClassic || null,
        startText: q.start.name ? q.start.name + (q.start.at && q.start.at[1] >= 0 ? ' (' + (Q.zones[q.start.at[0]] || 'zone ' + q.start.at[0]) + ' ' + q.start.at[1] + ', ' + q.start.at[2] + ')' : q.start.zone && Q.zones[q.start.zone] ? ' (' + Q.zones[q.start.zone] + ')' : '') + (q.start.t === 'item' ? ', an item that starts it' : q.start.t === 'object' ? ', an object' : '') : '?',
        startZone: q.start.at ? q.start.at[0] : q.start.zone, chain: !!q.next };
      if (ok) {
        const k = rec.name + '|' + rec.zone;                            // the database keeps several ids for one quest (race or faction versions)
        if (nameCount[k]) continue; nameCount[k] = 1;
        out.open.push(rec);
      } else {
        const waiting = [].concat(pre, preAll).filter((p) => inLog.has(p));
        if (waiting.length) { rec.after = waiting.map((p) => Q.quests[p] && Q.quests[p].n).filter(Boolean)[0]; out.soon.push(rec); }
      }
    }
    out.total = out.open.length;
    const groups = new Map();
    const logZones = new Set(ch.quests.map((q) => String(q.zone || '').toLowerCase()));
    for (const q of out.open) { const k = q.zoneName; if (!groups.has(k)) groups.set(k, { zone: k, id: q.zone, dungeon: q.dungeon, cls: q.cls, here: hereId != null && +hereId === q.zone, inLog: logZones.has(k.toLowerCase()), quests: [] }); groups.get(k).quests.push(q); }
    // Where you stand first, then class quests, zones you already have quests in, dungeons of your level, then the rest by size.
    const rank = (g) => (g.here ? 0 : g.cls ? 1 : g.inLog ? 2 : g.dungeon ? 3 : 4);
    out.byZone = [...groups.values()].map((g) => { g.quests.sort((a, b) => a.lv - b.lv || a.name.localeCompare(b.name)); return g; })
      .sort((a, b) => (rank(a) - rank(b)) || (b.quests.length - a.quests.length));
    return out;
  }

  // ---------------------------------------------------------------- professions
  function craftContext(ch, price, count) {
    const C = deps.crafts; if (!C) return null;
    const E = craftEngine();
    const pt = priceTable(ch);
    if (!pt) return null;
    const mine = {};
    C.D.profs.forEach((p, i) => { if (ch.skills[p]) mine[i] = ch.skills[p].rank; });
    const ctx = E.context(pt, { basis: 'min', sellTo: 'best', maxSkill: 300, trim: true, disc: 0, mine });
    return {
      E, ctx, pt, mine,
      costOf(id, profName) {
        const pi = C.D.profs.indexOf(profName); if (pi < 0) return null;
        const rs = (E.craftIndex[pi].get(id) || []).slice().sort((a, b) => a.learn - b.learn);
        if (!rs.length) return null;
        const r = rs[0], pl = ctx.plan(r, 1, new Map(count));   // what you hold is used first and costs nothing
        const kn = ch.recipes[profName];
        return { name: r.name, learn: r.learn, cost: pl.cost, known: kn ? kn.names.has(r.name) : null, pattern: r.src === 2,
          held: [...pl.used].map(([hid, q]) => q + ' ' + (E.items.get(hid) || ['item ' + hid])[0]).join(', '),
          mats: pl.buy.map((b) => b.q + ' ' + (E.items.get(b.id) || ['item ' + b.id])[0] + (b.src === 'vendor' ? ' (vendor)' : '')).join(', ') };
      },
      vendorBuy(id) { return ctx.vendorUnit(id); },
    };
  }
  let _engine = null;
  function craftEngine() { if (!_engine) _engine = deps.crafts.core.makeEngine(deps.crafts.D); return _engine; }
  // One price table for the crafts code: AHledger's scan with the export's own scan laid over it.
  function priceTable(ch) {
    const base = deps.prices;
    if (!base && !ch.ah) return null;
    const map = new Map(base ? base.map : []);
    if (ch.ah) for (const [id, p] of ch.ah.prices) { const b = map.get(id) || { med: p.min, m7: null, m30: null, lo: null, hi: null, sold: null }; map.set(id, Object.assign({}, b, { min: p.min, qty: p.qty, med: b.med == null ? p.min : b.med })); }
    return base ? Object.assign({}, base, { map }) : { market: 'forever/rppvp/alliance/eu', ts: Date.now(), map, game: 'forever', ruleset: 'rppvp', faction: 'alliance', region: 'eu' };
  }

  function professionAdvice(ch, price, count, notes) {
    const C = deps.crafts, out = [];
    if (!C) return out;
    const E = craftEngine();
    const cc = craftContext(ch, price, count);
    const nameOf = (id) => (E.items.get(id) || ['item ' + id])[0];
    C.D.profs.forEach((prof, pi) => {
      const sk = ch.skills[prof]; if (!sk) return;
      const p = { name: prof, skill: sk.rank, cap: sk.max, capped: sk.rank >= sk.max, gathering: !!GATHERING[prof], learnNow: [], soon: [], path: null, profit: [], snapshot: (ch.recipes[prof] || {}).snapshot || null };
      if (p.gathering) { out.push(p); return; }
      const kn = ch.recipes[prof];
      const mineRecipes = E.recipes.filter((r) => r.prof === pi);
      if (kn) {
        p.learnNow = mineRecipes.filter((r) => r.src !== 2 && r.learn <= sk.rank && !kn.names.has(r.name) && r.grey > sk.rank)
          .sort((a, b) => b.learn - a.learn).slice(0, 8).map((r) => ({ name: r.name, learn: r.learn, fee: r.fee, estimated: !!r.est }));
      }
      p.soon = mineRecipes.filter((r) => r.src !== 2 && r.learn > sk.rank && r.learn <= sk.rank + 15).sort((a, b) => a.learn - b.learn).slice(0, 6)
        .map((r) => ({ name: r.name, learn: r.learn, fee: r.fee }));
      if (cc) {
        const to = Math.min(sk.max, sk.rank + 25);
        if (to > sk.rank) {
          try {
            const P = E.levelPath(cc.pt, { basis: 'min', trim: true, disc: 0 }, pi, sk.rank, to, cc.mine, false);
            p.path = { from: P.from, to: P.to, net: P.net, mats: P.mats, fees: P.fees, back: P.back, gaps: P.gaps,
              steps: P.steps.map((s) => ({ name: s.r.name, from: s.from, to: s.to, crafts: s.n, mats: s.mats, fee: s.fee, known: kn ? kn.names.has(s.r.name) : null,
                sell: s.ah > 0 ? 'auction house' : 'vendor', back: s.back })),
              buy: P.buy.map((b) => ({ name: nameOf(b.id), q: Math.ceil(b.q - 1e-9), src: b.src, each: b.u, have: count.get(b.id) || 0 })),
              short: P.short.map((s) => ({ name: nameOf(s.id), need: Math.ceil(s.need), listed: s.listed })) };
          } catch (e) { notes.push('Leveling path for ' + prof + ' failed: ' + e.message); }
        }
        // What pays right now among recipes you can make. Expected profit, as on the Craft Profits page.
        const evals = mineRecipes.filter((r) => r.learn <= sk.rank && (!kn || kn.names.has(r.name) || r.src !== 2)).map((r) => cc.ctx.evalRecipe(r))
          .filter((e) => e.exp != null && e.exp > 0 && !(e.via === 'ah' && e.listed <= 2 && (!e.sale || e.sale.ref == null)));
        p.profit = evals.sort((a, b) => b.exp - a.exp).slice(0, 5).map((e) => ({ name: e.r.name, exp: e.exp, cost: e.c.cost, via: e.via, listed: e.listed, known: kn ? kn.names.has(e.r.name) : null }));
      }
      out.push(p);
    });
    // Professions the crafts data does not cover (Fishing, Enchanting's rods and so on) still get their cap line.
    for (const name of ['Fishing']) if (ch.skills[name]) out.push({ name, skill: ch.skills[name].rank, cap: ch.skills[name].max, capped: ch.skills[name].rank >= ch.skills[name].max, gathering: true, learnNow: [], soon: [], path: null, profit: [] });
    return out;
  }

  // ---------------------------------------------------------------- bags: keep, post or vendor
  function bagAdvice(ch, price, professions, up) {
    const keep = new Map();
    for (const p of professions) if (p.path) for (const b of p.path.buy) keep.set(b.name, p.name);
    const upgrades = new Set(up.own.map((u) => u.id));
    const rows = [];
    for (const x of ch.bags) {
      if (x.soulbound || upgrades.has(x.id) || !x.vendor) continue;      // no vendor price: quest item, hearthstone and the like
      const p = price(x.id);
      const post = p ? p.min * CUT : null;
      let verdict, why;
      if (keep.has(x.name)) { verdict = 'keep'; why = 'material for your next ' + keep.get(x.name) + ' points'; }
      else if (post != null && post > x.vendor * 1.25 && (post - x.vendor) * x.count >= 100) { verdict = 'post'; why = 'cheapest listing ' + coins(p.min) + ' each, ' + p.qty + ' listed; a vendor pays ' + coins(x.vendor); }
      else if (x.lines.length) { verdict = 'vendor'; why = 'gear you are not wearing' + (p ? ', and listings start at ' + coins(p.min) : ', none listed') + '; a vendor pays ' + coins(x.vendor); }
      else continue;
      rows.push({ name: x.name, count: x.count, verdict, why, value: verdict === 'post' ? post * x.count : x.vendor * x.count });
    }
    return rows.sort((a, b) => b.value - a.value);
  }

  return { report };
}

// ---------------------------------------------------------------- plain-text report
function render(R) {
  const o = [];
  const c = R.character;
  o.push('# ' + c.name + ', level ' + c.level + ' ' + c.race + ' ' + c.cls[0].toUpperCase() + c.cls.slice(1));
  o.push((c.zone ? c.zone + (c.subzone ? ' / ' + c.subzone : '') + ' · ' : '') + coins(c.gold) + ' · exported ' + (c.exported || '?') + (c.addon ? ' · addon ' + c.addon : ''));
  o.push('');
  o.push(R.scoreNote);
  if (R.priceSource) o.push('Auction prices: ' + R.priceSource + '.');
  const gain = (u) => R.weights && R.weights[0] && R.weights[1] ? pct(u.healGain) + ' healing, ' + pct(u.questGain) + ' questing' : pct(u.value);
  const item = (u) => u.name + ' (' + u.slot + (u.replaces ? ', replaces ' + u.replaces : ', empty slot') + '; ' + u.stats + ')';

  const U = R.upgrades;
  o.push('', '## Gear');
  if (U.own.length) { o.push('', 'Put on now, you already have it:'); U.own.forEach((u) => o.push('- ' + item(u) + ': ' + gain(u) + '. In your ' + u.where + '.')); }
  if (R.afterOwn) o.push('', 'Everything below is compared with your gear after those are on.');
  if (U.rewards.length) {
    o.push('', 'Quest rewards to choose:');
    U.rewards.forEach((r) => {
      if (r.pick) o.push('- ' + r.quest + (r.complete ? ' (ready to hand in)' : '') + ': take ' + item(r.pick) + ', ' + gain(r.pick) + '.' + (r.cantWear.length ? ' ' + r.cantWear.join(' and ') + (r.cantWear.length > 1 ? ' do' : ' does') + ' not fit your level or what you wield.' : ''));
      else o.push('- ' + r.quest + ': none of the choices beats what you wear.' + (r.vendorPick ? ' ' + r.vendorPick.name + ' sells for the most (' + coins(r.vendorPick.vendor) + ').' : ''));
    });
  }
  if (U.ah.length) {
    o.push('', 'On the auction house, best buys first (' + U.ahAll + ' listed items would be an upgrade):');
    U.ah.slice(0, 10).forEach((u) => o.push('- ' + item(u) + ': ' + gain(u) + ' for ' + coins(u.price) + (u.afford ? ' (' + Math.max(1, Math.round(u.share * 100)) + '% of your gold)' : ' (more than you have)') + ', ' + u.listed + ' listed.'));
  } else if (R.priceSource) o.push('', 'Nothing listed on the auction house beats your gear.');
  if (U.craft.length) { o.push('', 'Make yourself:'); U.craft.slice(0, 6).forEach((u) => o.push('- ' + item(u) + ': ' + gain(u) + '. ' + u.prof + ' ' + u.skill + (u.known === false ? (u.pattern ? ', needs a pattern you do not have' : ', learn it at the trainer first') : '') + ', ' + (u.cost != null ? (u.mats ? 'still to buy ' + coins(u.cost) + ' (' + u.mats + ')' : 'you hold every material') : 'materials not all for sale') + (u.held ? '; from your bags and bank: ' + u.held : '') + '.')); }
  if (U.quest.length) { o.push('', 'Rewards of quests you can pick up now:'); U.quest.slice(0, 8).forEach((u) => o.push('- ' + item(u) + ': ' + gain(u) + '. ' + u.quest + ' (level ' + u.questLevel + ', ' + u.zone + '), from ' + u.start + '.')); }
  if (U.vendor.length) { o.push('', 'Sold by vendors:'); U.vendor.slice(0, 5).forEach((u) => o.push('- ' + item(u) + ': ' + gain(u) + '. ' + (u.npc || 'Vendor') + (u.zone ? ', ' + u.zone : '') + (u.others ? ' (and ' + u.others + ' other vendor' + (u.others > 1 ? 's' : '') + ')' : '') + (u.cost ? ', ' + coins(u.cost) : '') + '.')); }
  if (U.farm.length) { o.push('', 'Drops worth knowing (10% chance or better):'); U.farm.slice(0, 5).forEach((u) => o.push('- ' + item(u) + ': ' + gain(u) + '. ' + u.npc + (u.zone ? ', ' + u.zone : '') + (u.lv ? ' (' + u.lv + ')' : '') + ', ' + u.chance + '%.')); }
  if (!U.own.length && !U.rewards.length && !U.ah.length && !U.craft.length && !U.quest.length && !U.vendor.length && !U.farm.length) o.push('', 'No upgrade found in any source.');

  const Q = R.quests;
  o.push('', '## Quests');
  if (!Q.hasData) o.push('', 'No quest data here yet. Run `python tools/fetch_quests.py` once.');
  else if (!Q.total) o.push('', 'No open quest found for your level that you have not done.');
  else {
    o.push('', Q.total + ' quests you can pick up now and have not done (quest level ' + Math.max(1, c.level - 5) + ' to ' + (c.level + 3) + '). XP is Classic\'s figure; Forever pays more for many quests.');
    const shown = Q.byZone.filter((g) => g.here || g.cls || g.inLog || g.dungeon).concat(Q.byZone.filter((g) => !(g.here || g.cls || g.inLog || g.dungeon)).slice(0, 4));
    shown.forEach((g) => {
      o.push('', '**' + g.zone + '**' + (g.here ? ' (you are here)' : g.dungeon ? ' (dungeon: collect these before going in)' : '') + ', ' + g.quests.length + ':');
      g.quests.slice(0, g.here ? 15 : 6).forEach((q) => o.push('- ' + q.name + ' (level ' + q.lv + (q.xpClassic ? ', ' + q.xpClassic + ' XP' : '') + (q.chain ? ', starts a chain' : '') + '): ' + q.startText));
      const more = g.quests.length - (g.here ? 15 : 6); if (more > 0) o.push('- and ' + more + ' more');
    });
    const rest = Q.byZone.filter((g) => shown.indexOf(g) < 0);
    if (rest.length) o.push('', 'Other zones with open quests: ' + rest.map((g) => g.zone + ' (' + g.quests.length + ')').join(', ') + '.');
    if (Q.soon.length) { o.push('', 'Open up when you finish a quest in your log:'); Q.soon.slice(0, 8).forEach((q) => o.push('- ' + q.name + ' (level ' + q.lv + ', ' + q.zoneName + ') after ' + q.after)); }
  }

  if (R.professions.length) {
    o.push('', '## Professions');
    for (const p of R.professions) {
      o.push('', '**' + p.name + ' ' + p.skill + '/' + p.cap + '**' + (p.capped ? ': at its cap. Train the next rank at a trainer before you lose points.' : p.cap - p.skill <= 10 ? ': ' + (p.cap - p.skill) + ' point' + (p.cap - p.skill === 1 ? '' : 's') + ' from its cap. Train the next rank soon.' : ''));
      if (p.learnNow.length) o.push('Learn at the trainer, you have the skill and not the recipe (recipe list from ' + p.snapshot + '): ' + p.learnNow.map((r) => r.name + ' (' + r.learn + (r.fee ? ', ' + coins(r.fee) : '') + ')').join(', ') + '.');
      else if (!p.gathering && !p.snapshot) o.push('Open the ' + p.name + ' window once with the addon loaded and export again: then this names the recipes you are missing.');
      if (p.path && p.path.steps.length) {
        o.push('Cheapest way from ' + p.path.from + ' to ' + p.path.to + ' at today\'s prices: materials ' + coins(p.path.mats) + (p.path.fees ? ', trainer ' + coins(p.path.fees) : '') + ', back from sales ' + coins(p.path.back) + ', net ' + (p.path.net <= 0 ? 'a gain of ' + coins(-p.path.net) : coins(p.path.net)) + '.');
        p.path.steps.forEach((s) => o.push('- ' + s.from + ' to ' + s.to + ': ' + s.crafts + ' x ' + s.name + (s.known === false ? ' (learn it first' + (s.fee ? ', ' + coins(s.fee) : '') + ')' : '') + ', then sell to the ' + s.sell + '.'));
        o.push('Shopping list: ' + p.path.buy.map((b) => b.q + ' ' + b.name + ' (' + (b.src === 'vendor' ? 'vendor' : 'auction house') + ', ' + coins(b.each) + ' each' + (b.have ? ', you hold ' + b.have : '') + ')').join('; ') + '.');
        if (p.path.short.length) o.push('Not enough listed today: ' + p.path.short.map((s) => s.name + ' (need ' + s.need + ', ' + s.listed + ' listed)').join(', ') + '.');
        if (p.path.gaps.length) o.push('No priced recipe gives points at ' + p.path.gaps.map((g) => g[0] + '-' + g[1]).join(', ') + '.');
      }
      if (p.soon.length) o.push('Next recipes at the trainer: ' + p.soon.map((r) => r.name + ' at ' + r.learn).join(', ') + '.');
      if (p.profit.length) o.push('Expected to pay now: ' + p.profit.map((e) => e.name + ' (' + coins(e.exp) + ' a craft, sold to the ' + (e.via === 'ah' ? 'auction house, ' + e.listed + ' listed' : 'vendor') + ')').join('; ') + '.');
      else if (!p.gathering && R.priceSource) o.push('Nothing you can make is expected to turn a profit at today\'s prices.');
    }
  }

  if (R.bags.length) {
    o.push('', '## Bags');
    for (const b of R.bags) o.push('- ' + b.name + (b.count > 1 ? ' x' + b.count : '') + ': ' + b.verdict + ' (' + b.why + ').');
  }
  if (R.notes.length) { o.push('', '## Notes'); R.notes.forEach((n) => o.push('- ' + n)); }
  return o.join('\n') + '\n';
}

const api = { makeAdvisor, render, coins };
if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.CheckAdvise = api;
})(typeof self !== 'undefined' ? self : this);
