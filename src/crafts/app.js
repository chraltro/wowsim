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
  const DEF = { prof: 'all', skills: { all: 150 }, basis: 'med', sellTo: 'best', sort: 'expected', onlyProfit: true, trainerOnly: false, trim: true, hideThin: true, disc: '0', mine: {}, budget: 5, planRecipes: false,
    rbProf: 'all', lv: null };
  let saved = {};
  try { saved = JSON.parse(store.get('fcp.ui') || '{}') || {}; } catch (e) { saved = {}; }
  const S = Object.assign({}, DEF, saved);
  S.skills = Object.assign({ all: Number(saved.maxSkill) || 150 }, saved.skills || {});
  S.mine = Object.assign({}, saved.mine || {});
  if (S.prof !== 'all' && !(Number(S.prof) >= 0 && Number(S.prof) < PROFS.length)) S.prof = 'all';
  if (!saved.v2 && S.sort === 'profit') S.sort = 'expected'; // first visit after expected profit arrived
  if (!['expected', 'profit', 'margin', 'skill'].includes(S.sort)) S.sort = 'expected';
  let q = '', fq = '', rq = '';
  const open = new Set(), openR = new Set(), openL = new Set();
  const qty = new Map();
  let limit = 60, limA = 25, limB = 25, limC = 15;
  const save = () => store.set('fcp.ui', JSON.stringify({ v2: 1, prof: S.prof, skills: S.skills, basis: S.basis, sellTo: S.sellTo, sort: S.sort, onlyProfit: S.onlyProfit,
    trainerOnly: S.trainerOnly, trim: S.trim, hideThin: S.hideThin, disc: S.disc, mine: S.mine, budget: S.budget, planRecipes: S.planRecipes,
    rbProf: S.rbProf, lv: S.lv }));
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
  const fmtQty = (x) => fmtInt(Math.ceil(x - 1e-9));
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
  const fitNum = (el) => { el.style.width = (Math.max(1, String(el.value).length) + 0.35) + 'ch'; };
  const fitNums = () => document.querySelectorAll('.ask input[type="number"]').forEach(fitNum);
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
    fitNum($('skill'));
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
    if (r.est && r.src !== 2) notes.push('The skill a trainer teaches this at is an estimate.');

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

  // Table rows for everything a plan buys, and a line for what it crafts first.
  function buyRows(pl) {
    const WORD = { vendor: 'vendor', ah: 'AH' };
    let rows = '';
    const order = { ah: 0, vendor: 1 };
    for (const b of pl.buy.slice().sort((x, y) => (order[x.src] ?? 2) - (order[y.src] ?? 2))) {
      const bits = [];
      if (b.u != null && b.q > 1) bits.push(coin(b.u) + ' each');
      if (b.src === 'ah') { const l = listedQty(b.id); bits.push(l < b.q ? '<span class="warn">only ' + fmtInt(l) + ' listed</span>' : fmtInt(l) + ' listed'); }
      rows += '<tr><td class="qn">' + fmtQty(b.q) + '</td><td><span class="q' + itemQ(b.id) + '">' + esc(itemName(b.id)) + '</span>' + (bits.length ? '<small>' + bits.join(', ') + '</small>' : '') + '</td>' +
        '<td class="src">' + (b.src ? WORD[b.src] : '<span class="neg">no price</span>') + '</td><td class="amt">' + (b.u != null ? coin(b.u * b.q) : '–') + '</td></tr>';
    }
    return rows;
  }
  const craftFirst = (pl) => (pl.steps.length ? 'Craft first: ' + pl.steps.map((x) => x.n + ' × ' + esc(x.r.name)).join(', ') + '.' : '');
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

  // ---------- item check ----------
  const openK = new Set();
  let checkRows = new Map();
  const CHECK_SHOWN = 8;
  // Items whose name holds the search: ones listed on this house first, names that start with it before names that only hold it.
  function checkMatches(s) {
    const out = [];
    for (const [id, it] of E.items) {
      const at = it[0].toLowerCase().indexOf(s);
      if (at < 0) continue;
      out.push({ id, rank: (PT.map.has(id) ? 0 : 2) + (at === 0 ? 0 : 1), listed: listedQty(id) });
    }
    return out.sort((a, b) => a.rank - b.rank || b.listed - a.listed || a.id - b.id);
  }
  function checkWhy(c) {
    if (c.bop) return 'Soulbound items cannot be posted.';
    if (c.listAt == null) return c.sell > 0 ? 'Nobody lists it on this house or any other in the scan, so there is no price to post at.' : 'A vendor will not take it and nobody lists it.';
    if (c.verdict === 'post') return 'Posting beats a vendor by about ' + coin(c.gain) + ' a unit, counting the 5% cut and the deposits lost on listings that expire.';
    return c.net <= c.sell ? 'After the 5% cut the auction house pays no more than a vendor does.'
      : 'The extra ' + coin(c.net - c.sell) + ' a sale does not cover the deposit: about ' + Math.round((1 - c.chance) * 100) + '% of listings expire and lose ' + coin(c.deposit) + '.';
  }
  function checkDetail(c) {
    const cheap = c.min ?? c.med;
    let rows = '';
    if (c.listed > 0) rows += '<tr><td>Cheapest listing here</td><td class="amt">' + coin(cheap) + '<small>' + fmtInt(c.listed) + ' listed' + (c.med != null && c.med !== cheap ? ', median ' + coin(c.med) : '') + '</small></td></tr>';
    if (c.ref != null) rows += '<tr><td>Other ' + esc(region()) + ' houses</td><td class="amt">' + coin(c.ref) + '<small>median of their listings</small></td></tr>';
    if (c.listAt != null) {
      rows += '<tr><td>Post at about</td><td class="amt">' + coin(c.listAt) + '<small>' + (c.unlisted ? 'what other houses ask, no one here to undercut' : c.trimmed ? 'twice what other houses ask' : 'just under the cheapest') + '</small></td></tr>' +
        '<tr><td>After the 5% cut</td><td class="amt">' + coin(c.net) + '</td></tr>' +
        '<tr><td>Chance it sells in 48 hours</td><td class="amt">' + Math.round(c.chance * 100) + '%<small>' + (c.band ? SPEED[c.band] + (c.ownTurn ? '' : ', from other houses') : 'no sales data') + '</small></td></tr>' +
        '<tr><td>Deposit lost if it expires</td><td class="amt">' + coin(c.deposit) + '</td></tr>' +
        '<tr class="sum"><td>Expected a unit</td><td class="amt">' + coin(c.exp) + '<small>up to three listings, then a vendor</small></td></tr>';
    }
    rows += '<tr class="' + (c.listAt != null ? '' : 'sum') + '"><td>A vendor pays</td><td class="amt">' + (c.sell > 0 ? coin(c.sell) : '<span class="sub">nothing</span>') + '</td></tr>';
    const notes = [checkWhy(c)];
    if (c.thin) notes.push('One listing here and no other house to compare with, so the price may be a guess.');
    if (c.trimmed) notes.push('The cheapest listing here is far above other houses, so it counts at twice theirs.');
    return '<div class="detail"><table class="bill">' + rows + '</table><ul class="notes">' + notes.map((x) => '<li>' + x + '</li>').join('') + '</ul>' +
      (c.listed > 0 || c.ref != null ? '<div class="acts"><a class="ext" href="' + ahlLink(c.id) + '" target="_blank" rel="noopener">Price history on AHledger</a></div>' : '') + '</div>';
  }
  function checkRow(c) {
    const post = c.verdict === 'post';
    const word = c.bop ? 'soulbound' : post ? 'post it' + (c.band ? ', ' + SPEED[c.band] : '') : c.verdict === 'none' ? 'no buyer' : 'vendor it';
    return line({ sid: c.id, q: itemQ(c.id), name: esc(itemName(c.id)), amount: post ? coin(c.exp) : c.sell > 0 ? coin(c.sell) : '<span class="coin">–</span>', cls: post ? 'pos' : '',
      left: (c.sell > 0 ? 'Vendor ' + coin(c.sell) : 'No vendor price') + (c.listAt != null ? ', post at ' + coin(c.listAt) : c.bop ? '' : ', not on the AH'),
      right: '<span class="' + (post && (c.band === 'barely' || !c.band) ? 'warn' : '') + '">' + word + '</span>', open: openK.has(c.id), detail: () => checkDetail(c) });
  }
  function renderCheck(ctx, s) {
    const sect = $('chkSect');
    if (s.length < 2) { sect.hidden = true; $('chkList').innerHTML = ''; return; }
    const all = checkMatches(s).slice(0, 80).map((m) => ctx.sellCheck(m.id)).filter((c) => c && (c.listAt != null || c.bop || c.sell > 0));
    sect.hidden = !all.length;
    if (!all.length) { $('chkList').innerHTML = ''; return; }
    checkRows = new Map(all.map((c) => [c.id, c]));
    $('chkList').innerHTML = all.slice(0, CHECK_SHOWN).map(checkRow).join('');
    $('chkMore').textContent = all.length > CHECK_SHOWN ? 'Showing ' + CHECK_SHOWN + ' of ' + (all.length >= 80 ? 'more than 80' : all.length) + ' matches. Type more of the name to narrow it.' : '';
  }

  // ---------- flips ----------
  let flipView = null, flipEvals = new Map();
  function renderFlips() {
    const ctx = E.context(PT, ctxOpts({ sellTo: 'ah', maxSkill: 300 }));
    const vctx = E.context(PT, ctxOpts({ sellTo: 'vendor', maxSkill: 300 }));
    flipView = { ctx: vctx, single: false, skill: 300, sort: 'expected' };
    const s = fq.trim().toLowerCase();
    renderCheck(ctx, s);
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
    fitNums();
  }
  function renderPlan() {
    const budget = Math.max(0, Number(S.budget) || 0) * 10000;
    const mine = {};
    for (const k of Object.keys(S.mine)) mine[k] = clampSkill(S.mine[k]);
    const P = lastPlan = E.spend(PT, ctxOpts({}), mine, budget, !!S.planRecipes);
    const noProf = !Object.keys(mine).length;
    if (!P.lines.length) {
      $('planTally').innerHTML = '';
      const picks = noProf && budget > 0 ? '<div class="picks">' + PROFS.map((p, i) => (hasRecipes[i] ? '<button type="button" class="btn" data-addprof="' + i + '">' + esc(p) + '</button>' : '')).join('') + '</div>' : '';
      $('planList').innerHTML = '<li class="empty">' + (budget <= 0 ? 'Enter how much gold you want to put to work.'
        : 'Nothing gains at least ' + coin(P.minLine) + ' with this budget' + (noProf ? '. Tap the professions you have to bring crafts in.' : '.')) + picks + '</li>';
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

  // ---------- recipes worth buying ----------
  let rbRows = new Map(), rbAll = false, limR = 30, limW = 10;
  const haveSkill = (prof) => (S.mine[prof] != null ? clampSkill(S.mine[prof]) : null);
  function wayText(w) {
    if (w.src === 'ah') return coin(w.price) + ' on the AH';
    if (w.src === 'vendor') return coin(w.price) + ' from a vendor';
    return w.favor + ' favor' + (w.price != null ? ', about ' + coin(w.price) : '');
  }
  function buildRbSelect() {
    const mine = Object.keys(S.mine).length;
    $('rbProf').innerHTML = '<option value="all">every profession</option>' + (mine ? '<option value="mine">my professions</option>' : '') +
      PROFS.map((p, i) => (hasRecipes[i] ? '<option value="' + i + '">' + esc(p) + '</option>' : '')).join('');
    if (S.rbProf === 'mine' && !mine) S.rbProf = 'all';
    $('rbProf').value = S.rbProf;
    fit($('rbProf'));
  }
  function recipeDetail(x) {
    const r = x.r, e = x.e, w = x.way;
    const n = Math.max(1, x.n);
    const pl = x.ctx.plan(r, n);
    const notesTop = [];
    let rows = '';
    if (w) {
      const small = w.src === 'ah' ? fmtInt(w.listed) + ' listed, this is the cheapest'
        : w.src === 'vendor' ? (w.limited ? 'limited stock' : '')
        : w.favor + ' Merchant\'s Favor' + (w.honored ? ', needs Honored' : '');
      rows += '<tr><td class="qn">1</td><td><span class="q' + itemQ(r.ritem) + '">' + esc(itemName(r.ritem)) + '</span>' + (small ? '<small>' + small + '</small>' : '') + '</td>' +
        '<td class="src">' + { ah: 'AH', vendor: 'vendor', favor: 'crates' }[w.src] + '</td><td class="amt">' + coin(w.price) + '</td></tr>';
    }
    rows += buyRows(pl);
    const mats = pl.cost;
    rows += '<tr class="sum"><td></td><td colspan="2">Materials for ' + n + (n === 1 ? ' craft' : ' crafts') + '</td><td class="amt">' + coin(mats) + '</td></tr>';
    const made = e.y * n;
    rows += e.via === 'vendor'
      ? '<tr><td></td><td colspan="2">A vendor pays ' + (made !== 1 ? trimNum(made) + ' at ' : '') + coin(e.vend / e.y) + '</td><td class="amt">' + coin(e.vend * n) + '</td></tr>'
      : '<tr><td></td><td colspan="2">' + (made !== 1 ? trimNum(made) + ' sell' : 'Sells') + ' on the AH at about ' + coin(e.a) + ' less 5%<small>' + (e.band ? SPEED[e.band] : 'no sales data') + ', expected ' + coin(e.exp, true) + ' a craft after expired listings</small></td><td class="amt">' + coin(e.ahNet * n) + '</td></tr>';
    if (e.via === 'ah' && e.sale && e.sale.trimmed) notesTop.push('Listed here at ' + coin(e.sale.raw) + '. Other ' + esc(region()) + ' houses sit near ' + coin(e.sale.ref) + ', so a sale counts at twice that.');
    const after = e.exp * n - (w ? w.price : 0);
    rows += '<tr class="total"><td></td><td colspan="2">' + (w ? 'Expected after ' + (x.n > 1 ? 'the first batch' : 'the first craft') : 'Expected for ' + n) + '</td><td class="amt ' + sign(after) + '">' + coin(after, true) + '</td></tr>';

    const notes = [];
    const have = haveSkill(r.prof);
    notes.push('Needs ' + esc(PROFS[r.prof]) + ' ' + r.learn + (have != null && have < r.learn ? ', <span class="warn">you are at ' + have + '</span>' : '') + '. Makes <span class="q' + itemQ(r.res) + '">' + esc(r.name) + '</span>.');
    if (x.n < 1) notes.push('<span class="warn">The materials for even one craft are not all listed right now.</span>');
    else if (e.via === 'vendor') notes.push('A batch is ' + x.n + (x.stock < x.cap ? ', as far as the listed materials go.' : ' when the result goes to a vendor.'));
    else notes.push(x.stock < x.cap ? 'A batch is ' + x.n + ', as far as the listed materials go.' : 'A batch is ' + x.n + ': a quarter of the ' + fmtInt(e.listed) + ' already listed.');
    notes.push(...notesTop);
    const cf = craftFirst(pl);
    if (cf) notes.push(cf);
    if (w && w.src === 'favor' && w.crates) notes.push('The favor comes from ' + w.crates.map((k) => k.n + ' × ' + esc(itemName(k.c.id).replace('Waylaid Crate: ', ''))).join(', ') + ', each bought empty and filled. The Market tab has the crates.');
    for (const o of x.ways) {
      if (o === w) continue;
      if (o.src === 'ah') notes.push('The AH also has it from ' + coin(o.price) + '.');
      else if (o.src === 'vendor') notes.push('A vendor also sells it for ' + coin(o.price) + (o.limited ? ' in limited stock.' : '.'));
      else notes.push('Also sold for ' + o.favor + ' Merchant\'s Favor' + (o.honored ? ' at Honored' : '') + (o.price != null ? ', about ' + coin(o.price) + ' through crates.' : '. No crate is listed to price that.'));
    }
    if (!w) notes.push('Nobody sells the recipe here right now.');
    if (x.thin) notes.push('<span class="warn">Only ' + e.listed + ' listed here and no other house backs up the price.</span>');
    return '<div class="detail"><table class="bill">' + rows + '</table><ul class="notes">' + notes.map((t) => '<li>' + t + '</li>').join('') + '</ul>' +
      '<div class="acts"><button type="button" class="btn" data-copy>Copy shopping list</button>' +
      '<a class="ext" href="' + ahlLink(r.res) + '" target="_blank" rel="noopener">Price history on AHledger</a></div></div>';
  }
  function recipeText(x) {
    const r = x.r, n = Math.max(1, x.n), pl = x.ctx.plan(r, n);
    const lines = [itemName(r.ritem) + ' (' + PROFS[r.prof] + ' ' + r.learn + ')'];
    if (x.way) lines.push('Buy the recipe: ' + (x.way.src === 'favor' ? x.way.favor + ' Merchant\'s Favor, about ' + coinText(x.way.price) + ' through crates' : coinText(x.way.price) + (x.way.src === 'ah' ? ' on the auction house' : ' from a vendor')));
    lines.push('', 'For ' + n + ' x ' + r.name + ':');
    buyLines(pl.buy, lines);
    if (pl.steps.length) { lines.push('', 'Craft first:'); for (const st of pl.steps) lines.push(st.n + ' x ' + st.r.name); }
    if (x.way) lines.push('', 'Expected ' + coinText(x.e.exp * n - x.way.price) + ' after the first batch.');
    return lines.join('\n');
  }
  function renderRecipes() {
    buildRbSelect();
    const all = E.recipeBuys(PT, ctxOpts({}));
    const s = rq.trim().toLowerCase();
    const inProf = (x) => (S.rbProf === 'all' ? true : S.rbProf === 'mine' ? S.mine[x.r.prof] != null : x.r.prof === Number(S.rbProf));
    const pool = all.filter((x) => inProf(x) && x.e.exp > 0 && !(S.hideThin && x.thin) &&
      (!s || itemName(x.r.ritem).toLowerCase().includes(s) || x.r.name.toLowerCase().includes(s)));
    const sale = pool.filter((x) => x.way).sort((a, b) => b.net - a.net);
    const pay = sale.filter((x) => x.net > 0);
    const slow = sale.length - pay.length;
    const shown = rbAll ? sale : pay;
    rbRows = new Map(pool.map((x) => [x.r.sid, x]));
    $('rbTally').innerHTML = '<b>' + pay.length + '</b> ' + (pay.length === 1 ? 'recipe for sale pays' : 'recipes for sale pay') + ' for ' + (pay.length === 1 ? 'itself' : 'themselves') + ' with the first batch of crafts.' +
      (slow ? ' <button type="button" class="textbtn" id="rbToggle">' + (rbAll ? 'Hide' : 'Show') + ' ' + slow + ' that ' + (slow === 1 ? 'takes' : 'take') + ' longer</button>' : '');
    const rowOf = (x) => {
      const have = haveSkill(x.r.prof);
      const behind = have != null && have < x.r.learn;
      let right;
      if (!x.way) right = SPEED[x.e.band] || (x.e.via === 'vendor' ? 'to a vendor' : 'no sales data');
      else if (x.n < 1) right = '<span class="warn">materials short</span>';
      else right = x.payback <= x.n ? 'pays back in ' + x.payback + (x.payback === 1 ? ' craft' : ' crafts') : x.payback + ' crafts to pay back';
      return line({ sid: x.r.sid, open: openR.has(x.r.sid), q: itemQ(x.r.ritem), name: esc(itemName(x.r.ritem)),
        amount: x.way ? coin(x.net, true) : coin(x.e.exp, true) + ' a craft', cls: sign(x.way ? x.net : x.e.exp),
        left: esc(PROFS[x.r.prof]) + ' ' + (behind ? '<span class="warn">' + x.r.learn + '</span>' : x.r.learn) + (x.way ? ', ' + wayText(x.way) : ''), right, detail: () => recipeDetail(x) });
    };
    $('rbList').innerHTML = shown.length ? shown.slice(0, limR).map(rowOf).join('')
      : '<li class="empty">' + (s ? 'Nothing matches “' + esc(rq) + '”.' : 'No recipe for sale pays for itself in one batch right now.') + '</li>';
    $('rbMore').innerHTML = shown.length > limR ? '<button type="button" class="btn" id="rbMoreBtn">Show ' + Math.min(30, shown.length - limR) + ' more</button>' : '';
    const watch = pool.filter((x) => !x.way).sort((a, b) => b.e.exp - a.e.exp);
    $('rbWatchSect').hidden = !watch.length;
    $('rbWatch').innerHTML = watch.slice(0, limW).map(rowOf).join('');
    $('rbWatchMore').innerHTML = watch.length > limW ? '<button type="button" class="btn" id="rbWatchBtn">Show ' + Math.min(20, watch.length - limW) + ' more</button>' : '';
  }

  // ---------- leveling ----------
  const NO_PATH = ['Enchanting', 'Mining', 'Herbalism', 'Skinning']; // these level by enchanting or gathering, which has no price
  const LEVELERS = PROFS.map((p, i) => i).filter((i) => hasRecipes[i] && !NO_PATH.includes(PROFS[i]));
  const TIER = [75, 150, 225, 300];
  let lastPath = null;
  function knownSkill(prof) { return S.mine[prof] != null ? clampSkill(S.mine[prof]) : S.skills[prof] != null ? clampSkill(S.skills[prof]) : null; }
  function lvDefaults(prof) {
    const k = knownSkill(prof);
    const from = k != null && k < 300 ? k : 1;
    return { prof, from, to: TIER.find((t) => t > from) || 300, bought: !!(S.lv && S.lv.bought) };
  }
  function lvState() {
    if (!S.lv || !LEVELERS.includes(Number(S.lv.prof))) {
      const mine = Object.keys(S.mine).map(Number).find((i) => LEVELERS.includes(i));
      S.lv = lvDefaults(mine != null ? mine : single() && LEVELERS.includes(Number(S.prof)) ? Number(S.prof) : PROFS.indexOf('Tailoring'));
    }
    return S.lv;
  }
  function syncLeveling() {
    const L = lvState();
    $('lvProf').innerHTML = LEVELERS.map((i) => '<option value="' + i + '">' + esc(PROFS[i]) + '</option>').join('');
    $('lvProf').value = L.prof; fit($('lvProf'));
    $('lvFrom').value = L.from; $('lvTo').value = L.to; $('lvBought').checked = !!L.bought;
    fitNum($('lvFrom')); fitNum($('lvTo'));
  }
  const whole = (x) => Math.round(x);
  function sellText(st) {
    const k = whole(st.keep), a = whole(st.ah), v = whole(st.vendor);
    if (k && !a && !v) return 'keep for later';
    const bits = [];
    if (k) bits.push('keep ' + fmtInt(k));
    if (a && !v && !k) return 'sell on the AH';
    if (v && !a && !k) return 'to a vendor';
    if (a) bits.push('AH ' + fmtInt(a));
    if (v) bits.push('vendor ' + fmtInt(v));
    return bits.join(', ') || 'nothing to sell';
  }
  const costCoin = (c) => (c < -0.5 ? coin(-c, true) : c < 0.5 ? coin(0) : coin(-c));
  const costCls = (c) => (c < -0.5 ? 'pos' : '');
  function stepDetail(st, P) {
    const r = st.r, e = st.e, y = e.y;
    let rows = buyRows(st);
    for (const k of st.kept) rows += '<tr><td class="qn">' + fmtQty(k.q) + '</td><td><span class="q' + itemQ(k.id) + '">' + esc(itemName(k.id)) + '</span><small>made in an earlier step</small></td><td class="src">kept</td><td class="amt">–</td></tr>';
    rows += '<tr class="sum"><td></td><td colspan="2">Materials for ' + st.n + (st.n === 1 ? ' craft' : ' crafts') + '</td><td class="amt">' + coin(st.mats) + '</td></tr>';
    if (st.fee > 0) rows += '<tr><td></td><td colspan="2">' + (st.feeKind === 'trainer' ? 'Trainer fee, at Classic\'s price' : 'Buy <span class="q' + itemQ(r.ritem) + '">' + esc(itemName(r.ritem)) + '</span> ' + (st.feeKind === 'ah' ? 'on the AH' : 'from a vendor')) + '</td><td class="amt">' + coin(st.fee) + '</td></tr>';
    if (whole(st.ah)) rows += '<tr><td></td><td colspan="2">' + fmtInt(whole(st.ah)) + ' to the AH at about ' + coin(e.a) + ' less 5%<small>' + (e.band ? SPEED[e.band] : 'no sales data') + ', so ' + coin(st.d.best / y) + ' each is what to expect</small></td><td class="amt pos">' + coin(st.ah * st.d.best / y, true) + '</td></tr>';
    if (whole(st.vendor)) rows += '<tr><td></td><td colspan="2">' + fmtInt(whole(st.vendor)) + ' to a vendor at ' + coin(st.d.vend / y) + '</td><td class="amt pos">' + coin(st.vendor * st.d.vend / y, true) + '</td></tr>';
    if (whole(st.keep)) rows += '<tr><td></td><td colspan="2">' + fmtInt(whole(st.keep)) + ' kept for later steps</td><td class="amt">–</td></tr>';
    rows += '<tr class="total"><td></td><td colspan="2">' + (st.net < -0.5 ? 'This step is expected to gain' : 'This step costs about') + '</td><td class="amt ' + costCls(st.net) + '">' + coin(Math.abs(st.net)) + '</td></tr>';
    const notes = [];
    const pts = st.to - st.from;
    notes.push(st.to <= r.yellow ? 'Orange the whole way: every craft gives a point.'
      : 'Gives a point every time below ' + r.yellow + ' and none from ' + r.grey + ', so ' + pts + (pts === 1 ? ' point takes' : ' points take') + ' about ' + st.n + (st.n === 1 ? ' craft.' : ' crafts.'));
    const cf = craftFirst({ steps: st.pre });
    if (cf) notes.push(cf);
    if (whole(st.ah) && whole(st.vendor)) notes.push('The AH counts for a quarter of the ' + fmtInt(e.listed) + ' already listed. The rest goes to a vendor.');
    if (st.short) {
      const mine = P.short.filter((x) => st.buy.some((b) => b.src === 'ah' && b.id === x.id));
      notes.push('<span class="warn">The whole plan needs more than is listed of ' + mine.map((x) => esc(itemName(x.id)) + ' (' + fmtQty(x.need) + ', ' + fmtInt(x.listed) + ' listed)').join(' and ') + '.</span>');
    }
    if (r.est && r.src !== 2) notes.push('The skill a trainer teaches this at is an estimate.');
    return '<div class="detail"><table class="bill">' + rows + '</table><ul class="notes">' + notes.map((t) => '<li>' + t + '</li>').join('') + '</ul>' +
      '<div class="acts"><button type="button" class="btn" data-copy>Copy this step</button>' +
      '<a class="ext" href="' + ahlLink(r.res) + '" target="_blank" rel="noopener">Price history on AHledger</a></div></div>';
  }
  function sellLine(st) {
    const k = whole(st.keep), a = whole(st.ah), v = whole(st.vendor);
    const bits = [];
    if (k) bits.push('keep ' + k);
    if (a) bits.push(a + ' to the AH at about ' + coinText(st.e.a));
    if (v) bits.push(v + ' to a vendor');
    return bits.join(', ');
  }
  function stepText(st) {
    const lines = [st.n + ' x ' + st.r.name + ' (' + PROFS[st.r.prof] + ' ' + st.from + ' to ' + st.to + ')'];
    if (st.fee > 0) lines.push(st.feeKind === 'trainer' ? 'Learn it from a trainer, about ' + coinText(st.fee) : 'Buy ' + itemName(st.r.ritem) + (st.feeKind === 'ah' ? ' on the auction house, ' : ' from a vendor, ') + coinText(st.fee));
    buyLines(st.buy, lines);
    if (st.kept.length) { lines.push('', 'From earlier steps:'); for (const k of st.kept) lines.push(Math.ceil(k.q - 1e-9) + ' ' + itemName(k.id)); }
    if (st.pre.length) { lines.push('', 'Craft first:'); for (const x of st.pre) lines.push(x.n + ' x ' + x.r.name); }
    const sl = sellLine(st);
    if (sl) lines.push('', 'Then: ' + sl + '.');
    return lines.join('\n');
  }
  function pathText(P) {
    const lines = [PROFS[P.prof] + ' ' + P.from + ' to ' + P.to + ' on ' + marketLabel(PT)];
    buyLines(P.buy, lines);
    lines.push('', 'Steps:');
    for (const st of P.steps) {
      const sl = sellLine(st);
      lines.push(st.from + ' to ' + st.to + ': ' + st.n + ' x ' + st.r.name + (st.fee > 0 && st.feeKind !== 'trainer' ? ' (buy ' + itemName(st.r.ritem) + ')' : '') + (st.pre.length ? ' (first ' + st.pre.map((x) => x.n + ' x ' + x.r.name).join(', ') + ')' : '') + (sl ? ', ' + sl : ''));
    }
    for (const g of P.gaps) lines.push(g[0] + ' to ' + g[1] + ': nothing with listed materials gives points');
    lines.push('', 'Materials about ' + coinText(P.mats) + (P.fees > 0 ? ', learning the recipes about ' + coinText(P.fees) : '') + ', expected back from sales ' + coinText(P.back) + '.');
    return lines.join('\n');
  }
  function renderLeveling() {
    const L = lvState();
    const from = Math.round(Number(L.from)), to = Math.round(Number(L.to));
    if (!(from >= 1 && to <= 300 && to > from)) {
      lastPath = null;
      $('lvTally').innerHTML = '';
      $('lvList').innerHTML = '<li class="empty">Set a target above your skill, up to 300.</li>';
      $('lvActs').innerHTML = '';
      return;
    }
    const mine = {};
    for (const k of Object.keys(S.mine)) mine[k] = clampSkill(S.mine[k]);
    const P = lastPath = E.levelPath(PT, ctxOpts({}), Number(L.prof), from, to, mine, !!L.bought);
    const ahead = P.net < -0.5;
    const spend = 'Materials ' + coin(P.mats) + (P.fees > 0 ? ' and ' + coin(P.fees) + ' to learn the recipes' : '');
    let tally = !P.steps.length ? '' : ahead
      ? 'Expected to come out <b class="pos">' + coin(-P.net) + '</b> ahead. ' + spend + ', against ' + coin(P.back) + ' expected from selling what you make.'
      : 'About <b>' + coin(P.net) + '</b> all in. ' + spend + ', less ' + coin(P.back) + ' expected from selling what you make.';
    if (P.gaps.length) tally += ' <span class="warn">Nothing with listed materials gives points from ' + P.gaps.map((g) => g[0] + ' to ' + g[1]).join(' or ') + '.</span>' + (L.bought ? '' : ' Recipes you would have to buy may cover it.');
    if (P.short.length) {
      const top = P.short.slice().sort((a, b) => b.need / Math.max(1, b.listed) - a.need / Math.max(1, a.listed));
      tally += ' <span class="warn">The auction house lists ' + fmtInt(top[0].listed) + ' ' + esc(itemName(top[0].id)) + ' and this needs ' + fmtQty(top[0].need) + (top.length > 1 ? ', and ' + (top.length - 1) + ' more ' + (top.length === 2 ? 'material is' : 'materials are') + ' short' : '') + '.</span>';
    }
    $('lvTally').innerHTML = tally;
    if (!P.steps.length) {
      $('lvList').innerHTML = '<li class="empty">Nothing with listed materials gives ' + esc(PROFS[P.prof]) + ' points between ' + from + ' and ' + to + ' in this scan.</li>';
      $('lvActs').innerHTML = '';
      return;
    }
    $('lvList').innerHTML = P.steps.map((st, i) => {
      const diff = difficulty(st.r, st.from);
      return line({ sid: i, open: openL.has(i), tick: diff && diff.tick, q: itemQ(st.r.res),
        name: st.n + ' × ' + esc(st.r.name), amount: costCoin(st.net), cls: costCls(st.net),
        left: 'Skill ' + st.from + ' to ' + st.to + (st.short ? ', <span class="warn">materials short</span>' : '') + (st.fee > 0 && st.feeKind !== 'trainer' ? ', buy the recipe' : ''),
        right: sellText(st), detail: () => stepDetail(st, P) });
    }).join('');
    $('lvActs').innerHTML = '<button type="button" class="btn" id="copyPath">Copy the whole plan</button>';
  }

  // ---------- tabs ----------
  const TABS = ['crafts', 'flips', 'plan', 'recipes', 'leveling', 'market'];
  const RENDER = { flips: renderFlips, plan: () => { renderMine(); renderPlan(); }, recipes: renderRecipes, leveling: () => { syncLeveling(); renderLeveling(); }, market: renderMarket };
  let tab = 'crafts';
  function tabEdges() {
    const bar = $('tabs'), over = bar.scrollWidth - bar.clientWidth;
    bar.classList.toggle('more-l', over > 2 && bar.scrollLeft > 6);
    bar.classList.toggle('more-r', over > 2 && bar.scrollLeft < over - 6);
  }
  function moveInk() {
    const b = $('tab-' + tab);
    $('tabInk').style.width = b.offsetWidth + 'px';
    $('tabInk').style.transform = 'translateX(' + b.offsetLeft + 'px)';
    tabEdges();
  }
  function setTab(t, push) {
    tab = TABS.includes(t) ? t : 'crafts';
    for (const k of TABS) { $('view-' + k).hidden = k !== tab; $('tab-' + k).setAttribute('aria-selected', String(k === tab)); }
    moveInk();
    const bar = $('tabs'), btn = $('tab-' + tab);
    if (bar.scrollWidth > bar.clientWidth) bar.scrollTo({ left: btn.offsetLeft - (bar.clientWidth - btn.offsetWidth) / 2, behavior: 'smooth' });
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
  document.addEventListener('input', (ev) => { if (ev.target.matches && ev.target.matches('.ask input[type="number"]')) fitNum(ev.target); });
  document.addEventListener('focusout', (ev) => { if (ev.target.matches && ev.target.matches('.ask input[type="number"]')) requestAnimationFrame(() => fitNum(ev.target)); });
  $('sellTo').addEventListener('change', (ev) => { S.sellTo = ev.target.value; save(); syncAsk(); rerender(); });
  $('sort').addEventListener('change', (ev) => { S.sort = ev.target.value; save(); syncAsk(); rerender(); });
  $('q').addEventListener('input', (ev) => { q = ev.target.value; limit = 60; schedule(); });
  $('fq').addEventListener('input', (ev) => { fq = ev.target.value; limA = 25; limB = 25; limC = 15; renderFlips(); });
  $('summary').addEventListener('click', (ev) => { if (ev.target.id === 'toggleUnpriced') { showUnpriced = !showUnpriced; render(); } });
  $('more').addEventListener('click', (ev) => { if (ev.target.id === 'moreBtn') { limit += 60; render(); } });
  $('moreA').addEventListener('click', (ev) => { if (ev.target.id === 'moreA_btn') { limA += 25; renderFlips(); } });
  $('moreB').addEventListener('click', (ev) => { if (ev.target.id === 'moreB_btn') { limB += 25; renderFlips(); } });
  $('moreC').addEventListener('click', (ev) => { if (ev.target.id === 'moreC_btn') { limC += 15; renderFlips(); } });

  function toggle(li, head, html, set) {
    const sid = Number(li.dataset.sid);
    set = set || open;
    if (li.classList.contains('open')) {
      set.delete(sid); li.classList.remove('open'); head.setAttribute('aria-expanded', 'false');
    } else {
      li.querySelector('.inner').innerHTML = html();
      set.add(sid);
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
  $('chkList').addEventListener('click', (ev) => {
    const head = ev.target.closest('.row-head'), li = ev.target.closest('.row');
    if (!head || !li || !li.dataset.sid) return;
    const c = checkRows.get(Number(li.dataset.sid));
    if (c) toggle(li, head, () => checkDetail(c), openK);
  });
  $('crateList').addEventListener('click', (ev) => {
    const head = ev.target.closest('.row-head'), li = ev.target.closest('.row');
    if (!head || !li || !li.dataset.sid) return;
    const c = crateRows.get(Number(li.dataset.sid));
    if (c) toggle(li, head, () => crateDetail(c));
  });
  // recipes worth buying
  $('rbProf').addEventListener('change', (ev) => { S.rbProf = ev.target.value; save(); openR.clear(); limR = 30; limW = 10; renderRecipes(); });
  $('rq').addEventListener('input', (ev) => { rq = ev.target.value; limR = 30; limW = 10; renderRecipes(); });
  $('rbTally').addEventListener('click', (ev) => { if (ev.target.id === 'rbToggle') { rbAll = !rbAll; renderRecipes(); } });
  $('rbMore').addEventListener('click', (ev) => { if (ev.target.id === 'rbMoreBtn') { limR += 30; renderRecipes(); } });
  $('rbWatchMore').addEventListener('click', (ev) => { if (ev.target.id === 'rbWatchBtn') { limW += 20; renderRecipes(); } });
  const onRecipeClick = (ev) => {
    const li = ev.target.closest('.row');
    if (!li || !li.dataset.sid) return;
    const x = rbRows.get(Number(li.dataset.sid));
    if (!x) return;
    if (ev.target.closest('[data-copy]')) { copy(recipeText(x), 'Shopping list copied'); return; }
    const head = ev.target.closest('.row-head');
    if (head) toggle(li, head, () => recipeDetail(x), openR);
  };
  $('rbList').addEventListener('click', onRecipeClick);
  $('rbWatch').addEventListener('click', onRecipeClick);
  // leveling
  const lvChanged = () => { save(); openL.clear(); renderLeveling(); };
  $('lvProf').addEventListener('change', (ev) => { S.lv = lvDefaults(Number(ev.target.value)); syncLeveling(); lvChanged(); });
  $('lvFrom').addEventListener('input', (ev) => { const v = Math.round(Number(ev.target.value)); if (!(v >= 1 && v <= 299)) return; S.lv.from = v; lvChanged(); });
  $('lvTo').addEventListener('input', (ev) => { const v = Math.round(Number(ev.target.value)); if (!(v >= 2 && v <= 300)) return; S.lv.to = v; lvChanged(); });
  ['lvFrom', 'lvTo'].forEach((id) => $(id).addEventListener('blur', () => { $('lvFrom').value = S.lv.from; $('lvTo').value = S.lv.to; }));
  $('lvBought').addEventListener('change', (ev) => { S.lv.bought = ev.target.checked; lvChanged(); });
  $('lvList').addEventListener('click', (ev) => {
    const li = ev.target.closest('.row');
    if (!li || !li.dataset.sid || !lastPath) return;
    const st = lastPath.steps[Number(li.dataset.sid)];
    if (!st) return;
    if (ev.target.closest('[data-copy]')) { copy(stepText(st), 'Step copied'); return; }
    const head = ev.target.closest('.row-head');
    if (head) toggle(li, head, () => stepDetail(st, lastPath), openL);
  });
  $('lvActs').addEventListener('click', (ev) => { if (ev.target.id === 'copyPath' && lastPath) copy(pathText(lastPath), 'Plan copied'); });
  for (const k of TABS) $('tab-' + k).addEventListener('click', () => setTab(k, true));
  window.addEventListener('hashchange', () => setTab(location.hash.slice(1), false));
  window.addEventListener('resize', moveInk);
  $('tabs').addEventListener('scroll', tabEdges, { passive: true });

  // plan inputs
  $('budget').addEventListener('input', (ev) => { const v = Number(ev.target.value); if (!(v >= 0)) return; S.budget = v; save(); renderPlan(); });
  function addProf(k) {
    S.mine[k] = clampSkill(S.skills[k] ?? 75);
    save(); renderMine(); renderPlan();
  }
  $('addProf').addEventListener('change', (ev) => { if (ev.target.value !== '') addProf(ev.target.value); });
  $('planList').addEventListener('click', (ev) => { const b = ev.target.closest('[data-addprof]'); if (b) addProf(b.dataset.addprof); });
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
    PT = p; source = src; openL.clear();
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
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { syncAsk(); if (tab === 'plan') renderMine(); if (tab === 'recipes') fit($('rbProf')); if (tab === 'leveling') fit($('lvProf')); moveInk(); });
  // Fetch the latest scan where the page may reach AHledger (GitHub Pages); elsewhere keep the copy we have.
  if (source !== 'paste' && /^https?:$/.test(location.protocol)) {
    checking = true; renderHouse();
    loadLatest(store.get('fcp.market') || dotted(PT.market)).catch(() => {}).finally(() => { checking = false; renderHouse(); });
  }
})();
