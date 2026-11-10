(function () {
  'use strict';
  const D = JSON.parse(document.getElementById('data').textContent);
  const E = makeEngine(D);
  const PROFS = D.profs;
  const TIERS = ['Apprentice', 'Journeyman', 'Expert', 'Artisan'];
  const SPEED = { fast: 'sells fast', steady: 'sells steadily', slow: 'sells slowly', barely: 'barely sells' };
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* storage unavailable */ } },
  };

  // ---------- prices ----------
  const SNAP = parsePriceTable(D.snap);
  const API = 'https://api.ahledger.com/v1/pricetable/';
  const dotted = (m) => m.replace(/\//g, '.');
  let PT = SNAP;
  let source = 'snapshot'; // snapshot | cache | live | paste
  let checking = false;
  (function loadSaved() {
    const t = store.get('fcp.prices');
    if (!t) return;
    try {
      const p = parsePriceTable(t);
      if (p.market !== SNAP.market || p.ts > SNAP.ts) { PT = p; source = store.get('fcp.source') === 'paste' ? 'paste' : 'cache'; }
    } catch (e) { store.del('fcp.prices'); }
  })();

  // ---------- state ----------
  const DEF = { prof: 'all', skills: { all: 150 }, basis: 'med', sellTo: 'best', sort: 'expected', onlyProfit: true, trainerOnly: false, trim: true, hideThin: true, disc: '0', mine: {}, budget: 5, planRecipes: false };
  let saved = {};
  try { saved = JSON.parse(store.get('fcp.ui') || '{}') || {}; } catch (e) { saved = {}; }
  const S = Object.assign({}, DEF, saved);
  S.skills = Object.assign({ all: Number(saved.maxSkill) || 150 }, saved.skills || {});
  S.mine = Object.assign({}, saved.mine || {});
  if (S.prof !== 'all' && !(Number(S.prof) >= 0 && Number(S.prof) < PROFS.length)) S.prof = 'all';
  if (!saved.v2 && S.sort === 'profit') S.sort = 'expected'; // first visit after expected profit arrived
  if (!['expected', 'profit', 'margin', 'skill'].includes(S.sort)) S.sort = 'expected';
  let q = '', fq = '';
  const open = new Set();
  const qty = new Map();
  let limit = 60, limA = 25, limB = 25, limC = 15;
  const save = () => store.set('fcp.ui', JSON.stringify({ v2: 1, prof: S.prof, skills: S.skills, basis: S.basis, sellTo: S.sellTo, sort: S.sort, onlyProfit: S.onlyProfit,
    trainerOnly: S.trainerOnly, trim: S.trim, hideThin: S.hideThin, disc: S.disc, mine: S.mine, budget: S.budget, planRecipes: S.planRecipes }));
  const single = () => S.prof !== 'all';
  const clampSkill = (v) => Math.min(300, Math.max(1, Math.round(Number(v)) || 150));
  const skillNow = () => clampSkill(S.skills[S.prof] ?? S.skills.all);
  const ctxOpts = (over) => Object.assign({ basis: S.basis, sellTo: S.sellTo, maxSkill: skillNow(), trim: S.trim, disc: Number(S.disc) }, over);
  const EVERY = Object.fromEntries(PROFS.map((_, i) => [i, 300]));

  // ---------- formatting ----------
  function coin(c, signed) {
    const k = coins(c);
    if (!k) return '<span class="coin">–</span>';
    const sign = k.neg ? '−' : (signed ? '+' : '');
    return '<span class="coin">' + sign + k.parts.map(([n, u]) => n + '<span class="' + u + '">' + u + '</span>').join('') + '</span>';
  }
  const coinText = (c) => { const k = coins(c); return k ? (k.neg ? '-' : '') + k.parts.map(([n, u]) => n + u).join(' ') : '?'; };
  const fmtInt = (n) => (n == null ? '–' : n >= 10000 ? Math.round(n / 1000) + 'k' : n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n));
  const pct = (x) => (x == null ? '' : (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(Math.round(x * 100)) + '%');
  const trimNum = (x) => (Number.isInteger(x) ? String(x) : x.toFixed(1));
  const itemName = (id) => { const it = E.items.get(id); return it ? it[0] : 'Item ' + id; };
  const itemQ = (id) => { const it = E.items.get(id); return it ? Math.min(it[1], 5) : 1; };
  const listedQty = (id) => (PT.map.get(id) || {}).qty || 0;
  const region = () => String(PT.region || '').toUpperCase();
  const ahlLink = (id) => 'https://ahledger.com/items/' + id + '/' + dotted(PT.market) + '?utm_source=forever_craft_profits';
  const sign = (v) => (v > 0 ? 'pos' : v < 0 ? 'neg' : '');
  function age(ts) {
    const h = (Date.now() - ts) / 36e5;
    if (h < 1) return 'under an hour ago';
    if (h < 36) return Math.round(h) + (Math.round(h) === 1 ? ' hour ago' : ' hours ago');
    const d = Math.round(h / 24);
    return d + (d === 1 ? ' day ago' : ' days ago');
  }

  function renderHouse() {
    const stale = Date.now() - PT.ts > 12 * 36e5;
    const src = { live: '', cache: ', saved copy', paste: ', pasted', snapshot: ', built-in copy' }[source];
    $('houseBtn').innerHTML = '<b>' + esc(marketLabel(PT)) + '</b><span class="age' + (stale ? ' stale' : '') + '">scanned ' + esc(age(PT.ts)) +
      (checking ? ', checking for a newer scan' : src) + '</span><span class="chg">Change</span>';
    document.querySelectorAll('.regionName').forEach((n) => { n.textContent = region(); });
  }

  // ---------- the question ----------
  const measure = $('measure');
  function fit(sel) {
    measure.textContent = sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : '';
    sel.style.width = Math.ceil(measure.getBoundingClientRect().width) + 'px';
  }
  const hasRecipes = PROFS.map(() => false);
  for (const r of E.recipes) hasRecipes[r.prof] = true;
  function buildProfSelect() {
    $('prof').innerHTML = '<option value="all">all professions</option>' +
      PROFS.map((p, i) => (hasRecipes[i] ? '<option value="' + i + '">' + esc(p) + '</option>' : '')).join('');
  }
  function syncAsk() {
    $('prof').value = S.prof;
    $('skill').value = skillNow();
    $('skillWord').textContent = single() ? 'at skill' : 'up to skill';
    $('sellTo').value = S.sellTo;
    const so = $('sort');
    so.querySelector('[value="skill"]').disabled = !single();
    so.value = S.sort === 'skill' && !single() ? 'expected' : S.sort;
    ['prof', 'sellTo', 'sort'].forEach((id) => fit($(id)));
  }
  function syncSettings() {
    $('basis').value = S.basis; $('disc').value = S.disc;
    $('trim').checked = !!S.trim; $('onlyProfit').checked = !!S.onlyProfit; $('trainerOnly').checked = !!S.trainerOnly; $('hideThin').checked = !!S.hideThin;
  }

  // ---------- rows ----------
  function line(o) {
    const tag = o.sid != null ? 'button type="button"' : 'div';
    return '<li class="row' + (o.open ? ' open' : '') + '"' + (o.sid != null ? ' data-sid="' + o.sid + '"' : '') + '>' +
      '<' + tag + ' class="row-head"' + (o.sid != null ? ' aria-expanded="' + !!o.open + '"' : '') + (o.tick ? ' style="--tick:var(--d-' + o.tick + ')"' : '') + '>' +
        '<span class="nm q' + (o.q ?? 1) + '">' + o.name + '</span>' +
        '<span class="amt ' + (o.cls || '') + '">' + o.amount + '</span>' +
        '<span class="sub">' + o.left + '</span><span class="sub r">' + o.right + '</span>' +
      '</' + tag.split(' ')[0] + '>' +
      (o.sid != null ? '<div class="body"><div class="inner">' + (o.open ? o.detail() : '') + '</div></div>' : '') +
    '</li>';
  }
  function difficulty(r, skill) {
    const ch = skillChance(r, skill);
    if (ch == null) return null;
    const mid = Math.round((r.yellow + r.grey) / 2);
    if (skill < r.yellow) return { tick: 'orange', text: 'orange until ' + r.yellow };
    if (skill < mid) return { tick: 'yellow', text: 'yellow until ' + mid };
    if (skill < r.grey) return { tick: 'green', text: 'green until ' + r.grey };
    return { tick: 'grey', text: 'grey, no skill-ups' };
  }
  const speedText = (e) => (e.via === 'vendor' ? 'to a vendor' : e.band ? SPEED[e.band] : 'no sales data');
  function row(e, view) {
    const r = e.r;
    const yld = r.qmin === r.qmax ? (r.qmin > 1 ? '×' + r.qmin : '') : '×' + r.qmin + ' to ' + r.qmax;
    const diff = view.single ? difficulty(r, view.skill) : null;
    let left = view.single ? 'Skill ' + r.learn + (diff ? ', ' + diff.text : '') : PROFS[r.prof] + ' ' + r.learn;
    if (r.src === 2) left += ', needs recipe';
    const shown = view.sort === 'profit' || view.sort === 'margin' ? e.profit : e.exp;
    let right;
    if (view.sort === 'margin' && e.margin != null) right = pct(e.margin) + ' on cost';
    else if (view.sort === 'skill') right = e.perPoint > 0 ? coin(e.perPoint) + ' a point' : 'pays for itself';
    else if (e.profit == null) right = 'no price';
    else right = '<span class="' + (e.band === 'barely' || (e.via === 'ah' && !e.band) ? 'warn' : '') + '">' + speedText(e) + '</span>';
    const short = e.profit != null && view.ctx.plan(r, 1).stock < 1;
    return line({ sid: r.sid, open: open.has(r.sid), tick: diff && diff.tick, q: itemQ(r.res),
      name: esc(r.name) + (yld ? '<span class="yield">' + yld + '</span>' : ''),
      amount: coin(shown, true), cls: sign(shown), left: esc(left) + (short ? ', <span class="warn">materials short</span>' : ''), right, detail: () => detail(e, view) });
  }

  function detail(e, view) {
    const r = e.r;
    const n = qty.get(r.sid) || 1;
    const plan = view.ctx.plan(r, n);
    const WORD = { vendor: 'vendor', ah: 'AH', craft: 'craft' };
    let rows = '';
    for (const p of e.c.parts) {
      const need = p.q * n;
      let small = '';
      if (p.src === 'craft' && p.via) {
        const st = plan.steps.find((s) => s.r.sid === p.via.sid);
        const k = st ? st.n : need;
        small = 'Cheaper to make: ' + p.via.reag.map(([id, qq]) => qq * k + ' ' + esc(itemName(id))).join(', ');
      } else if (p.u != null) {
        const bits = [];
        if (need > 1) bits.push(coin(p.u) + ' each');
        if (p.src === 'ah') bits.push(fmtInt(listedQty(p.id)) + ' listed');
        small = bits.join(', ');
      }
      rows += '<tr><td class="qn">' + need + '</td><td><span class="q' + itemQ(p.id) + '">' + esc(itemName(p.id)) + '</span>' + (small ? '<small>' + small + '</small>' : '') + '</td>' +
        '<td class="src">' + (p.src ? WORD[p.src] : '<span class="neg">no price</span>') + '</td>' +
        '<td class="amt">' + (p.u != null ? coin(p.u * need) : '–') + '</td></tr>';
    }
    const cost = e.c.cost != null ? e.c.cost * n : null;
    rows += '<tr class="sum"><td></td><td colspan="2">Materials</td><td class="amt">' + coin(cost) + '</td></tr>';
    const made = e.y * n;
    const count = made !== 1 ? trimNum(made) + ' at ' : '';
    if (e.via === 'vendor') {
      rows += '<tr><td></td><td colspan="2">Vendor pays ' + count + coin(e.vend / e.y) + '</td><td class="amt">' + coin(e.vend * n) + '</td></tr>';
      if (e.profit != null) rows += '<tr class="total"><td></td><td colspan="2">Profit' + (n > 1 ? ' for ' + n : '') + '</td><td class="amt ' + sign(e.profit) + '">' + coin(e.profit * n, true) + '</td></tr>';
    } else if (e.ahNet != null) {
      rows += '<tr><td></td><td colspan="2">Sells on the AH, ' + count + coin(e.a) + ' less 5%' +
        (e.sale && e.sale.trimmed ? '<small>Listed here at ' + coin(e.sale.raw) + '. Other ' + esc(region()) + ' houses sit near ' + coin(e.sale.ref) + ', so it counts at twice that.</small>' : '') +
        '</td><td class="amt">' + coin(e.ahNet * n) + '</td></tr>';
      if (e.profit != null) {
        rows += '<tr><td></td><td colspan="2">Profit if ' + (made > 1 ? 'they all sell' : 'it sells') + '</td><td class="amt ' + sign(e.profit) + '">' + coin(e.profit * n, true) + '</td></tr>';
        rows += '<tr class="total"><td></td><td colspan="2">Expected' + (n > 1 ? ' for ' + n : '') + '</td><td class="amt ' + sign(e.exp) + '">' + coin(e.exp * n, true) + '</td></tr>';
      }
    }

    let stock = '';
    if (isFinite(plan.stock)) stock = plan.stock < n ? '<span class="warn">Only enough listed for ' + plan.stock + '</span>' : 'Enough listed for ' + fmtInt(plan.stock);
    const notes = [];
    if (e.via === 'ah' && e.profit != null) {
      const c100 = Math.round(e.chance * 100);
      const where = e.ownTurn ? 'by this house\'s scans' : 'going by other ' + esc(region()) + ' houses';
      notes.push(e.band
        ? '<span class="' + (e.band === 'barely' ? 'warn' : '') + '">' + SPEED[e.band][0].toUpperCase() + SPEED[e.band].slice(1) + ': about ' + c100 + ' in 100 listings sell within 48 hours, ' + where + '.</span>'
        : '<span class="warn">No sales data for this item, so it counts as barely selling.</span>');
      if (e.deposit >= 1) notes.push('Each 48-hour listing puts down ' + coin(e.deposit / e.y) + ', lost if it expires. Expected assumes three tries, then a vendor.');
      const fd = view.ctx.fodder(r);
      if (fd) notes.push('One of the cheapest skill-ups ' + (fd[0] === fd[1] ? 'around ' + fd[0] : 'from ' + fd[0] + ' to ' + fd[1]) + ', so people leveling ' + esc(PROFS[r.prof]) + ' keep listing it.');
    }
    const crate = crateFor.get(r.res);
    if (crate) notes.push(crate.q + ' of these fill a ' + esc(itemName(crate.id)) + '.');
    if (D.writ && D.writ[r.res]) notes.push('A Craftsman\'s Writ asks for one of these.');
    if (r.ritem) {
      const it = E.items.get(r.ritem), rp = PT.map.get(r.ritem);
      const vu = view.ctx.vendorUnit(r.ritem);
      const fav = D.fav && D.fav[r.ritem];
      const bits = [];
      if (fav) bits.push('it costs ' + fav[0] + ' Merchant\'s Favor' + (fav[1] ? ' at Honored' : ''));
      if (vu != null) bits.push('a vendor sells it for ' + coin(vu) + (it && it[5] ? ' in limited stock' : ''));
      if (rp && rp.min != null) bits.push('the AH has it from ' + coin(rp.min));
      notes.push('Taught by <span class="q' + itemQ(r.ritem) + '">' + esc(itemName(r.ritem)) + '</span>' + (bits.length ? ': ' + bits.join(', and ') + '.' : ', which is not on the AH right now.'));
    }
    if (e.via === 'ah' && e.listed <= 2) notes.push('<span class="warn">' + (e.listed === 0 ? 'Nobody lists this here, so the price is a guess.' : 'Only ' + e.listed + ' listed here, so the price is one seller asking.') + '</span>');
    if (e.via === 'ah' && e.listed > 2 && made > e.listed) notes.push('<span class="warn">' + trimNum(made) + ' is more than the ' + e.listed + ' already listed. Expect to undercut to sell them all.</span>');
    if (e.via === 'ah' && e.sale && e.sale.ref != null && !e.sale.trimmed) notes.push('Other ' + esc(region()) + ' houses list it around ' + coin(e.sale.ref) + '.');
    if (e.via === 'ah') notes.push(e.vend > 0 ? 'A vendor pays ' + coin(e.vend / e.y) + ' each.' : 'Vendors do not buy it.');
    else if (e.ahNet != null) notes.push('On the AH it would bring ' + coin(e.ahNet / e.y) + ' each after the cut.');
    if (r.yellow && r.grey) notes.push('Gives a skill point every time below ' + r.yellow + ', none from ' + r.grey + '.');

    return '<div class="detail">' +
      '<div class="make"><span>Make</span><span class="stepper"><button type="button" data-step="-1" aria-label="One fewer">−</button><output>' + n + '</output><button type="button" data-step="1" aria-label="One more">+</button></span>' +
        '<span class="stock">' + stock + '</span></div>' +
      '<table class="bill">' + rows + '</table>' +
      (notes.length ? '<ul class="notes">' + notes.map((x) => '<li>' + x + '</li>').join('') + '</ul>' : '') +
      '<div class="acts"><button type="button" class="btn" data-copy>Copy shopping list</button>' +
        '<a class="ext" href="' + ahlLink(r.res) + '" target="_blank" rel="noopener">Price history on AHledger</a></div>' +
    '</div>';
  }
  const crateFor = new Map();
  for (const c of D.crates || []) for (let i = 0; i < c[4].length; i += 2) if (!crateFor.has(c[4][i])) crateFor.set(c[4][i], { id: c[0], q: c[4][i + 1] });

  function buyLines(buy, lines) {
    const group = (src, title) => {
      const xs = buy.filter((b) => b.src === src);
      if (!xs.length) return;
      lines.push('', title);
      for (const b of xs) lines.push(b.q + ' ' + itemName(b.id) + (b.u != null ? '  (' + coinText(b.u) + ' each)' : ''));
    };
    group('ah', 'Buy on the auction house:');
    group('vendor', 'Buy from a vendor:');
    group(null, 'No price found:');
  }
  function shoppingText(e, view) {
    const r = e.r, n = qty.get(r.sid) || 1;
    const plan = view.ctx.plan(r, n);
    const lines = [r.name + ' x' + n + ' (' + PROFS[r.prof] + ')'];
    buyLines(plan.buy, lines);
    if (plan.steps.length) { lines.push('', 'Craft first:'); for (const s of plan.steps) lines.push(s.n + ' x ' + s.r.name); }
    if (plan.cost != null && e.profit != null) {
      lines.push('', 'Materials about ' + coinText(plan.cost) + '. ' + (e.via === 'vendor' ? 'Profit about ' + coinText(e.profit * n) + ' sold to a vendor.'
        : 'Profit about ' + coinText(e.profit * n) + ' if it sells, ' + coinText(e.exp * n) + ' expected.'));
    }
    return lines.join('\n');
  }

  // ---------- crafts ----------
  let raf = 0;
  function schedule() { cancelAnimationFrame(raf); raf = requestAnimationFrame(render); }
  let craftsView = null, craftsEvals = new Map(), showUnpriced = false;
  function render() {
    const skill = skillNow(), one = single(), pi = Number(S.prof);
    const sort = S.sort === 'skill' && !one ? 'expected' : S.sort;
    const ctx = E.context(PT, ctxOpts());
    const view = craftsView = { ctx, single: one, skill, sort };
    const s = q.trim().toLowerCase();
    let pool = E.recipes.filter((r) => (!one || r.prof === pi) && r.learn <= skill && (!S.trainerOnly || r.src !== 2));
    if (s) pool = pool.filter((r) => r.name.toLowerCase().includes(s) || r.reag.some(([id]) => itemName(id).toLowerCase().includes(s)));
    const evals = pool.map(ctx.evalRecipe);
    const isThin = (e) => e.via === 'ah' && e.listed <= 2 && (!e.sale || e.sale.ref == null);
    const paper = sort === 'profit' || sort === 'margin';
    const gain = (e) => (paper ? e.profit : e.exp);
    const thin = S.hideThin ? evals.filter((e) => e.profit != null && gain(e) > 0 && isThin(e)).length : 0;
    const priced = evals.filter((e) => e.profit != null && !(S.hideThin && isThin(e)));
    const unpriced = evals.filter((e) => e.profit == null);
    const winners = priced.filter((e) => gain(e) > 0);
    let shown, tally;
    if (sort === 'skill') {
      shown = priced.filter((e) => { const ch = skillChance(e.r, skill); if (!ch) return false; e.perPoint = -e.exp / ch; return true; })
        .sort((a, b) => a.perPoint - b.perPoint);
      const free = shown.filter((e) => e.perPoint <= 0).length;
      tally = '<b>' + shown.length + '</b> ' + (shown.length === 1 ? 'recipe still gives' : 'recipes still give') + ' skill points at ' + skill + ', cheapest per point first.' +
        (free ? ' ' + free + (free === 1 ? ' is' : ' are') + ' expected to pay for ' + (free === 1 ? 'itself.' : 'themselves.') : '');
    } else {
      shown = (S.onlyProfit ? winners : priced).slice();
      const key = sort === 'margin' ? (e) => e.margin ?? -Infinity : gain;
      shown.sort((a, b) => (key(b) - key(a)) || (b.profit - a.profit));
      tally = '<b>' + winners.length + '</b> of ' + priced.length + (paper ? ' recipes make money if they sell.' : ' recipes are expected to make money.');
      if (thin) tally += ' ' + thin + ' one-off ' + (thin === 1 ? 'listing is' : 'listings are') + ' hidden.';
    }
    if (unpriced.length) tally += ' <button type="button" class="textbtn" id="toggleUnpriced">' + (showUnpriced ? 'Hide' : 'Show') + ' ' + unpriced.length + ' without a price</button>';
    if (showUnpriced) shown = shown.concat(unpriced);
    craftsEvals = new Map(shown.map((e) => [e.r.sid, e]));
    $('summary').innerHTML = tally;
    if (!shown.length) {
      $('list').innerHTML = '<li class="empty">' + (s ? 'Nothing matches “' + esc(q) + '”.' : 'Nothing is expected to make money with these settings. Raise the skill, or open Settings and price from the cheapest listing.') + '</li>';
      $('more').innerHTML = '';
      return;
    }
    $('list').innerHTML = shown.slice(0, limit).map((e) => row(e, view)).join('');
    $('more').innerHTML = shown.length > limit ? '<button type="button" class="btn" id="moreBtn">Show ' + Math.min(60, shown.length - limit) + ' more</button>' : '';
  }

  // ---------- flips ----------
  let flipView = null, flipEvals = new Map();
  function renderFlips() {
    const ctx = E.context(PT, ctxOpts({ sellTo: 'ah', maxSkill: 300 }));
    const vctx = E.context(PT, ctxOpts({ sellTo: 'vendor', maxSkill: 300 }));
    flipView = { ctx: vctx, single: false, skill: 300, sort: 'expected' };
    const s = fq.trim().toLowerCase();
    const match = (id) => !s || itemName(id).toLowerCase().includes(s);
    const A = ctx.ahToVendor().filter((x) => match(x.id));
    $('flipA').innerHTML = A.length ? A.slice(0, limA).map((x) => {
      const few = x.med != null && x.med >= x.sell;
      return line({ q: itemQ(x.id), name: esc(itemName(x.id)), amount: 'up to ' + coin(x.profit, true), cls: 'pos',
        left: 'Buy under ' + coin(x.sell) + ', cheapest is ' + coin(x.buy),
        right: x.qty <= 1 ? '1 listed' : (few ? 'fewer than half of ' : 'most of ') + fmtInt(x.qty) });
    }).join('') : '<li class="empty">Nothing is listed under vendor price in this scan.</li>';
    $('moreA').innerHTML = A.length > limA ? '<button type="button" class="btn" id="moreA_btn">Show more</button>' : '';

    const C = vctx.craftToVendor().filter((e) => !s || e.r.name.toLowerCase().includes(s) || e.r.reag.some(([id]) => itemName(id).toLowerCase().includes(s)));
    flipEvals = new Map(C.map((e) => [e.r.sid, e]));
    $('flipC').innerHTML = C.length ? C.slice(0, limC).map((e) => row(e, flipView)).join('') : '<li class="empty">No craft beats its materials at the vendor with these prices.</li>';
    $('moreC').innerHTML = C.length > limC ? '<button type="button" class="btn" id="moreC_btn">Show more</button>' : '';

    const B = ctx.vendorToAh().filter((x) => x.exp > 0 && !(S.hideThin && x.thin) && match(x.id));
    $('flipB').innerHTML = B.length ? B.slice(0, limB).map((x) => line({ q: itemQ(x.id), name: esc(itemName(x.id)) + (x.limited ? '<span class="yield">limited stock</span>' : ''), amount: coin(x.exp, true), cls: 'pos',
      left: 'Vendor ' + coin(x.vendor) + ', AH ' + coin(x.ah) + ', ' + fmtInt(x.qty) + ' listed',
      right: '<span class="' + (x.band === 'barely' || !x.band ? 'warn' : '') + '">' + (x.band ? SPEED[x.band] : 'no sales data') + '</span>' })).join('')
      : '<li class="empty">No vendor goods are expected to pay off on the auction house right now.</li>';
    $('moreB').innerHTML = B.length > limB ? '<button type="button" class="btn" id="moreB_btn">Show more</button>' : '';
  }

  // ---------- plan ----------
  let lastPlan = null;
  function renderMine() {
    const keys = Object.keys(S.mine);
    $('mineChips').innerHTML = keys.length ? keys.map((k, i) =>
      '<span class="mine">' + esc(PROFS[k]) + ' <input type="number" min="1" max="300" inputmode="numeric" data-mine="' + k + '" value="' + clampSkill(S.mine[k]) + '" aria-label="' + esc(PROFS[k]) + ' skill">' +
      '<button type="button" data-drop="' + k + '" aria-label="Remove ' + esc(PROFS[k]) + '">×</button></span>' + (i < keys.length - 1 ? '<span class="sepr">, </span>' : '<span class="sepr"> and </span>')).join('') : '';
    const rest = PROFS.map((p, i) => i).filter((i) => hasRecipes[i] && S.mine[i] == null);
    $('addProf').innerHTML = '<option value="">' + (keys.length ? 'another profession' : 'no professions yet') + '</option>' + rest.map((i) => '<option value="' + i + '">' + esc(PROFS[i]) + '</option>').join('');
    $('addProf').value = '';
    fit($('addProf'));
    $('budget').value = S.budget;
    $('planRecipes').checked = !!S.planRecipes;
  }
  function renderPlan() {
    const budget = Math.max(0, Number(S.budget) || 0) * 10000;
    const mine = {};
    for (const k of Object.keys(S.mine)) mine[k] = clampSkill(S.mine[k]);
    const P = lastPlan = E.spend(PT, ctxOpts({}), mine, budget, !!S.planRecipes);
    const noProf = !Object.keys(mine).length;
    if (!P.lines.length) {
      $('planTally').innerHTML = '';
      $('planList').innerHTML = '<li class="empty">' + (budget <= 0 ? 'Enter how much gold you want to put to work.'
        : 'Nothing gains at least ' + coin(P.minLine) + ' with this budget' + (noProf ? '. Add your professions to bring crafts in.' : '.')) + '</li>';
      $('planActs').innerHTML = '';
      return;
    }
    $('planTally').innerHTML = 'Spend <b>' + coin(P.spent) + '</b> to expect <b class="pos">' + coin(P.gain, true) + '</b>.' +
      (P.sure > 0 ? ' ' + coin(P.sure) + ' of that is certain.' : '') + (noProf ? ' Add your professions to bring crafts in. A friend\'s profession counts too, if they craft for you.' : '');
    $('planList').innerHTML = P.lines.map((l) => {
      if (l.kind === 'buyVendor') return line({ q: itemQ(l.id), name: 'Buy ' + esc(itemName(l.id)) + ', sell to a vendor', amount: coin(l.gain, true), cls: 'pos',
        left: 'AH under ' + coin(l.sell) + ', cheapest is ' + coin(l.cost), right: 'certain' });
      const e = l.e;
      return line({ q: itemQ(e.r.res), name: 'Craft ' + l.n + ' × ' + esc(e.r.name), amount: coin(l.gain * l.n, true), cls: 'pos',
        left: esc(PROFS[e.r.prof]) + ', materials ' + coin(l.cost * l.n), right: e.via === 'vendor' ? 'vendor, certain' : 'list 48h, ' + speedText(e) });
    }).join('');
    $('planActs').innerHTML = '<button type="button" class="btn" id="copyPlan">Copy the plan</button>';
  }
  function planText() {
    const P = lastPlan;
    const buy = new Map();
    const add = (b, n) => { const k = b.id + '|' + b.src; const c = buy.get(k); if (c) c.q += b.q * n; else buy.set(k, { id: b.id, src: b.src, u: b.u, q: b.q * n }); };
    const craft = [], sell = [];
    for (const l of P.lines) {
      if (l.kind === 'buyVendor') { add({ id: l.id, src: 'ah', u: l.cost, q: 1 }, 1); sell.push('Vendor: ' + itemName(l.id) + ' (pays ' + coinText(l.sell) + ')'); }
      else {
        const pl = P.ctx.plan(l.e.r, l.n);
        for (const b of pl.buy) add(b, 1);
        for (const st of pl.steps) craft.push(st.n + ' x ' + st.r.name);
        craft.push(l.n + ' x ' + l.e.r.name);
        sell.push((l.e.via === 'vendor' ? 'Vendor: ' : 'List 48h: ') + trimNum(l.e.y * l.n) + ' ' + l.e.r.name + (l.e.via === 'vendor' ? '' : ' at about ' + coinText(l.e.a)));
      }
    }
    const lines = ['Plan for ' + coinText(P.spent) + ' on ' + marketLabel(PT)];
    buyLines([...buy.values()], lines);
    if (craft.length) lines.push('', 'Craft:', ...craft);
    lines.push('', 'Sell:', ...sell, '', 'Expected gain ' + coinText(P.gain) + (P.sure > 0 ? ', ' + coinText(P.sure) + ' of it certain.' : '.'));
    return lines.join('\n');
  }

  // ---------- market ----------
  let crateRows = new Map();
  function crateDetail(c) {
    let rows = '';
    for (const f of c.fills) {
      const small = [];
      if (f.buy != null) small.push(fmtInt(f.listed) + ' listed');
      if (f.craft != null && (f.buy == null || f.craft < f.buy)) small.push('or make them for ' + coin(f.craft) + ' (' + esc(PROFS[f.via.prof]) + ')');
      rows += '<tr><td class="qn">' + f.q + '</td><td><span class="q' + itemQ(f.id) + '">' + esc(itemName(f.id)) + '</span>' + (small.length ? '<small>' + small.join(', ') + '</small>' : '') + '</td>' +
        '<td class="amt">' + (f.buy != null ? coin(f.buy) : '<span class="sub">not listed</span>') + '</td></tr>';
    }
    const notes = [];
    notes.push(c.crate != null ? 'An empty crate goes for ' + coin(c.crate) + ' here, ' + fmtInt(c.listed) + ' listed. If you loot one, that is what selling it brings.' : 'No empty crates of this kind are listed here.');
    notes.push(c.favor ? 'Hands in for ' + c.favor + ' Merchant\'s Favor. Needs character level ' + c.level + '.' : 'The favor for ' + TIERS[c.tier] + ' crates is not confirmed yet. Needs character level ' + c.level + '.');
    return '<div class="detail"><table class="bill">' + rows + '</table><ul class="notes">' + notes.map((x) => '<li>' + x + '</li>').join('') + '</ul></div>';
  }
  function renderMarket() {
    const ctx = E.context(PT, ctxOpts({ mine: EVERY, maxSkill: 300 }));
    const cs = ctx.crates().sort((a, b) => (a.perFavor ?? Infinity) - (b.perFavor ?? Infinity) || (a.total ?? Infinity) - (b.total ?? Infinity) || a.tier - b.tier);
    const blank = cs.filter((c) => !c.best && c.crate == null).length;
    crateRows = new Map(cs.map((c) => [-c.id, c])); // negative keys keep crates apart from recipe ids in the open set
    $('crateNote').textContent = blank ? blank + (blank === 1 ? ' crate has' : ' crates have') + ' neither the crate nor a fill listed here and ' + (blank === 1 ? 'is' : 'are') + ' left out.' : '';
    $('crateList').innerHTML = cs.filter((c) => c.best || c.crate != null).map((c) => {
      const name = itemName(c.id).replace('Waylaid Crate: ', '');
      const fill = c.best ? c.best.q + ' ' + esc(itemName(c.best.id)) + ' for ' + coin(c.best.buy) : 'no fill is listed';
      let amount, right;
      if (c.perFavor != null) { amount = coin(c.perFavor) + ' a favor'; right = 'crate ' + coin(c.crate) + ', ' + c.favor + ' favor'; }
      else if (c.total != null) { amount = coin(c.total); right = 'favor not confirmed'; }
      else { amount = c.best ? coin(c.best.buy) : '–'; right = c.crate == null ? 'no crate listed' : 'crate ' + coin(c.crate); }
      return line({ sid: -c.id, open: open.has(-c.id), q: itemQ(c.id), name: esc(name), amount, cls: '', left: fill, right, detail: () => crateDetail(c) });
    }).join('');

    const t = ctx.trend();
    const max = Math.max(0.1, ...t.map((r) => Math.abs(r.chg || 0)));
    $('wave').innerHTML = t.filter((r) => r.n).map((r) => {
      const w = r.chg == null ? 0 : Math.max(1.5, Math.abs(r.chg) / max * 50);
      return '<div class="wrow"><span>Level ' + r.lo + ' to ' + r.hi + '</span><span class="wbar">' + (r.chg == null || Math.abs(r.chg) < 0.005 ? '' : '<i class="' + (r.chg > 0 ? 'up' : 'dn') + '" style="width:' + w.toFixed(1) + '%"></i>') + '</span>' +
        '<b class="' + (r.chg == null ? '' : sign(Math.round(r.chg * 100))) + '">' + (r.chg == null ? 'few' : Math.round(r.chg * 100) === 0 ? '0%' : pct(r.chg)) + '</b></div>';
    }).join('') || '<p class="note">This scan has no 7-day medians yet.</p>';
  }

  // ---------- tabs ----------
  const TABS = ['crafts', 'flips', 'plan', 'market'];
  const RENDER = { flips: renderFlips, plan: () => { renderMine(); renderPlan(); }, market: renderMarket };
  let tab = 'crafts';
  function moveInk() {
    const b = $('tab-' + tab);
    $('tabInk').style.width = b.offsetWidth + 'px';
    $('tabInk').style.transform = 'translateX(' + b.offsetLeft + 'px)';
  }
  function setTab(t, push) {
    tab = TABS.includes(t) ? t : 'crafts';
    for (const k of TABS) { $('view-' + k).hidden = k !== tab; $('tab-' + k).setAttribute('aria-selected', String(k === tab)); }
    moveInk();
    if (RENDER[tab]) RENDER[tab]();
    if (push && location.hash !== '#' + tab) { try { history.replaceState(null, '', '#' + tab); } catch (e) { location.hash = tab; } }
  }
  const rerender = () => { limit = 60; schedule(); if (RENDER[tab]) RENDER[tab](); };

  // ---------- events ----------
  $('prof').addEventListener('change', (ev) => {
    S.prof = ev.target.value;
    if (S.skills[S.prof] == null) S.skills[S.prof] = S.mine[S.prof] != null ? clampSkill(S.mine[S.prof]) : skillNow();
    save(); syncAsk(); open.clear(); rerender();
  });
  $('skill').addEventListener('input', (ev) => {
    const v = Math.round(Number(ev.target.value));
    if (!(v >= 1 && v <= 300)) return;
    S.skills[S.prof] = v; save(); rerender();
  });
  $('skill').addEventListener('blur', () => { $('skill').value = skillNow(); });
  document.addEventListener('focusin', (ev) => { if (ev.target.matches && ev.target.matches('.ask input[type="number"]')) ev.target.select(); });
  $('sellTo').addEventListener('change', (ev) => { S.sellTo = ev.target.value; save(); syncAsk(); rerender(); });
  $('sort').addEventListener('change', (ev) => { S.sort = ev.target.value; save(); syncAsk(); rerender(); });
  $('q').addEventListener('input', (ev) => { q = ev.target.value; limit = 60; schedule(); });
  $('fq').addEventListener('input', (ev) => { fq = ev.target.value; limA = 25; limB = 25; limC = 15; renderFlips(); });
  $('summary').addEventListener('click', (ev) => { if (ev.target.id === 'toggleUnpriced') { showUnpriced = !showUnpriced; render(); } });
  $('more').addEventListener('click', (ev) => { if (ev.target.id === 'moreBtn') { limit += 60; render(); } });
  $('moreA').addEventListener('click', (ev) => { if (ev.target.id === 'moreA_btn') { limA += 25; renderFlips(); } });
  $('moreB').addEventListener('click', (ev) => { if (ev.target.id === 'moreB_btn') { limB += 25; renderFlips(); } });
  $('moreC').addEventListener('click', (ev) => { if (ev.target.id === 'moreC_btn') { limC += 15; renderFlips(); } });

  function toggle(li, head, html) {
    const sid = Number(li.dataset.sid);
    if (li.classList.contains('open')) {
      open.delete(sid); li.classList.remove('open'); head.setAttribute('aria-expanded', 'false');
    } else {
      li.querySelector('.inner').innerHTML = html();
      open.add(sid);
      void li.offsetHeight; // paint the closed state first so the opening animates
      li.classList.add('open'); head.setAttribute('aria-expanded', 'true');
    }
  }
  function copy(text, done) {
    navigator.clipboard.writeText(text).then(() => toast(done), () => toast('Copying is blocked here. Select the text and copy it by hand.'));
  }
  function onLedgerClick(ev, getMap, getView) {
    const li = ev.target.closest('.row');
    if (!li || !li.dataset.sid) return;
    const sid = Number(li.dataset.sid);
    const e = getMap().get(sid);
    if (!e) return;
    const step = ev.target.closest('[data-step]');
    if (step) {
      qty.set(sid, Math.min(999, Math.max(1, (qty.get(sid) || 1) + Number(step.dataset.step))));
      li.querySelector('.inner').innerHTML = detail(e, getView());
      return;
    }
    if (ev.target.closest('[data-copy]')) { copy(shoppingText(e, getView()), 'Shopping list copied'); return; }
    const head = ev.target.closest('.row-head');
    if (head) toggle(li, head, () => detail(e, getView()));
  }
  $('list').addEventListener('click', (ev) => onLedgerClick(ev, () => craftsEvals, () => craftsView));
  $('flipC').addEventListener('click', (ev) => onLedgerClick(ev, () => flipEvals, () => flipView));
  $('crateList').addEventListener('click', (ev) => {
    const head = ev.target.closest('.row-head'), li = ev.target.closest('.row');
    if (!head || !li || !li.dataset.sid) return;
    const c = crateRows.get(Number(li.dataset.sid));
    if (c) toggle(li, head, () => crateDetail(c));
  });
  for (const k of TABS) $('tab-' + k).addEventListener('click', () => setTab(k, true));
  window.addEventListener('hashchange', () => setTab(location.hash.slice(1), false));
  window.addEventListener('resize', moveInk);

  // plan inputs
  $('budget').addEventListener('input', (ev) => { const v = Number(ev.target.value); if (!(v >= 0)) return; S.budget = v; save(); renderPlan(); });
  $('addProf').addEventListener('change', (ev) => {
    const k = ev.target.value;
    if (k === '') return;
    S.mine[k] = clampSkill(S.skills[k] ?? 75);
    save(); renderMine(); renderPlan();
  });
  $('mineChips').addEventListener('input', (ev) => {
    const k = ev.target.dataset.mine;
    const v = Math.round(Number(ev.target.value));
    if (k == null || !(v >= 1 && v <= 300)) return;
    S.mine[k] = v; S.skills[k] = v; save(); renderPlan();
  });
  $('mineChips').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-drop]');
    if (!b) return;
    delete S.mine[b.dataset.drop]; save(); renderMine(); renderPlan();
  });
  $('planRecipes').addEventListener('change', (ev) => { S.planRecipes = ev.target.checked; save(); renderPlan(); });
  $('planActs').addEventListener('click', (ev) => { if (ev.target.id === 'copyPlan' && lastPlan) copy(planText(), 'Plan copied'); });

  // ---------- settings sheet ----------
  const sheet = $('sheet'), bg = $('sheetBg');
  let lastFocus = null;
  const houseId = () => 'forever.' + $('hRuleset').value + '.' + $('hFaction').value + '.' + $('hRegion').value;
  const syncLink = () => { $('ptLink').href = API + houseId(); };
  function openSheet() {
    lastFocus = document.activeElement;
    $('hRuleset').value = PT.ruleset; $('hFaction').value = PT.faction; $('hRegion').value = PT.region === 'us' ? 'us' : 'eu';
    syncLink(); syncSettings();
    $('sheetIntro').textContent = 'Showing ' + marketLabel(PT) + ', scanned ' + age(PT.ts) + '. Pick a house to load its latest scan from AHledger.';
    $('pasteErr').textContent = ''; $('liveErr').textContent = '';
    sheet.hidden = false; bg.hidden = false; sheet.scrollTop = 0;
    requestAnimationFrame(() => { sheet.classList.add('show'); bg.classList.add('show'); });
    setTimeout(() => $('closeSheet').focus({ preventScroll: true }), 330);
  }
  function closeSheet() {
    sheet.classList.remove('show'); bg.classList.remove('show');
    setTimeout(() => { sheet.hidden = true; bg.hidden = true; if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true }); }, 330);
  }
  let toastT = 0;
  function toast(msg) {
    const t = $('toast'); t.textContent = msg; t.classList.add('show');
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 2600);
  }
  function applyPrices(p, src) {
    PT = p; source = src;
    renderHouse(); render();
    if (RENDER[tab]) RENDER[tab]();
  }
  async function loadLatest(id) {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 9000);
    let res;
    try { res = await fetch(API + id, { signal: ctl.signal, cache: 'no-cache' }); }
    finally { clearTimeout(timer); }
    if (!res.ok) throw new Error(res.status === 404 ? 'AHledger has no scans for that house yet.' : 'AHledger answered with an error (' + res.status + '). Try again in a minute.');
    const text = await res.text();
    const p = parsePriceTable(text);
    store.set('fcp.prices', text.trim()); store.set('fcp.source', 'live'); store.set('fcp.market', id);
    if (p.market === PT.market && p.ts === PT.ts) { source = 'live'; renderHouse(); }
    else applyPrices(p, 'live');
    return p;
  }
  $('houseBtn').addEventListener('click', openSheet);
  document.querySelectorAll('[data-settings]').forEach((b) => b.addEventListener('click', openSheet));
  $('closeSheet').addEventListener('click', closeSheet);
  bg.addEventListener('click', closeSheet);
  document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape' && !sheet.hidden) closeSheet(); });
  ['hRuleset', 'hFaction', 'hRegion'].forEach((id) => $(id).addEventListener('change', syncLink));
  $('basis').addEventListener('change', (ev) => { S.basis = ev.target.value; save(); rerender(); });
  $('disc').addEventListener('change', (ev) => { S.disc = ev.target.value; save(); rerender(); });
  ['trim', 'onlyProfit', 'trainerOnly', 'hideThin'].forEach((id) => $(id).addEventListener('change', (ev) => { S[id] = ev.target.checked; save(); rerender(); }));
  $('copyLink').addEventListener('click', () => copy($('ptLink').href, 'Link copied'));
  $('loadLive').addEventListener('click', async () => {
    const b = $('loadLive');
    b.disabled = true; b.textContent = 'Loading'; $('liveErr').textContent = '';
    try {
      const p = await loadLatest(houseId());
      closeSheet();
      toast('Loaded ' + marketLabel(p) + ', scanned ' + age(p.ts));
    } catch (e) {
      $('liveErr').textContent = e.name === 'AbortError' ? 'AHledger took too long to answer. Try again.'
        : e instanceof TypeError ? 'This page cannot reach AHledger. Paste the table below instead.' : e.message;
      $('pasteBox').open = true;
    } finally { b.disabled = false; b.textContent = 'Load the latest scan'; }
  });
  $('usePaste').addEventListener('click', () => {
    const txt = $('paste').value;
    try {
      const p = parsePriceTable(txt);
      store.set('fcp.prices', txt.trim()); store.set('fcp.source', 'paste'); store.set('fcp.market', dotted(p.market));
      applyPrices(p, 'paste');
      $('paste').value = '';
      closeSheet();
      toast('Loaded ' + marketLabel(p) + ', scanned ' + age(p.ts));
    } catch (e) { $('pasteErr').textContent = e.message; }
  });
  $('restore').addEventListener('click', () => {
    store.del('fcp.prices'); store.del('fcp.source'); store.del('fcp.market'); applyPrices(SNAP, 'snapshot'); closeSheet(); toast('Back to the built-in prices');
  });

  // ---------- start ----------
  if (/github\.io$/.test(location.hostname)) $('siteLink').href = '../';
  $('buildNo').textContent = D.build;
  buildProfSelect();
  renderHouse(); syncAsk(); syncSettings();
  render();
  setTab(location.hash.slice(1), false);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { syncAsk(); if (tab === 'plan') renderMine(); moveInk(); });
  // Fetch the latest scan where the page may reach AHledger (GitHub Pages); elsewhere keep the copy we have.
  if (source !== 'paste' && /^https?:$/.test(location.protocol)) {
    checking = true; renderHouse();
    loadLatest(store.get('fcp.market') || dotted(PT.market)).catch(() => {}).finally(() => { checking = false; renderHouse(); });
  }
})();
