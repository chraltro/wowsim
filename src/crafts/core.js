// Pure pricing logic. No DOM. Shared by the page and the Node test.
const CUT = 0.95; // the faction auction house keeps 5% of a sale
const TRIM = 2; // with trimming on, a sale counts at most 2x the other houses in the region

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
    };
  });
  const craftIndex = D.profs.map(() => new Map());
  for (const r of recipes) {
    const m = craftIndex[r.prof];
    if (!m.has(r.res)) m.set(r.res, []);
    m.get(r.res).push(r);
  }

  function context(pt, opts) {
    const facBit = pt.faction === 'horde' ? 2 : 1;
    const memo = new Map();
    const refs = (D.ref && D.ref[pt.region]) || {};
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
      const key = id + '|' + prof;
      if (memo.has(key)) return memo.get(key);
      let best = null;
      const v = vendorUnit(id);
      if (v != null) best = { u: v, src: 'vendor' };
      const a = ahUnit(id);
      if (a != null && (!best || a < best.u)) best = { u: a, src: 'ah' };
      if (stack.length < 3) {
        const list = craftIndex[prof].get(id);
        if (list) {
          for (const r of list) {
            if (r.learn > opts.maxSkill || stack.includes(r.sid)) continue;
            const c = recipeCost(r, [...stack, r.sid]);
            if (c.cost == null) continue;
            const u = c.cost / ((r.qmin + r.qmax) / 2);
            if (!best || u < best.u) best = { u, src: 'craft', via: r };
          }
        }
      }
      memo.set(key, best);
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
      let value = null; let via = null;
      if (opts.sellTo === 'ah') { value = ahNet; via = 'ah'; }
      else if (opts.sellTo === 'vendor') { value = vend > 0 ? vend : null; via = 'vendor'; }
      else if (ahNet != null && ahNet >= vend) { value = ahNet; via = 'ah'; }
      else if (vend > 0) { value = vend; via = 'vendor'; }
      const profit = c.cost != null && value != null ? value - c.cost : null;
      const p = pt.map.get(r.res);
      return {
        r, c, y, a, ahNet, vend, value, via, profit, bop, sale,
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
        if (sell > p.min) out.push({ id, buy: p.min, sell, profit: sell - p.min, qty: p.qty });
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
          out.push({ id, vendor: v, ah: s.u, raw: s.raw, trimmed: s.trimmed, net, profit: net - v, qty: p.qty, sold: p.sold, limited: !!it[5] });
        }
      }
      return out.sort((a, b) => b.profit - a.profit);
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
    return { evalRecipe, ahToVendor, vendorToAh, craftToVendor, ahUnit, saleUnit, vendorUnit };
  }
  return { items, recipes, craftIndex, context };
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

if (typeof module !== 'undefined') module.exports = { parsePriceTable, marketLabel, makeEngine, coins, CUT, TRIM };
