// Pure pricing logic. No DOM. Shared by the page and the Node test.
const CUT = 0.95; // the faction auction house keeps 5% of a sale
const TRIM = 2; // with trimming on, a sale counts at most 2x the other houses in the region
const DEPOSIT = 0.6; // a 48-hour listing costs 60% of the vendor price (15% per 12 hours), lost when it expires
const POSTS = 3; // the expectation assumes up to three 48-hour listings, then selling to a vendor
const NO_DATA_TURN = 1 / 14; // without sales data an item counts as barely selling

// turn = units sold a day per unit listed. AHledger's four speeds: stock clears in under a day, 3 days, 14 days, or longer.
function speedBand(turn) {
  if (turn == null) return null;
  return turn >= 1 ? 'fast' : turn >= 1 / 3 ? 'steady' : turn >= 1 / 14 ? 'slow' : 'barely';
}
// Chance that one average listing sells within 48 hours.
function sellChance(turn) { return 1 - Math.exp(-2 * turn); }
// What one unit brings on average: posted for 48 hours up to three times, sold to a vendor after the third miss.
function expectedSale(net, vendor, turn) {
  const miss = Math.exp(-2 * turn);
  const never = Math.pow(miss, POSTS);
  let failed = 0;
  for (let k = 1; k <= POSTS; k++) failed += Math.pow(miss, k);
  return (1 - never) * net + never * vendor - DEPOSIT * vendor * failed;
}

function parsePriceTable(text) {
  const lines = String(text || '').trim().split(/\r?\n/);
  const head = (lines[0] || '').trim().split('|');
  if (head[0] !== 'AHL1' || !head[1] || head[1].split('/').length !== 4) {
    throw new Error('That text is not an AHledger price table. It should start with AHL1|forever/…');
  }
  const num = (x) => (x === undefined || x === '' ? null : Number(x));
  const map = new Map();
  for (let i = 1; i < lines.length; i++) {
    const f = lines[i].trim().split(':');
    if (f.length < 4) continue;
    const id = Number(f[0]);
    if (!id) continue;
    map.set(id, {
      med: num(f[1]), min: num(f[2]), qty: num(f[3]) || 0,
      m7: num(f[4]), m30: num(f[5]), lo: num(f[6]), hi: num(f[7]),
      sold: f[8] !== undefined && f[8] !== '' ? Number(f[8]) / 10 : null,
    });
  }
  if (!map.size) throw new Error('The price table has a header but no item rows. Copy the whole page.');
  const [game, ruleset, faction, region] = head[1].split('/');
  return { market: head[1], ts: Number(head[2]) * 1000, map, game, ruleset, faction, region };
}

function marketLabel(pt) {
  const rs = { normal: 'Normal', pvp: 'PvP', rp: 'RP', rppvp: 'RP-PvP' }[pt.ruleset] || pt.ruleset;
  const fa = pt.faction ? pt.faction[0].toUpperCase() + pt.faction.slice(1) : '';
  return `${rs} ${fa} ${String(pt.region || '').toUpperCase()}`.trim();
}

// Build the engine once per dataset. opts: { basis: 'med'|'min', sellTo: 'ah'|'vendor'|'best', maxSkill }
function makeEngine(D) {
  const items = new Map(Object.entries(D.I).map(([k, v]) => [Number(k), v]));
  const recipes = D.R.map((r) => {
    const reag = [];
    for (let i = 0; i < r[11].length; i += 2) reag.push([r[11][i], r[11][i + 1]]);
    const res = items.get(r[8]);
    return {
      sid: r[0], name: r[1] || (res ? res[0] : `Item ${r[8]}`), prof: r[2], learn: r[3],
      yellow: r[4], grey: r[5], src: r[6], ritem: r[7], res: r[8], qmin: r[9], qmax: r[10], reag,
      est: r[12] ? 1 : 0, fee: r[13] || 0,
    };
  });
  const craftIndex = D.profs.map(() => new Map());
  const isReagent = new Set();
  for (const r of recipes) {
    const m = craftIndex[r.prof];
    if (!m.has(r.res)) m.set(r.res, []);
    m.get(r.res).push(r);
    for (const [id] of r.reag) isReagent.add(id);
  }

  function context(pt, opts) {
    const facBit = pt.faction === 'horde' ? 2 : 1;
    const memo = new Map();
    const refs = (D.ref && D.ref[pt.region]) || {};
    const turns = (D.turn && D.turn[pt.region]) || {};
    // How fast an item sells: this house's own estimate when the scan has one, otherwise the region's other houses.
    const turnOf = (id) => {
      const p = pt.map.get(id);
      if (p && p.sold != null && p.qty > 0) return { t: p.sold / p.qty, own: true };
      const t = turns[id];
      return t == null ? null : { t, own: false };
    };
    // Which recipes may supply a material: opts.mine (profession -> skill) when set, else the recipe's own profession.
    const mine = opts.mine || null;
    const usable = (r) => !(opts.trainerMats && r.src === 2); // trainerMats: materials only from recipes a trainer teaches
    const makers = (id, prof) => {
      const out = [];
      if (mine) {
        for (const k of Object.keys(mine)) for (const r of craftIndex[k].get(id) || []) if (r.learn <= mine[k] && usable(r)) out.push(r);
      } else {
        for (const r of craftIndex[prof].get(id) || []) if (r.learn <= opts.maxSkill && usable(r)) out.push(r);
      }
      return out;
    };
    const ahUnit = (id) => {
      const p = pt.map.get(id);
      if (!p) return null;
      const v = opts.basis === 'min' ? (p.min ?? p.med) : (p.med ?? p.min);
      return v == null ? null : v;
    };
    // What a sale is counted at: the house price, cut down to TRIM x the other houses when trimming is on.
    const saleUnit = (id) => {
      const raw = ahUnit(id);
      if (raw == null) return { u: null, raw: null, ref: null, trimmed: false };
      const ref = refs[id] ?? null;
      if (opts.trim && ref != null && raw > ref * TRIM) return { u: ref * TRIM, raw, ref, trimmed: true };
      return { u: raw, raw, ref, trimmed: false };
    };
    const disc = Math.min(Math.max(Number(opts.disc) || 0, 0), 0.5); // reputation discount on vendor purchases
    const vendorUnit = (id) => {
      const it = items.get(id);
      if (!it || !it[3] || !(it[4] & facBit)) return null;
      return it[3] * (1 - disc);
    };
    function reagentUnit(id, prof, stack) {
      const key = mine ? id : id + '|' + prof;
      if (memo.has(key)) return memo.get(key);
      let best = null;
      const v = vendorUnit(id);
      if (v != null) best = { u: v, src: 'vendor' };
      const a = ahUnit(id);
      if (a != null && (!best || a < best.u)) best = { u: a, src: 'ah' };
      let partial = false;
      if (stack.length < 3) {
        for (const r of makers(id, prof)) {
          if (stack.includes(r.sid)) { partial = true; continue; }
          const c = recipeCost(r, [...stack, r.sid]);
          if (c.cost == null) continue;
          const u = c.cost / ((r.qmin + r.qmax) / 2);
          if (!best || u < best.u) best = { u, src: 'craft', via: r };
        }
      } else partial = true;
      if (!partial) memo.set(key, best);
      return best;
    }
    function recipeCost(r, stack) {
      let cost = 0;
      const missing = [];
      const parts = [];
      for (const [id, q] of r.reag) {
        const b = reagentUnit(id, r.prof, stack);
        if (!b) { missing.push(id); parts.push({ id, q, u: null, src: null }); }
        else { cost += b.u * q; parts.push({ id, q, u: b.u, src: b.src, via: b.via }); }
      }
      return { cost: missing.length ? null : cost, missing, parts };
    }
    function evalRecipe(r) {
      const c = recipeCost(r, [r.sid]);
      const y = (r.qmin + r.qmax) / 2;
      const it = items.get(r.res);
      const sell = it ? it[2] : 0;
      const bop = it ? it[6] : 0;
      const sale = bop ? { u: null, raw: null, ref: null, trimmed: false } : saleUnit(r.res);
      const a = sale.u;
      const ahNet = a != null ? a * y * CUT : null;
      const vend = sell * y;
      const tn = a != null ? turnOf(r.res) : null;
      const turn = tn ? tn.t : NO_DATA_TURN;
      const ahExp = a != null ? expectedSale(a * CUT, sell, turn) * y : null;
      let value = null; let via = null; let expValue = null;
      if (opts.sellTo === 'ah') { value = ahNet; expValue = ahExp; via = 'ah'; }
      else if (opts.sellTo === 'vendor') { value = vend > 0 ? vend : null; expValue = value; via = 'vendor'; }
      else if (ahExp != null && ahExp >= vend) { value = ahNet; expValue = ahExp; via = 'ah'; }
      else if (vend > 0) { value = vend; expValue = vend; via = 'vendor'; }
      const profit = c.cost != null && value != null ? value - c.cost : null;
      const exp = c.cost != null && expValue != null ? expValue - c.cost : null;
      const p = pt.map.get(r.res);
      return {
        r, c, y, a, ahNet, vend, value, via, profit, exp, bop, sale,
        turn: via === 'ah' && tn ? tn.t : null, ownTurn: !!(tn && tn.own), band: via === 'ah' ? speedBand(tn ? tn.t : null) : null,
        chance: via === 'ah' ? sellChance(turn) : 1, deposit: DEPOSIT * sell * y,
        margin: profit != null && c.cost > 0 ? profit / c.cost : null,
        listed: p ? p.qty : 0, sold: p ? p.sold : null,
        trend: p && p.med != null && p.m7 ? (p.med - p.m7) / p.m7 : null,
        perDay: profit != null && p && p.sold != null ? profit * p.sold : null,
      };
    }
    // Buy below vendor price on the AH, sell to a vendor.
    function ahToVendor() {
      const out = [];
      for (const [id, p] of pt.map) {
        const it = items.get(id);
        if (!it || p.min == null) continue;
        const sell = it[2];
        if (sell > p.min) out.push({ id, buy: p.min, med: p.med, sell, profit: sell - p.min, qty: p.qty });
      }
      return out.sort((a, b) => b.profit - a.profit);
    }
    // Buy from a vendor, sell on the AH.
    function vendorToAh() {
      const out = [];
      for (const [id, it] of items) {
        const v = vendorUnit(id);
        if (v == null) continue;
        const s = saleUnit(id);
        if (s.u == null) continue;
        const net = s.u * CUT;
        if (net - v > 0.5) {
          const p = pt.map.get(id);
          const tn = turnOf(id);
          const exp = expectedSale(net, it[2], tn ? tn.t : NO_DATA_TURN) - v;
          out.push({ id, vendor: v, ah: s.u, raw: s.raw, trimmed: s.trimmed, net, profit: net - v, exp, band: speedBand(tn ? tn.t : null), qty: p.qty, limited: !!it[5], thin: p.qty <= 2 && s.ref == null });
        }
      }
      return out.sort((a, b) => b.exp - a.exp);
    }
    // Buy materials, craft, sell the result to a vendor.
    function craftToVendor() {
      const out = [];
      for (const r of recipes) {
        if (r.learn > opts.maxSkill) continue;
        const it = items.get(r.res);
        if (!it || !it[2]) continue;
        const c = recipeCost(r, [r.sid]);
        if (c.cost == null) continue;
        const y = (r.qmin + r.qmax) / 2;
        const vend = it[2] * y;
        if (vend - c.cost >= 1) out.push(evalRecipe(r));
      }
      return out.filter((e) => e.profit != null && e.profit >= 1).sort((a, b) => b.profit - a.profit);
    }
    // Everything to buy and every craft to make first for n crafts of r, with crafted materials expanded.
    // own: Map of item -> count already in the bags. Those are used first and taken out of the map.
    function plan(r, n, own) {
      const buy = new Map();
      const steps = new Map();
      const used = new Map();
      let ok = true;
      const add = (id, q, src, u) => {
        const k = id + '|' + src;
        const cur = buy.get(k);
        if (cur) cur.q += q; else buy.set(k, { id, q, src, u });
      };
      (function walk(rec, crafts, stack) {
        for (const [id, q] of rec.reag) {
          let need = q * crafts;
          const mineNow = own ? own.get(id) || 0 : 0;
          if (mineNow > 0) {
            const take = Math.min(mineNow, need);
            own.set(id, mineNow - take); used.set(id, (used.get(id) || 0) + take); need -= take;
            if (need <= 0) continue;
          }
          const b = reagentUnit(id, rec.prof, stack);
          if (!b) { ok = false; add(id, need, null, null); continue; }
          if (b.src !== 'craft') { add(id, need, b.src, b.u); continue; }
          const sub = Math.ceil(need / ((b.via.qmin + b.via.qmax) / 2) - 1e-9);
          walk(b.via, sub, [...stack, b.via.sid]);
          const st = steps.get(b.via.sid);
          if (st) st.n += sub; else steps.set(b.via.sid, { r: b.via, n: sub });
        }
      })(r, n, [r.sid]);
      const list = [...buy.values()];
      let stock = Infinity;
      for (const b of list) {
        if (b.src !== 'ah') continue;
        const listed = (pt.map.get(b.id) || {}).qty || 0;
        stock = Math.min(stock, Math.floor(listed / (b.q / n)));
      }
      return { buy: list, steps: [...steps.values()], cost: ok ? list.reduce((t, b) => t + b.u * b.q, 0) : null, stock, used };
    }
    // Skill ranges where a trainer recipe is one of the two cheapest skill-ups of its profession: levelers keep making it.
    const fodderMemo = new Map();
    function fodder(r) {
      if (!fodderMemo.has(r.prof)) {
        const ranges = new Map();
        const pool = recipes.filter((x) => x.prof === r.prof && x.src !== 2 && x.yellow && x.grey).map((x) => ({ x, cost: recipeCost(x, [x.sid]).cost }));
        for (let s = 5; s <= 295; s += 5) {
          const cand = [];
          for (const c of pool) {
            if (c.cost == null || c.x.learn > s) continue;
            const ch = skillChance(c.x, s);
            if (ch > 0) cand.push([c.cost / ch, c.x.sid]);
          }
          cand.sort((a, b) => a[0] - b[0]);
          for (const [, sid] of cand.slice(0, 2)) {
            const g = ranges.get(sid);
            if (g) g[1] = s; else ranges.set(sid, [s, s]);
          }
        }
        fodderMemo.set(r.prof, ranges);
      }
      return fodderMemo.get(r.prof).get(r.sid) || null;
    }
    // Waylaid Crates: the empty crate's price here, the cheapest way to fill it, and what a Merchant's Favor costs that way.
    function crates() {
      return (D.crates || []).map(([id, tier, level, favor, flat]) => {
        const fills = [];
        for (let i = 0; i < flat.length; i += 2) {
          const fid = flat[i], q = flat[i + 1];
          const vu = vendorUnit(fid), au = ahUnit(fid);
          const buyU = [vu, au].filter((x) => x != null).sort((a, b) => a - b)[0];
          const b = reagentUnit(fid, 0, []);
          fills.push({ id: fid, q, buy: buyU != null ? buyU * q : null, listed: (pt.map.get(fid) || {}).qty || 0, vendor: vu != null && buyU === vu,
            craft: b && b.src === 'craft' ? b.u * q : null, via: b && b.src === 'craft' ? b.via : null });
        }
        const priced = fills.filter((f) => f.buy != null).sort((a, b) => a.buy - b.buy);
        const best = priced[0] || null;
        const p = pt.map.get(id);
        const crate = p ? (opts.basis === 'min' ? (p.min ?? p.med) : (p.med ?? p.min)) : null;
        const total = best && crate != null ? best.buy + crate : null;
        return { id, tier, level, favor, fills, best, crate, listed: p ? p.qty : 0, total, perFavor: total != null && favor ? total / favor : null };
      });
    }
    // What an amount of Merchant's Favor costs here: the cheapest crates per favor first, as many as are listed.
    function favor(need) {
      const cs = crates().filter((c) => c.perFavor != null).sort((a, b) => a.perFavor - b.perFavor);
      let left = need, cost = 0;
      const used = [];
      for (const c of cs) {
        if (left <= 0) break;
        const can = Math.min(c.listed, c.best.vendor ? Infinity : Math.floor(c.best.listed / c.best.q));
        const n = Math.min(can, Math.ceil(left / c.favor));
        if (n < 1) continue;
        cost += n * c.total; left -= n * c.favor; used.push({ c, n });
      }
      return left > 0 ? null : { cost, used };
    }
    // Price of trade materials against their 7-day median, grouped by item level in tens. The middle item of each group.
    function trend() {
      const groups = [];
      for (const [id, p] of pt.map) {
        const it = items.get(id);
        if (!it || it[7] !== 7 || !p.med || !p.m7) continue;
        const b = Math.min(5, Math.max(0, Math.floor((it[8] - 1) / 10)));
        (groups[b] = groups[b] || []).push(p.med / p.m7 - 1);
      }
      const rows = [];
      for (let b = 0; b < 6; b++) {
        const g = (groups[b] || []).sort((x, y) => x - y);
        rows.push({ lo: b * 10 + 1, hi: b * 10 + 10, n: g.length, chg: g.length >= 5 ? g[Math.floor(g.length / 2)] : null });
      }
      return rows;
    }
    return { evalRecipe, ahToVendor, vendorToAh, craftToVendor, plan, fodder, crates, favor, trend, turnOf, ahUnit, saleUnit, vendorUnit };
  }
  // A one-off asking price nobody else backs up is no plan.
  const thinSale = (e) => e.via === 'ah' && e.listed <= 2 && (!e.sale || e.sale.ref == null);
  // One batch of crafts: a quarter of what is already listed when it goes to the auction house, 20 for a vendor.
  const batchCap = (e) => (e.via === 'vendor' ? 20 : Math.max(1, Math.floor(e.listed * 0.25 / e.y)));
  // What to do with a gold budget: sure auction-to-vendor flips and crafts in your professions, best return per gold first.
  // mine: { professionIndex: skill }. Crafts taught by a recipe item are left out unless withRecipes is set.
  function spend(pt, opts, mine, budget, withRecipes) {
    const ctx = context(pt, Object.assign({}, opts, { sellTo: 'best', mine, maxSkill: 300 }));
    const cands = [];
    for (const x of ctx.ahToVendor()) cands.push({ kind: 'buyVendor', id: x.id, cost: x.buy, gain: x.profit, cap: 1, sure: true, sell: x.sell });
    for (const r of recipes) {
      if (mine[r.prof] == null || r.learn > mine[r.prof] || (r.src === 2 && !withRecipes)) continue;
      const e = ctx.evalRecipe(r);
      if (e.exp == null || e.exp <= 0 || !(e.c.cost > 0)) continue;
      if (thinSale(e)) continue;
      cands.push({ kind: 'craft', e, cost: e.c.cost, gain: e.exp, cap: batchCap(e), sure: e.via === 'vendor', needs: ctx.plan(r, 1).buy });
    }
    cands.sort((a, b) => b.gain / b.cost - a.gain / a.cost);
    const minLine = Math.max(50, budget * 0.01);
    const used = new Map();
    const lines = [];
    let left = budget;
    for (const c of cands) {
      let n = Math.min(c.cap, Math.floor(left / c.cost));
      if (c.needs) {
        for (const b of c.needs) {
          if (b.src !== 'ah') continue;
          const free = ((pt.map.get(b.id) || {}).qty || 0) - (used.get(b.id) || 0);
          n = Math.min(n, Math.floor(free / b.q));
        }
      }
      if (n < 1 || n * c.gain < minLine) continue;
      if (c.needs) for (const b of c.needs) if (b.src === 'ah') used.set(b.id, (used.get(b.id) || 0) + b.q * n);
      left -= n * c.cost;
      lines.push(Object.assign({ n }, c));
    }
    lines.sort((a, b) => b.n * b.gain - a.n * a.gain);
    const sum = (f) => lines.reduce((t, l) => t + f(l), 0);
    return { ctx, lines, spent: budget - left, gain: sum((l) => l.n * l.gain), sure: sum((l) => (l.sure ? l.n * l.gain : 0)), minLine };
  }

  // Recipe items and what buying one is worth: its price here against the expected gain of a first batch of crafts.
  // Each row: the ways to get the recipe (auction house, vendor, Merchant's Favor through crates), the cheapest of
  // them, the batch size, and what is left after the batch has paid for the recipe.
  function recipeBuys(pt, opts) {
    const base = Object.assign({}, opts, { sellTo: 'best', mine: null });
    const byLearn = new Map();
    const ctxFor = (skill) => {
      if (!byLearn.has(skill)) byLearn.set(skill, context(pt, Object.assign({}, base, { maxSkill: skill })));
      return byLearn.get(skill);
    };
    const any = ctxFor(300);
    const favorMemo = new Map();
    const favorCost = (n) => { if (!favorMemo.has(n)) favorMemo.set(n, any.favor(n)); return favorMemo.get(n); };
    const rows = [];
    for (const r of recipes) {
      if (r.src !== 2 || !r.ritem) continue;
      const ctx = ctxFor(r.learn); // materials from this profession's recipes up to the skill the recipe itself needs
      const e = ctx.evalRecipe(r);
      if (e.exp == null) continue;
      const it = items.get(r.ritem), p = pt.map.get(r.ritem);
      const ways = [];
      if (p && p.min != null) ways.push({ src: 'ah', price: p.min, listed: p.qty });
      const vu = ctx.vendorUnit(r.ritem);
      if (vu != null) ways.push({ src: 'vendor', price: vu, limited: !!(it && it[5]) });
      const fv = D.fav && D.fav[r.ritem];
      if (fv) {
        const f = favorCost(fv[0]);
        ways.push({ src: 'favor', price: f ? f.cost : null, favor: fv[0], honored: !!fv[1], crates: f ? f.used : null });
      }
      const way = ways.filter((w) => w.price != null).sort((a, b) => a.price - b.price)[0] || null;
      const cap = batchCap(e);
      const stock = ctx.plan(r, 1).stock;
      const n = Math.max(0, Math.min(cap, stock));
      rows.push({ r, e, ctx, ways, way, price: way ? way.price : null, cap, stock, n, thin: thinSale(e),
        net: way ? e.exp * n - way.price : null, payback: way && e.exp > 0 ? Math.ceil(way.price / e.exp - 1e-9) : null });
    }
    return rows;
  }

  // The cheapest climb from one skill to another at this scan's prices, with recipes a trainer teaches.
  // bought: also allow recipes taught by a recipe item that a vendor sells or the auction house lists.
  // A step is one recipe made for a run of skill points, while it still gives a point at least one time in four.
  // Learning a recipe costs once: Classic's trainer fee, or the recipe item's price. Results sell where they are
  // expected to bring more, but the auction house only counts for a quarter of what is already listed; the rest goes
  // to a vendor. Results a later step needs are kept instead.
  const GAP = 1e12;
  function levelPath(pt, opts, prof, from, to, mine, bought) {
    from = Math.max(1, Math.round(from) || 1); to = Math.round(to) || 0;
    const N = to - from;
    if (!(N > 0)) return { prof, from, to, steps: [], gaps: [], buy: [], short: [], mats: 0, fees: 0, back: 0, net: 0, missed: 0 };
    const base = Object.assign({}, opts, { sellTo: 'best', maxSkill: 300, trainerMats: true });
    // Materials can be crafted with this profession at the skill reached so far, and with the other professions given.
    const marks = [...new Set(recipes.filter((r) => r.prof === prof && r.src !== 2 && isReagent.has(r.res)).map((r) => r.learn))].sort((a, b) => a - b);
    const segOf = (s) => { let k = 0; while (k < marks.length && marks[k] <= s) k++; return k; };
    const ctxs = new Map();
    const ctxAt = (s) => {
      const k = segOf(s);
      if (!ctxs.has(k)) ctxs.set(k, context(pt, Object.assign({}, base, { mine: Object.assign({}, mine, { [prof]: k ? marks[k - 1] : 0 }) })));
      return ctxs.get(k);
    };
    const feeOf = new Map();
    const pool = [];
    for (const r of recipes) {
      if (r.prof !== prof || !r.yellow || !r.grey || r.learn >= to || r.grey <= from) continue;
      if (r.src !== 2) { feeOf.set(r.sid, { cost: r.fee, kind: r.fee ? 'trainer' : null }); pool.push(r); continue; }
      if (!bought || !r.ritem) continue;
      const p = pt.map.get(r.ritem), vu = ctxAt(from).vendorUnit(r.ritem);
      const ways = [];
      if (p && p.min != null) ways.push({ cost: p.min, kind: 'ah' });
      if (vu != null) ways.push({ cost: vu, kind: 'vendor' });
      if (!ways.length) continue;
      feeOf.set(r.sid, ways.sort((a, b) => a.cost - b.cost)[0]); pool.push(r);
    }
    // Per recipe and skill point: crafts for one point, and the prices in force at that skill.
    const infos = new Map();
    const info = (r, s) => {
      const key = segOf(s) + '|' + r.sid;
      if (!infos.has(key)) {
        const ctx = ctxAt(s), e = ctx.evalRecipe(r);
        let d = null;
        const stock = e.c.cost != null ? ctx.plan(r, 1).stock : 0;
        if (stock >= 1) { // the listed materials cover at least one craft
          const ah = e.via === 'ah' && !thinSale(e);
          d = { e, ctx, cost: e.c.cost, vend: e.vend, best: ah ? e.exp + e.c.cost : e.vend, cap: ah ? Math.floor(e.listed * 0.25 / e.y) : 0, stock };
        }
        infos.set(key, d);
      }
      return infos.get(key);
    };
    const table = pool.map((r) => {
      const row = new Array(N).fill(null);
      for (let j = 0; j < N; j++) {
        const s = from + j;
        if (r.learn > s) continue;
        const ch = skillChance(r, s);
        if (!ch) break;
        const d = info(r, s);
        if (d) row[j] = { n: 1 / ch, d };
      }
      return row;
    });
    // A recipe that gives a point less than one time in four is nearly grey: it only counts where nothing better does.
    for (let j = 0; j < N; j++) {
      if (!table.some((row) => row[j] && row[j].n <= 4)) continue;
      for (const row of table) if (row[j] && row[j].n > 4) row[j] = null;
    }
    // Shortest path over skill points. A run of recipe r from point i to j costs its crafts, rounded up, plus its fee
    // the first time. Each point remembers what its cheapest way there has already made, so a recipe picked up a
    // second time pays no second fee and gets no second auction-house quarter. Crafts past the listed materials
    // count a quarter dearer, which steers toward what can be bought today. bother[i]: what a step starting at point i
    // has to save to be worth switching recipes for.
    function solve(bother) {
      const cost = new Float64Array(N + 1).fill(Infinity);
      const prev = new Array(N + 1).fill(null);
      const done = new Array(N + 1).fill(null); // done[i]: recipe index -> crafts made on the cheapest way to point i
      cost[0] = 0; done[0] = new Map();
      for (let i = 0; i < N; i++) {
        if (i > 0) {
          const p = prev[i];
          done[i] = new Map(done[p.i]);
          if (p.ri >= 0) {
            let crafts = 0;
            for (let j = p.i; j < i; j++) crafts += table[p.ri][j].n;
            done[i].set(p.ri, (done[i].get(p.ri) || 0) + crafts);
          }
        }
        if (cost[i] + GAP < cost[i + 1]) { cost[i + 1] = cost[i] + GAP; prev[i + 1] = { i, ri: -1 }; } // no priced recipe gives this point
        const last = prev[i] ? prev[i].ri : -1;
        for (let ri = 0; ri < pool.length; ri++) {
          const row = table[ri];
          if (ri === last || !row[i]) continue;
          const had = done[i].get(ri) || 0;
          let made = had;
          let acc = (done[i].has(ri) ? 0 : feeOf.get(pool[ri].sid).cost) + bother[i];
          for (let j = i; j < N && row[j]; j++) {
            const n = row[j].n, d = row[j].d;
            const ahN = Math.max(0, Math.min(n, d.cap - made));
            const over = Math.max(0, Math.min(n, made + n - d.stock));
            acc += n * d.cost - ahN * d.best - (n - ahN) * d.vend + over * d.cost * 0.25;
            made += n;
            const whole = Math.ceil(made - had - 1e-9) - (made - had); // the part of a craft a step is rounded up by
            const t = cost[i] + acc + whole * (d.cost - d.vend);
            if (t < cost[j + 1]) { cost[j + 1] = t; prev[j + 1] = { i, ri }; }
          }
        }
      }
      const runs = [];
      for (let j = N; j > 0; j = prev[j].i) runs.push({ i: prev[j].i, j, ri: prev[j].ri });
      return runs.reverse();
    }
    // Walk the runs in order: buy materials, keep what later steps need, sell the rest.
    function account(runs) {
      const out = { prof, from, to, steps: [], gaps: [], buy: [], short: [], mats: 0, fees: 0, back: 0, net: 0, missed: 0 };
      const madeSoFar = new Map(), bags = new Map(), buyAll = new Map();
      for (const run of runs) {
        const s0 = from + run.i, s1 = from + run.j;
        if (run.ri < 0) {
          const g = out.gaps[out.gaps.length - 1];
          if (g && g[1] === s0) g[1] = s1; else out.gaps.push([s0, s1]);
          out.missed += s1 - s0;
          continue;
        }
        const r = pool[run.ri], row = table[run.ri], d = row[run.i].d;
        let crafts = 0;
        for (let j = run.i; j < run.j; j++) crafts += row[j].n;
        const n = Math.ceil(crafts - 1e-9);
        const own = new Map();
        for (const [id, lots] of bags) { const q = lots.reduce((t, l) => t + l.q, 0); if (q > 0) own.set(id, q); }
        const pl = d.ctx.plan(r, n, own);
        for (const [id, q] of pl.used) {
          let left = q;
          for (const lot of bags.get(id)) { const t = Math.min(lot.q, left); lot.q -= t; lot.step.keep += t; left -= t; if (left <= 0) break; }
        }
        const before = madeSoFar.get(r.sid) || 0;
        const fee = before > 0 ? { cost: 0, kind: null } : feeOf.get(r.sid);
        const step = { r, e: d.e, d, ctx: d.ctx, from: s0, to: s1, n, buy: pl.buy, pre: pl.steps, mats: pl.cost,
          kept: [...pl.used].map(([id, q]) => ({ id, q })), fee: fee.cost, feeKind: fee.kind,
          made: n * d.e.y, keep: 0, before, short: false };
        madeSoFar.set(r.sid, before + n);
        if (isReagent.has(r.res)) { if (!bags.has(r.res)) bags.set(r.res, []); bags.get(r.res).push({ step, q: step.made }); }
        for (const b of pl.buy) {
          const k = b.id + '|' + b.src, cur = buyAll.get(k);
          if (cur) cur.q += b.q; else buyAll.set(k, { id: b.id, q: b.q, src: b.src, u: b.u });
        }
        out.steps.push(step);
      }
      out.buy = [...buyAll.values()];
      const shortIds = new Set();
      for (const b of out.buy) {
        if (b.src !== 'ah') continue;
        const listed = (pt.map.get(b.id) || {}).qty || 0;
        if (b.q > listed) { out.short.push({ id: b.id, need: b.q, listed }); shortIds.add(b.id); }
      }
      for (const st of out.steps) {
        const y = st.e.y, sell = Math.max(0, st.made - st.keep);
        st.ah = Math.min(sell, Math.max(0, st.d.cap - st.before) * y);
        st.vendor = sell - st.ah;
        st.back = (st.ah * st.d.best + st.vendor * st.d.vend) / y;
        st.net = st.mats + st.fee - st.back;
        st.short = st.buy.some((b) => b.src === 'ah' && shortIds.has(b.id));
        out.mats += st.mats; out.fees += st.fee; out.back += st.back;
      }
      out.net = out.mats + out.fees - out.back;
      return out;
    }
    // A switch of recipe has to save 50 copper, or half of what a skill point's materials cost around that skill
    // (the 25 points around it on a first pass), whichever is more. That keeps one-craft detours out.
    const first = account(solve(new Float64Array(N).fill(50)));
    const perPoint = new Float64Array(N);
    for (const st of first.steps) for (let j = st.from - from; j < st.to - from; j++) perPoint[j] = st.mats / (st.to - st.from);
    const bother = new Float64Array(N);
    for (let i = 0; i < N; i++) {
      let sum = 0, n = 0;
      for (let j = Math.max(0, i - 12); j <= Math.min(N - 1, i + 12); j++) { sum += perPoint[j]; n++; }
      bother[i] = Math.max(50, 0.5 * sum / n);
    }
    return account(solve(bother));
  }
  return { items, recipes, craftIndex, context, spend, recipeBuys, levelPath };
}

// Chance of a skill point from one craft at this skill: 1 while orange, falling to 0 at grey. Null when unknown.
function skillChance(r, skill) {
  if (!r.yellow || !r.grey || r.grey <= r.yellow) return null;
  if (skill >= r.grey) return 0;
  if (skill < r.yellow) return 1;
  return (r.grey - skill) / (r.grey - r.yellow);
}

function coins(c) {
  if (c == null || !isFinite(c)) return null;
  const neg = c < 0;
  let v = Math.round(Math.abs(c));
  const g = Math.floor(v / 10000); v -= g * 10000;
  const s = Math.floor(v / 100); const cc = v - s * 100;
  const parts = [];
  if (g) parts.push([g, 'g']);
  if (s) parts.push([s, 's']);
  if (cc || (!g && !s)) parts.push([cc, 'c']);
  return { neg, parts };
}

if (typeof module !== 'undefined') module.exports = { parsePriceTable, marketLabel, makeEngine, coins, skillChance, speedBand, sellChance, expectedSale, CUT, TRIM, DEPOSIT, POSTS };
