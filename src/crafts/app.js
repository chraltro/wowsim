(function () {
  'use strict';
  const D = JSON.parse(document.getElementById('data').textContent);
  const E = makeEngine(D);
  const PROFS = D.profs;
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
  const DEF = { prof: 'all', skills: { all: 150 }, basis: 'med', sellTo: 'best', sort: 'profit', onlyProfit: true, trainerOnly: false, trim: true, hideThin: true, disc: '0' };
  let saved = {};
  try { saved = JSON.parse(store.get('fcp.ui') || '{}') || {}; } catch (e) { saved = {}; }
  const S = Object.assign({}, DEF, saved);
  S.skills = Object.assign({ all: Number(saved.maxSkill) || 150 }, saved.skills || {});
  if (S.prof !== 'all' && !(Number(S.prof) >= 0 && Number(S.prof) < PROFS.length)) S.prof = 'all';
  if (!['profit', 'margin', 'skill'].includes(S.sort)) S.sort = 'profit';
  let q = '', fq = '';
  const open = new Set();
  const qty = new Map();
  let limit = 60, limA = 25, limB = 25, limC = 15;
  const save = () => store.set('fcp.ui', JSON.stringify({ prof: S.prof, skills: S.skills, basis: S.basis, sellTo: S.sellTo, sort: S.sort, onlyProfit: S.onlyProfit, trainerOnly: S.trainerOnly, trim: S.trim, hideThin: S.hideThin, disc: S.disc }));
  const single = () => S.prof !== 'all';
  const skillNow = () => { const v = Number(S.skills[S.prof] ?? S.skills.all); return Math.min(300, Math.max(1, v || 150)); };
  const ctxOpts = (over) => Object.assign({ basis: S.basis, sellTo: S.sellTo, maxSkill: skillNow(), trim: S.trim, disc: Number(S.disc) }, over);

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
  const ahlLink = (id) => 'https://ahledger.com/items/' + id + '/' + dotted(PT.market) + '?utm_source=forever_craft_profits';
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
    document.querySelectorAll('.regionName').forEach((n) => { n.textContent = String(PT.region || '').toUpperCase(); });
  }

  // ---------- the question ----------
  const measure = $('measure');
  function fit(sel) {
    measure.textContent = sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : '';
    sel.style.width = Math.ceil(measure.getBoundingClientRect().width) + 'px';
  }
  function buildProfSelect() {
    const counts = PROFS.map(() => 0);
    for (const r of E.recipes) counts[r.prof]++;
    $('prof').innerHTML = '<option value="all">all professions</option>' +
      PROFS.map((p, i) => (counts[i] ? '<option value="' + i + '">' + esc(p) + '</option>' : '')).join('');
  }
  function syncAsk() {
    $('prof').value = S.prof;
    $('skill').value = skillNow();
    $('skillWord').textContent = single() ? 'at skill' : 'up to skill';
    $('sellTo').value = S.sellTo;
    const so = $('sort');
    so.querySelector('[value="skill"]').disabled = !single();
    so.value = S.sort === 'skill' && !single() ? 'profit' : S.sort;
    ['prof', 'sellTo', 'sort'].forEach((id) => fit($(id)));
  }
  function syncSettings() {
    $('basis').value = S.basis; $('disc').value = S.disc;
    $('trim').checked = !!S.trim; $('onlyProfit').checked = !!S.onlyProfit; $('trainerOnly').checked = !!S.trainerOnly; $('hideThin').checked = !!S.hideThin;
  }

  // ---------- rows ----------
  function difficulty(r, skill) {
    const ch = skillChance(r, skill);
    if (ch == null) return null;
    const mid = Math.round((r.yellow + r.grey) / 2);
    if (skill < r.yellow) return { tick: 'orange', text: 'orange until ' + r.yellow };
    if (skill < mid) return { tick: 'yellow', text: 'yellow until ' + mid };
    if (skill < r.grey) return { tick: 'green', text: 'green until ' + r.grey };
    return { tick: 'grey', text: 'grey, no skill-ups' };
  }
  function row(e, view) {
    const r = e.r;
    const isOpen = open.has(r.sid);
    const yld = r.qmin === r.qmax ? (r.qmin > 1 ? '×' + r.qmin : '') : '×' + r.qmin + ' to ' + r.qmax;
    const diff = view.single ? difficulty(r, view.skill) : null;
    let left = view.single ? 'Skill ' + r.learn + (diff ? ', ' + diff.text : '') : PROFS[r.prof] + ' ' + r.learn;
    if (r.src === 2) left += ', needs recipe';
    let right;
    if (view.sort === 'margin' && e.margin != null) right = pct(e.margin) + ' on cost';
    else if (view.sort === 'skill') right = e.perPoint > 0 ? coin(e.perPoint) + ' a point' : 'pays for itself';
    else if (e.via === 'vendor') right = 'to a vendor';
    else if (e.profit == null) right = 'no price';
    else right = '<span class="' + (e.listed <= 2 ? 'warn' : '') + '">' + fmtInt(e.listed) + ' on AH' + (e.sale && e.sale.trimmed ? ', capped' : '') + '</span>';
    return '<li class="row' + (isOpen ? ' open' : '') + '" data-sid="' + r.sid + '">' +
      '<button type="button" class="row-head" aria-expanded="' + isOpen + '"' + (diff ? ' style="--tick:var(--d-' + diff.tick + ')"' : '') + '>' +
        '<span class="nm q' + itemQ(r.res) + '">' + esc(r.name) + (yld ? '<span class="yield">' + yld + '</span>' : '') + '</span>' +
        '<span class="amt ' + (e.profit > 0 ? 'pos' : e.profit < 0 ? 'neg' : '') + '">' + coin(e.profit, true) + '</span>' +
        '<span class="sub">' + esc(left) + '</span><span class="sub r">' + right + '</span>' +
      '</button>' +
      '<div class="body"><div class="inner">' + (isOpen ? detail(e, view) : '') + '</div></div>' +
    '</li>';
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
    } else if (e.ahNet != null) {
      rows += '<tr><td></td><td colspan="2">Sells on the AH, ' + count + coin(e.a) + ' less 5%' +
        (e.sale && e.sale.trimmed ? '<small>Listed here at ' + coin(e.sale.raw) + '. Other ' + esc(String(PT.region).toUpperCase()) + ' houses sit near ' + coin(e.sale.ref) + ', so it counts at twice that.</small>' : '') +
        '</td><td class="amt">' + coin(e.ahNet * n) + '</td></tr>';
    }
    if (e.profit != null) {
      rows += '<tr class="total"><td></td><td colspan="2">Profit' + (n > 1 ? ' for ' + n : '') + '</td><td class="amt ' + (e.profit > 0 ? 'pos' : 'neg') + '">' + coin(e.profit * n, true) + '</td></tr>';
    }

    let stock = '';
    if (isFinite(plan.stock)) {
      stock = plan.stock < n ? '<span class="warn">Only enough listed for ' + plan.stock + '</span>' : 'Enough listed for ' + fmtInt(plan.stock);
    }
    const notes = [];
    if (r.ritem) {
      const it = E.items.get(r.ritem), rp = PT.map.get(r.ritem);
      const vu = view.ctx.vendorUnit(r.ritem);
      const bits = [];
      if (vu != null) bits.push('a vendor sells it for ' + coin(vu) + (it && it[5] ? ' in limited stock' : ''));
      if (rp && rp.min != null) bits.push('the AH has it from ' + coin(rp.min));
      notes.push('Taught by <span class="q' + itemQ(r.ritem) + '">' + esc(itemName(r.ritem)) + '</span>' + (bits.length ? ': ' + bits.join(', and ') + '.' : ', which is not on the AH right now.'));
    }
    if (e.via === 'ah' && e.listed <= 2) notes.push('<span class="warn">' + (e.listed === 0 ? 'Nobody lists this here, so the price is a guess.' : 'Only ' + e.listed + ' listed here, so the price is one seller asking.') + '</span>');
    if (e.via === 'ah' && e.listed > 2 && made > e.listed) notes.push('<span class="warn">' + trimNum(made) + ' is more than the ' + e.listed + ' already listed. Expect to undercut to sell them all.</span>');
    if (e.via === 'ah' && e.sale && e.sale.ref != null && !e.sale.trimmed) notes.push('Other ' + esc(String(PT.region).toUpperCase()) + ' houses list it around ' + coin(e.sale.ref) + '.');
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

  function shoppingText(e, view) {
    const r = e.r, n = qty.get(r.sid) || 1;
    const plan = view.ctx.plan(r, n);
    const lines = [r.name + ' x' + n + ' (' + PROFS[r.prof] + ')'];
    const group = (src, title) => {
      const xs = plan.buy.filter((b) => b.src === src);
      if (!xs.length) return;
      lines.push('', title);
      for (const b of xs) lines.push(b.q + ' ' + itemName(b.id) + (b.u != null ? '  (' + coinText(b.u) + ' each)' : ''));
    };
    group('ah', 'Buy on the auction house:');
    group('vendor', 'Buy from a vendor:');
    group(null, 'No price found:');
    if (plan.steps.length) { lines.push('', 'Craft first:'); for (const s of plan.steps) lines.push(s.n + ' x ' + s.r.name); }
    if (plan.cost != null) lines.push('', 'Materials about ' + coinText(plan.cost) + '. ' + (e.profit != null ? 'Profit about ' + coinText(e.profit * n) + (e.via === 'vendor' ? ' sold to a vendor.' : ' on the AH after the cut.') : ''));
    return lines.join('\n');
  }

  // ---------- crafts ----------
  let raf = 0;
  function schedule() { cancelAnimationFrame(raf); raf = requestAnimationFrame(render); }
  let craftsView = null, craftsEvals = new Map(), showUnpriced = false;
  function render() {
    const skill = skillNow(), one = single(), pi = Number(S.prof);
    const sort = S.sort === 'skill' && !one ? 'profit' : S.sort;
    const ctx = E.context(PT, ctxOpts());
    const view = craftsView = { ctx, single: one, skill, sort };
    const s = q.trim().toLowerCase();
    let pool = E.recipes.filter((r) => (!one || r.prof === pi) && r.learn <= skill && (!S.trainerOnly || r.src !== 2));
    if (s) pool = pool.filter((r) => r.name.toLowerCase().includes(s) || r.reag.some(([id]) => itemName(id).toLowerCase().includes(s)));
    const evals = pool.map(ctx.evalRecipe);
    const isThin = (e) => e.via === 'ah' && e.listed <= 2 && (!e.sale || e.sale.ref == null);
    const thin = S.hideThin ? evals.filter((e) => e.profit != null && e.profit > 0 && isThin(e)).length : 0;
    const priced = evals.filter((e) => e.profit != null && !(S.hideThin && isThin(e)));
    const unpriced = evals.filter((e) => e.profit == null);
    const winners = priced.filter((e) => e.profit > 0);
    let shown, tally;
    if (sort === 'skill') {
      shown = priced.filter((e) => { const ch = skillChance(e.r, skill); if (!ch) return false; e.perPoint = -e.profit / ch; return true; })
        .sort((a, b) => a.perPoint - b.perPoint);
      const free = shown.filter((e) => e.perPoint <= 0).length;
      tally = '<b>' + shown.length + '</b> ' + (shown.length === 1 ? 'recipe still gives' : 'recipes still give') + ' skill points at ' + skill + ', cheapest per point first.' +
        (free ? ' ' + free + (free === 1 ? ' pays' : ' pay') + ' for ' + (free === 1 ? 'itself.' : 'themselves.') : '');
    } else {
      shown = (S.onlyProfit ? winners : priced).slice();
      const key = sort === 'margin' ? (e) => e.margin ?? -Infinity : (e) => e.profit;
      shown.sort((a, b) => (key(b) - key(a)) || (b.profit - a.profit));
      tally = '<b>' + winners.length + '</b> of ' + priced.length + ' recipes make money.';
      if (thin) tally += ' ' + thin + ' one-off ' + (thin === 1 ? 'listing is' : 'listings are') + ' hidden.';
    }
    if (unpriced.length) tally += ' <button type="button" class="textbtn" id="toggleUnpriced">' + (showUnpriced ? 'Hide' : 'Show') + ' ' + unpriced.length + ' without a price</button>';
    if (showUnpriced) shown = shown.concat(unpriced);
    craftsEvals = new Map(shown.map((e) => [e.r.sid, e]));
    $('summary').innerHTML = tally;
    if (!shown.length) {
      $('list').innerHTML = '<li class="empty">' + (s ? 'Nothing matches “' + esc(q) + '”.' : 'Nothing makes money with these settings. Raise the skill, or open Settings and price from the cheapest listing.') + '</li>';
      $('more').innerHTML = '';
      return;
    }
    $('list').innerHTML = shown.slice(0, limit).map((e) => row(e, view)).join('');
    $('more').innerHTML = shown.length > limit ? '<button type="button" class="btn" id="moreBtn">Show ' + Math.min(60, shown.length - limit) + ' more</button>' : '';
  }

  // ---------- flips ----------
  let flipView = null, flipEvals = new Map();
  function flat(name, qcls, amount, left, right) {
    return '<li class="row"><div class="row-head"><span class="nm q' + qcls + '">' + esc(name) + '</span><span class="amt pos">' + amount + '</span>' +
      '<span class="sub">' + left + '</span><span class="sub r">' + right + '</span></div></li>';
  }
  function renderFlips() {
    const ctx = E.context(PT, ctxOpts({ sellTo: 'ah', maxSkill: 300 }));
    const vctx = E.context(PT, ctxOpts({ sellTo: 'vendor', maxSkill: 300 }));
    flipView = { ctx: vctx, single: false, skill: 300, sort: 'profit' };
    const s = fq.trim().toLowerCase();
    const match = (id) => !s || itemName(id).toLowerCase().includes(s);
    const A = ctx.ahToVendor().filter((x) => match(x.id));
    $('flipA').innerHTML = A.length ? A.slice(0, limA).map((x) => {
      const few = x.med != null && x.med >= x.sell;
      return flat(itemName(x.id), itemQ(x.id), 'up to ' + coin(x.profit, true),
        'Buy under ' + coin(x.sell) + ', cheapest is ' + coin(x.buy),
        x.qty <= 1 ? '1 listed' : (few ? 'fewer than half of ' : 'most of ') + fmtInt(x.qty));
    }).join('') : '<li class="empty">Nothing is listed under vendor price in this scan.</li>';
    $('moreA').innerHTML = A.length > limA ? '<button type="button" class="btn" id="moreA_btn">Show more</button>' : '';

    const C = vctx.craftToVendor().filter((e) => !s || e.r.name.toLowerCase().includes(s) || e.r.reag.some(([id]) => itemName(id).toLowerCase().includes(s)));
    flipEvals = new Map(C.map((e) => [e.r.sid, e]));
    $('flipC').innerHTML = C.length ? C.slice(0, limC).map((e) => row(e, flipView)).join('') : '<li class="empty">No craft beats its materials at the vendor with these prices.</li>';
    $('moreC').innerHTML = C.length > limC ? '<button type="button" class="btn" id="moreC_btn">Show more</button>' : '';

    const B = ctx.vendorToAh().filter((x) => match(x.id));
    $('flipB').innerHTML = B.length ? B.slice(0, limB).map((x) => flat(itemName(x.id), itemQ(x.id), coin(x.profit, true),
      'Vendor ' + coin(x.vendor) + (x.limited ? ', limited stock' : '') + ', AH ' + coin(x.ah) + (x.trimmed ? ' capped from ' + coin(x.raw) : ''),
      '<span class="' + (x.qty <= 2 ? 'warn' : '') + '">' + fmtInt(x.qty) + ' on AH</span>')).join('')
      : '<li class="empty">No vendor goods list above vendor price here right now.</li>';
    $('moreB').innerHTML = B.length > limB ? '<button type="button" class="btn" id="moreB_btn">Show more</button>' : '';
  }

  // ---------- tabs ----------
  function moveInk() {
    const b = document.querySelector('.tabs button[aria-selected="true"]');
    $('tabInk').style.width = b.offsetWidth + 'px';
    $('tabInk').style.transform = 'translateX(' + b.offsetLeft + 'px)';
  }
  function setTab(t, push) {
    const flips = t === 'flips';
    $('view-crafts').hidden = flips; $('view-flips').hidden = !flips;
    $('tab-crafts').setAttribute('aria-selected', String(!flips));
    $('tab-flips').setAttribute('aria-selected', String(flips));
    moveInk();
    if (flips) renderFlips();
    if (push && location.hash !== '#' + t) { try { history.replaceState(null, '', '#' + t); } catch (e) { location.hash = t; } }
  }
  const rerender = () => { limit = 60; schedule(); if (!$('view-flips').hidden) renderFlips(); };

  // ---------- events ----------
  $('prof').addEventListener('change', (ev) => {
    S.prof = ev.target.value;
    if (S.skills[S.prof] == null) S.skills[S.prof] = skillNow();
    save(); syncAsk(); open.clear(); rerender();
  });
  $('skill').addEventListener('input', (ev) => {
    const v = Math.round(Number(ev.target.value));
    if (!(v >= 1 && v <= 300)) return;
    S.skills[S.prof] = v; save(); rerender();
  });
  $('skill').addEventListener('blur', () => { $('skill').value = skillNow(); });
  $('skill').addEventListener('focus', (ev) => ev.target.select());
  $('sellTo').addEventListener('change', (ev) => { S.sellTo = ev.target.value; save(); syncAsk(); rerender(); });
  $('sort').addEventListener('change', (ev) => { S.sort = ev.target.value; save(); syncAsk(); rerender(); });
  $('q').addEventListener('input', (ev) => { q = ev.target.value; limit = 60; schedule(); });
  $('fq').addEventListener('input', (ev) => { fq = ev.target.value; limA = 25; limB = 25; limC = 15; renderFlips(); });
  $('summary').addEventListener('click', (ev) => { if (ev.target.id === 'toggleUnpriced') { showUnpriced = !showUnpriced; render(); } });
  $('more').addEventListener('click', (ev) => { if (ev.target.id === 'moreBtn') { limit += 60; render(); } });
  $('moreA').addEventListener('click', (ev) => { if (ev.target.id === 'moreA_btn') { limA += 25; renderFlips(); } });
  $('moreB').addEventListener('click', (ev) => { if (ev.target.id === 'moreB_btn') { limB += 25; renderFlips(); } });
  $('moreC').addEventListener('click', (ev) => { if (ev.target.id === 'moreC_btn') { limC += 15; renderFlips(); } });

  function onLedgerClick(ev, getMap, getView) {
    const li = ev.target.closest('.row');
    if (!li || !li.dataset.sid) return;
    const sid = Number(li.dataset.sid);
    const e = getMap().get(sid);
    if (!e) return;
    const inner = li.querySelector('.inner');
    const step = ev.target.closest('[data-step]');
    if (step) {
      qty.set(sid, Math.min(999, Math.max(1, (qty.get(sid) || 1) + Number(step.dataset.step))));
      inner.innerHTML = detail(e, getView());
      return;
    }
    if (ev.target.closest('[data-copy]')) {
      const text = shoppingText(e, getView());
      navigator.clipboard.writeText(text).then(() => toast('Shopping list copied'), () => toast('Copying is blocked here. Select the bill and copy it by hand.'));
      return;
    }
    const head = ev.target.closest('.row-head');
    if (!head) return;
    if (li.classList.contains('open')) {
      open.delete(sid); li.classList.remove('open'); head.setAttribute('aria-expanded', 'false');
    } else {
      inner.innerHTML = detail(e, getView());
      open.add(sid);
      void li.offsetHeight; // paint the closed state first so the opening animates
      li.classList.add('open'); head.setAttribute('aria-expanded', 'true');
    }
  }
  $('list').addEventListener('click', (ev) => onLedgerClick(ev, () => craftsEvals, () => craftsView));
  $('flipC').addEventListener('click', (ev) => onLedgerClick(ev, () => flipEvals, () => flipView));
  $('tab-crafts').addEventListener('click', () => setTab('crafts', true));
  $('tab-flips').addEventListener('click', () => setTab('flips', true));
  window.addEventListener('hashchange', () => setTab(location.hash === '#flips' ? 'flips' : 'crafts', false));
  window.addEventListener('resize', () => { moveInk(); });

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
    if (!$('view-flips').hidden) renderFlips();
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
  $('copyLink').addEventListener('click', () => {
    navigator.clipboard.writeText($('ptLink').href).then(() => toast('Link copied'), () => toast('Copying is blocked here. Long-press the button beside it.'));
  });
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
  setTab(location.hash === '#flips' ? 'flips' : 'crafts', false);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { syncAsk(); moveInk(); });
  // Fetch the latest scan where the page may reach AHledger (GitHub Pages); elsewhere keep the copy we have.
  if (source !== 'paste' && /^https?:$/.test(location.protocol)) {
    checking = true; renderHouse();
    loadLatest(store.get('fcp.market') || dotted(PT.market)).catch(() => {}).finally(() => { checking = false; renderHouse(); });
  }
})();
