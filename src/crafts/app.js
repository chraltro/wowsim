(function () {
  'use strict';
  const D = JSON.parse(document.getElementById('data').textContent);
  const E = makeEngine(D);
  const PROFS = D.profs;
  const SRC = ['Starter', 'Trainer', 'Recipe item'];
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
  const ALL = PROFS.map((_, i) => i);
  const DEF = { profs: ALL, maxSkill: 150, basis: 'med', sellTo: 'best', sort: 'profit', onlyProfit: true, trainerOnly: false, trim: true, hideThin: true, disc: '0', q: '', fq: '', fbasis: 'med' };
  let saved = {};
  try { saved = JSON.parse(store.get('fcp.ui') || '{}') || {}; } catch (e) { saved = {}; }
  const S = Object.assign({}, DEF, saved);
  S.profs = new Set(Array.isArray(S.profs) ? S.profs.filter((i) => i >= 0 && i < PROFS.length) : ALL);
  const open = new Set();
  let limit = 60, limA = 25, limB = 25, limC = 15;
  let flipEvals = new Map();
  const save = () => store.set('fcp.ui', JSON.stringify(Object.assign({}, S, { profs: [...S.profs], q: '', fq: '' })));

  // ---------- formatting ----------
  function coinHTML(c, signed) {
    const k = coins(c);
    if (!k) return '<span class="coin">–</span>';
    const sign = k.neg ? '−' : (signed ? '+' : '');
    const cls = { g: 'ug', s: 'us', c: 'uc' };
    return '<span class="coin">' + sign + k.parts.map(([n, u]) => n + '<span class="u ' + cls[u] + '">' + u + '</span>').join('') + '</span>';
  }
  const fmtInt = (n) => (n == null ? '–' : n >= 10000 ? (n / 1000).toFixed(0) + 'k' : n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n));
  const fmtDay = (s) => (s == null ? null : s >= 10 ? Math.round(s) : s >= 1 ? s.toFixed(1).replace(/\.0$/, '') : s.toFixed(1));
  const pct = (x) => (x == null ? '' : (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(Math.round(x * 100)) + '%');
  const itemName = (id) => { const it = E.items.get(id); return it ? it[0] : 'Item ' + id; };
  const itemQ = (id) => { const it = E.items.get(id); return it ? Math.min(it[1], 5) : 1; };
  const ahlLink = (id) => 'https://ahledger.com/items/' + id + '/' + PT.market.replace(/\//g, '.') + '?utm_source=forever_craft_profits';
  function age(ts) {
    const h = (Date.now() - ts) / 36e5;
    if (h < 1) return 'under an hour ago';
    if (h < 36) return Math.round(h) + (Math.round(h) === 1 ? ' hour ago' : ' hours ago');
    const d = Math.round(h / 24);
    return d + (d === 1 ? ' day ago' : ' days ago');
  }
  const when = (ts) => new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(ts));

  function renderMarketLine() {
    const fresh = Date.now() - PT.ts < 12 * 36e5;
    const src = { live: 'live from AHledger', cache: 'last loaded copy', paste: 'your pasted prices', snapshot: 'built-in copy' }[source];
    $('marketLine').innerHTML = '<b>' + esc(marketLabel(PT)) + '</b><span class="fresh"><span class="dot' + (fresh ? ' ok' : '') + '"></span>Scanned ' +
      esc(when(PT.ts)) + ', ' + esc(age(PT.ts)) + ' · ' + (checking ? 'checking AHledger…' : src) + '</span>';
  }

  // ---------- controls ----------
  function renderProfChips() {
    const counts = PROFS.map(() => 0);
    for (const r of E.recipes) if (r.learn <= S.maxSkill) counts[r.prof]++;
    const all = S.profs.size === PROFS.length;
    let h = '<button type="button" class="chip" data-p="all" aria-pressed="' + all + '">All</button>';
    PROFS.forEach((p, i) => {
      h += '<button type="button" class="chip" data-p="' + i + '" aria-pressed="' + S.profs.has(i) + '">' + esc(p) + '<span class="ct">' + counts[i] + '</span></button>';
    });
    $('profChips').innerHTML = h;
  }
  function syncControls() {
    $('skill').value = S.maxSkill;
    $('skillOut').textContent = S.maxSkill;
    document.querySelectorAll('#skillTicks button').forEach((b) => b.setAttribute('aria-pressed', String(+b.dataset.skill === S.maxSkill)));
    document.querySelectorAll('.seg').forEach((seg) => {
      const k = seg.dataset.key;
      seg.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === S[k])));
    });
    $('onlyProfit').checked = !!S.onlyProfit;
    $('trainerOnly').checked = !!S.trainerOnly;
    $('trim').checked = !!S.trim;
    $('hideThin').checked = !!S.hideThin;
    $('ftrim').checked = !!S.trim;
    document.querySelectorAll('.regionName').forEach((n) => { n.textContent = String(PT.region || '').toUpperCase(); });
  }

  // ---------- crafts ----------
  let raf = 0;
  function schedule() { cancelAnimationFrame(raf); raf = requestAnimationFrame(render); }

  function card(e) {
    const r = e.r;
    const isOpen = open.has(r.sid);
    const yld = r.qmin === r.qmax ? (r.qmin > 1 ? '×' + r.qmin : '') : '×' + r.qmin + '–' + r.qmax;
    const pcls = e.profit > 0 ? 'pos' : e.profit < 0 ? 'neg' : '';
    const tags = [];
    tags.push('<span>' + esc(PROFS[r.prof]) + ' ' + r.learn + '</span>');
    tags.push(r.src === 2 ? '<span class="tag recipe">Recipe item</span>' : '<span class="tag">' + SRC[r.src] + '</span>');
    const stats = [];
    const sd = fmtDay(e.sold);
    if (sd != null) stats.push(sd + ' sold/day');
    if (e.via !== 'vendor' && e.trend != null && Math.abs(e.trend) >= 0.05) stats.push('7d ' + pct(e.trend));
    if (e.via === 'vendor') tags.push('<span class="tag vendor">Vendor it</span>');
    else if (e.sale && e.sale.trimmed) tags.push('<span class="tag warn">Trimmed</span>');
    const thin = e.via !== 'vendor' && e.listed <= 2;
    let listed = '<span class="' + (thin ? 'warnTxt' : '') + '">' + fmtInt(e.listed) + ' listed</span>';
    if (e.via === 'vendor') {
      let low = null;
      for (const p of e.c.parts) {
        if (p.src !== 'ah') continue;
        const q = (PT.map.get(p.id) || {}).qty || 0;
        if (!low || q < low.q) low = { id: p.id, q };
      }
      if (low) listed = '<span class="' + (low.q < 20 ? 'warnTxt' : '') + '">' + esc(itemName(low.id)) + ': ' + fmtInt(low.q) + ' listed</span>';
    }
    return '<li class="card' + (isOpen ? ' open' : '') + '" data-sid="' + r.sid + '">' +
      '<button type="button" class="card-head" aria-expanded="' + isOpen + '">' +
        '<div class="nm q' + itemQ(r.res) + '">' + esc(r.name) + (yld ? '<span class="yield">' + yld + '</span>' : '') + '</div>' +
        '<div class="fig"><div class="profit ' + pcls + '">' + coinHTML(e.profit, true) + '</div>' +
          '<div class="pct">' + (e.margin != null ? pct(e.margin) : '') + '</div>' +
          '<svg class="chev" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 6l4.5 4.5L12.5 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div>' +
        '<div class="meta">' + tags.join('') + '<span class="num">' + listed + (stats.length ? ' · ' + stats.join(' · ') : '') + '</span></div>' +
      '</button>' +
      '<div class="body"><div class="inner">' + (isOpen ? detail(e) : '') + '</div></div>' +
    '</li>';
  }

  function detail(e) {
    const r = e.r;
    const SRCT = { vendor: '<span class="tag vendor">Vendor</span>', ah: '<span class="tag">AH</span>', craft: '<span class="tag craft">Craft</span>' };
    let rows = '';
    for (const p of e.c.parts) {
      const lq = p.src === 'ah' ? (PT.map.get(p.id) || {}).qty : null;
      const eachBits = [];
      if (p.u != null && p.q > 1) eachBits.push(coinHTML(p.u) + ' each');
      if (lq != null) eachBits.push(fmtInt(lq) + ' listed');
      const each = eachBits.length ? '<span class="each">' + eachBits.join(' · ') + '</span>' : '';
      const via = p.src === 'craft' && p.via ? '<span class="each">Cheaper to craft than to buy' + (p.via.name !== itemName(p.id) ? ' (' + esc(p.via.name) + ')' : '') + '</span>' : '';
      rows += '<tr><td class="qn">' + p.q + '×</td><td><span class="q' + itemQ(p.id) + '">' + esc(itemName(p.id)) + '</span>' + via + '</td>' +
        '<td class="src">' + (p.src ? SRCT[p.src] : '<span class="tag none">No price</span>') + '</td>' +
        '<td class="amt">' + (p.u != null ? coinHTML(p.u * p.q) + each : '–') + '</td></tr>';
    }
    rows += '<tr class="sum"><td colspan="3">Materials</td><td class="amt">' + (e.c.cost != null ? coinHTML(e.c.cost) : '–') + '</td></tr>';
    const yTxt = e.y !== 1 ? ' × ' + (Number.isInteger(e.y) ? e.y : e.y.toFixed(1)) : '';
    if (e.via === 'vendor') {
      rows += '<tr><td colspan="3">Vendor pays ' + coinHTML(e.vend / e.y) + yTxt + '</td><td class="amt">' + coinHTML(e.vend) + '</td></tr>';
    } else if (e.sale && e.sale.trimmed) {
      rows += '<tr><td colspan="3">Counted at ' + coinHTML(e.a) + yTxt + ' on the AH, less 5%<span class="each">Listed here at ' + coinHTML(e.sale.raw) +
        '; other ' + esc(String(PT.region).toUpperCase()) + ' houses sit near ' + coinHTML(e.sale.ref) + '</span></td><td class="amt">' + coinHTML(e.ahNet) + '</td></tr>';
    } else {
      rows += '<tr><td colspan="3">Sells for ' + coinHTML(e.a) + yTxt + ' on the AH, less 5%</td><td class="amt">' + coinHTML(e.ahNet) + '</td></tr>';
    }
    rows += '<tr class="total"><td colspan="3">Profit per craft</td><td class="amt ' + (e.profit > 0 ? 'pos' : 'neg') + '">' + coinHTML(e.profit, true) + '</td></tr>';
    const facts = [];
    if (e.via !== 'vendor') facts.push(['Vendor pays', e.vend > 0 ? coinHTML(e.vend) + (e.y !== 1 ? ' for the batch' : '') : 'Nothing']);
    else if (e.ahNet != null) facts.push(['AH after cut', coinHTML(e.ahNet)]);
    if (e.r.yellow && e.r.grey) facts.push(['Skill-ups', 'Orange to ' + e.r.yellow + ', grey at ' + e.r.grey]);
    if (r.ritem) {
      const rp = PT.map.get(r.ritem);
      const it = E.items.get(r.ritem);
      const bits = [];
      const vu = it && it[3] && (it[4] & (PT.faction === 'horde' ? 2 : 1)) ? it[3] : null;
      if (vu) bits.push('vendor ' + coinHTML(vu) + (it[5] ? ' (limited)' : ''));
      if (rp && rp.min != null) bits.push('AH from ' + coinHTML(rp.min));
      facts.push(['Recipe', '<span class="q' + itemQ(r.ritem) + '">' + esc(itemName(r.ritem)) + '</span>' + (bits.length ? ' · ' + bits.join(' · ') : '')]);
    }
    if (e.sale && e.sale.ref != null && !e.sale.trimmed && e.via !== 'vendor') facts.push(['Other houses', 'Around ' + coinHTML(e.sale.ref) + ' in ' + esc(String(PT.region).toUpperCase())]);
    if (e.via !== 'vendor' && e.listed <= 2) facts.push(['Heads-up', e.listed === 0 ? 'Nobody lists this here, so the price is a guess.' : 'Only ' + e.listed + ' listed here, so the price is one seller asking.']);
    if (e.perDay != null) facts.push(['Per day', coinHTML(e.perDay, true) + ' if you sold all ' + fmtDay(e.sold) + ' a day']);
    return '<div class="detail"><table class="calc">' + rows + '</table>' +
      '<dl class="facts">' + facts.map(([k, v]) => '<dt>' + k + '</dt><dd>' + v + '</dd>').join('') + '</dl>' +
      '<a class="ext" href="' + ahlLink(r.res) + '" target="_blank" rel="noopener">Price history on AHledger</a></div>';
  }

  let lastEvals = new Map();
  let showUnpriced = false;
  function render() {
    const ctx = E.context(PT, { basis: S.basis, sellTo: S.sellTo, maxSkill: S.maxSkill, trim: S.trim, disc: Number(S.disc) });
    const q = S.q.trim().toLowerCase();
    let pool = E.recipes.filter((r) => S.profs.has(r.prof) && r.learn <= S.maxSkill && (!S.trainerOnly || r.src !== 2));
    if (q) pool = pool.filter((r) => r.name.toLowerCase().includes(q) || r.reag.some(([id]) => itemName(id).toLowerCase().includes(q)));
    const evals = pool.map(ctx.evalRecipe);
    const isThin = (e) => e.via === 'ah' && e.listed <= 2 && (!e.sale || e.sale.ref == null);
    const thinCount = S.hideThin ? evals.filter((e) => e.profit != null && e.profit > 0 && isThin(e)).length : 0;
    const priced = evals.filter((e) => e.profit != null && !(S.hideThin && isThin(e)));
    const unpriced = evals.filter((e) => e.profit == null);
    const winners = priced.filter((e) => e.profit > 0);
    let shown = S.onlyProfit ? winners : priced;
    const key = { profit: (e) => e.profit, margin: (e) => e.margin ?? -Infinity, day: (e) => (e.perDay == null ? -Infinity : e.perDay) }[S.sort];
    shown = shown.slice().sort((a, b) => (key(b) - key(a)) || (b.profit - a.profit));
    if (showUnpriced) shown = shown.concat(unpriced);
    lastEvals = new Map(shown.map((e) => [e.r.sid, e]));

    const profTxt = S.profs.size === PROFS.length ? 'all professions' : S.profs.size === 1 ? PROFS[[...S.profs][0]] : S.profs.size + ' professions';
    let h = '<div class="big"><b class="num">' + winners.length + '</b> of <span class="num">' + priced.length + '</span> priced recipes turn a profit</div>';
    h += '<div class="small">Skill ' + S.maxSkill + ' and below in ' + esc(profTxt) + ', ' + (S.basis === 'med' ? 'median' : 'cheapest') + ' prices, selling to ' +
      ({ ah: 'the auction house', vendor: 'vendors', best: 'whichever pays more' }[S.sellTo]) + '.';
    if (thinCount) h += ' Hiding ' + thinCount + ' one-off listing' + (thinCount === 1 ? '' : 's') + ' that no other house backs up.';
    if (unpriced.length) h += ' <button type="button" class="linkish" id="toggleUnpriced">' + (showUnpriced ? 'Hide' : 'Show') + ' ' + unpriced.length + ' without enough prices</button>';
    h += '</div>';
    $('summary').innerHTML = h;

    if (!shown.length) {
      $('list').innerHTML = '<li class="empty">' + (q ? 'Nothing matches “' + esc(S.q) + '”.' : 'No profitable recipes with these settings. Raise the skill cap, switch prices to Cheapest, or allow vendor sales.') + '</li>';
      $('more').innerHTML = '';
      return;
    }
    $('list').innerHTML = shown.slice(0, limit).map(card).join('');
    $('more').innerHTML = shown.length > limit ? '<button type="button" class="btn" id="moreBtn">Show ' + Math.min(60, shown.length - limit) + ' more of ' + (shown.length - limit) + '</button>' : '';
  }

  // ---------- flips ----------
  function frow(name, q, id, metaHTML, profitHTML, sub) {
    return '<li><a class="frow" href="' + ahlLink(id) + '" target="_blank" rel="noopener">' +
      '<div class="nm q' + q + '">' + esc(name) + '</div>' +
      '<div class="fig"><div class="profit pos">' + profitHTML + '</div><div class="pct">' + sub + '</div></div>' +
      '<div class="meta">' + metaHTML + '</div></a></li>';
  }
  function renderFlips() {
    const ctx = E.context(PT, { basis: S.fbasis, sellTo: 'ah', maxSkill: 300, trim: S.trim, disc: Number(S.disc) });
    const vctx = E.context(PT, { basis: S.fbasis, sellTo: 'vendor', maxSkill: 300, trim: S.trim, disc: Number(S.disc) });
    const q = S.fq.trim().toLowerCase();
    const match = (id) => !q || itemName(id).toLowerCase().includes(q);
    const A = ctx.ahToVendor().filter((x) => match(x.id));
    const C = vctx.craftToVendor().filter((e) => !q || e.r.name.toLowerCase().includes(q) || e.r.reag.some(([id]) => itemName(id).toLowerCase().includes(q)));
    flipEvals = new Map(C.map((e) => [e.r.sid, e]));
    $('flipC').innerHTML = C.length ? C.slice(0, limC).map(card).join('') : '<li class="empty">No craft beats its materials at the vendor with these prices.</li>';
    $('moreC').innerHTML = C.length > limC ? '<button type="button" class="btn" id="moreC_btn">Show more of ' + (C.length - limC) + '</button>' : '';
    const B = ctx.vendorToAh().filter((x) => match(x.id));
    $('flipA').innerHTML = A.length ? A.slice(0, limA).map((x) => frow(itemName(x.id), itemQ(x.id), x.id,
      '<span class="num">Buy ' + coinHTML(x.buy) + ' · vendor pays ' + coinHTML(x.sell) + ' · ' + fmtInt(x.qty) + ' listed</span>',
      coinHTML(x.profit, true), 'each')).join('') : '<li class="empty">No listings below vendor price in the current scan.</li>';
    $('moreA').innerHTML = A.length > limA ? '<button type="button" class="btn" id="moreA_btn">Show more of ' + (A.length - limA) + '</button>' : '';
    $('flipB').innerHTML = B.length ? B.slice(0, limB).map((x) => {
      const sd = fmtDay(x.sold);
      return frow(itemName(x.id), itemQ(x.id), x.id,
        '<span class="num">Vendor ' + coinHTML(x.vendor) + ' · AH ' + coinHTML(x.ah) + ' · ' + fmtInt(x.qty) + ' listed' + (sd != null ? ' · ' + sd + ' sold/day' : ' · no sales data') + '</span>' +
        (x.trimmed ? ' <span class="tag warn">Trimmed from ' + coinHTML(x.raw) + '</span>' : '') +
        (x.limited ? ' <span class="tag warn">Limited stock</span>' : ''),
        coinHTML(x.profit, true), 'each after cut');
    }).join('') : '<li class="empty">No vendor items sell above vendor price here right now.</li>';
    $('moreB').innerHTML = B.length > limB ? '<button type="button" class="btn" id="moreB_btn">Show more of ' + (B.length - limB) + '</button>' : '';
  }

  // ---------- tabs ----------
  function setTab(t, push) {
    const flips = t === 'flips';
    $('view-crafts').hidden = flips;
    $('view-flips').hidden = !flips;
    $('tab-crafts').setAttribute('aria-selected', String(!flips));
    $('tab-flips').setAttribute('aria-selected', String(flips));
    $('tabs').dataset.at = flips ? 'flips' : 'crafts';
    if (flips) renderFlips();
    if (push && location.hash !== '#' + t) { try { history.replaceState(null, '', '#' + t); } catch (e) { location.hash = t; } }
  }

  // ---------- events ----------
  $('profChips').addEventListener('click', (ev) => {
    const b = ev.target.closest('.chip');
    if (!b) return;
    const p = b.dataset.p;
    if (p === 'all') S.profs = S.profs.size === PROFS.length ? new Set() : new Set(ALL);
    else { const i = +p; if (S.profs.has(i)) S.profs.delete(i); else S.profs.add(i); }
    limit = 60; save(); renderProfChips(); schedule();
  });
  $('skill').addEventListener('input', (ev) => {
    S.maxSkill = +ev.target.value; $('skillOut').textContent = S.maxSkill;
    document.querySelectorAll('#skillTicks button').forEach((b) => b.setAttribute('aria-pressed', String(+b.dataset.skill === S.maxSkill)));
    limit = 60; schedule();
  });
  $('skill').addEventListener('change', () => { save(); renderProfChips(); });
  $('skillTicks').addEventListener('click', (ev) => {
    const b = ev.target.closest('button'); if (!b) return;
    S.maxSkill = +b.dataset.skill; limit = 60; save(); syncControls(); renderProfChips(); schedule();
  });
  document.querySelectorAll('.seg').forEach((seg) => seg.addEventListener('click', (ev) => {
    const b = ev.target.closest('button'); if (!b) return;
    S[seg.dataset.key] = b.dataset.v; save(); syncControls();
    if (seg.dataset.key === 'fbasis') renderFlips();
    else if (seg.dataset.key === 'disc') { limit = 60; schedule(); if (!$('view-flips').hidden) renderFlips(); }
    else { limit = 60; schedule(); }
  }));
  $('onlyProfit').addEventListener('change', (ev) => { S.onlyProfit = ev.target.checked; limit = 60; save(); schedule(); });
  $('trainerOnly').addEventListener('change', (ev) => { S.trainerOnly = ev.target.checked; limit = 60; save(); schedule(); });
  $('hideThin').addEventListener('change', (ev) => { S.hideThin = ev.target.checked; limit = 60; save(); schedule(); });
  const setTrim = (v) => { S.trim = v; save(); syncControls(); limit = 60; schedule(); if (!$('view-flips').hidden) renderFlips(); };
  $('trim').addEventListener('change', (ev) => setTrim(ev.target.checked));
  $('ftrim').addEventListener('change', (ev) => setTrim(ev.target.checked));
  $('q').addEventListener('input', (ev) => { S.q = ev.target.value; limit = 60; schedule(); });
  $('fq').addEventListener('input', (ev) => { S.fq = ev.target.value; limA = 25; limB = 25; limC = 15; renderFlips(); });
  $('summary').addEventListener('click', (ev) => { if (ev.target.id === 'toggleUnpriced') { showUnpriced = !showUnpriced; render(); } });
  $('more').addEventListener('click', (ev) => { if (ev.target.id === 'moreBtn') { limit += 60; render(); } });
  $('moreA').addEventListener('click', (ev) => { if (ev.target.id === 'moreA_btn') { limA += 25; renderFlips(); } });
  $('moreB').addEventListener('click', (ev) => { if (ev.target.id === 'moreB_btn') { limB += 25; renderFlips(); } });
  $('moreC').addEventListener('click', (ev) => { if (ev.target.id === 'moreC_btn') { limC += 15; renderFlips(); } });
  function onCardClick(ev, getMap) {
    const head = ev.target.closest('.card-head');
    if (!head) return;
    const li = head.parentElement;
    const sid = +li.dataset.sid;
    const inner = li.querySelector('.inner');
    if (open.has(sid) && li.classList.contains('open')) {
      open.delete(sid); li.classList.remove('open'); head.setAttribute('aria-expanded', 'false');
    } else {
      const e = getMap().get(sid);
      if (e && !inner.firstChild) inner.innerHTML = detail(e);
      open.add(sid);
      void li.offsetHeight; // let the closed state paint first so the opening animates
      li.classList.add('open'); head.setAttribute('aria-expanded', 'true');
    }
  }
  $('list').addEventListener('click', (ev) => onCardClick(ev, () => lastEvals));
  $('flipC').addEventListener('click', (ev) => onCardClick(ev, () => flipEvals));
  $('tab-crafts').addEventListener('click', () => setTab('crafts', true));
  $('tab-flips').addEventListener('click', () => setTab('flips', true));
  window.addEventListener('hashchange', () => setTab(location.hash === '#flips' ? 'flips' : 'crafts', false));

  // ---------- update sheet ----------
  const sheet = $('sheet'), bg = $('sheetBg');
  let lastFocus = null;
  function houseId() { return 'forever.' + $('hRuleset').value + '.' + $('hFaction').value + '.' + $('hRegion').value; }
  function syncLink() { $('ptLink').href = 'https://api.ahledger.com/v1/pricetable/' + houseId(); }
  function openSheet() {
    lastFocus = document.activeElement;
    $('hRuleset').value = PT.ruleset; $('hFaction').value = PT.faction; $('hRegion').value = PT.region === 'us' ? 'us' : 'eu';
    syncLink();
    $('sheetIntro').textContent = 'Showing ' + marketLabel(PT) + ', scanned ' + age(PT.ts) + '. Pick a house and load its latest scan from AHledger.';
    $('pasteErr').textContent = ''; $('liveErr').textContent = '';
    sheet.hidden = false; bg.hidden = false;
    requestAnimationFrame(() => { sheet.classList.add('show'); bg.classList.add('show'); });
    setTimeout(() => $('loadLive').focus({ preventScroll: true }), 320);
  }
  function closeSheet() {
    sheet.classList.remove('show'); bg.classList.remove('show');
    setTimeout(() => { sheet.hidden = true; bg.hidden = true; if (lastFocus) lastFocus.focus({ preventScroll: true }); }, 320);
  }
  let toastT = 0;
  function toast(msg) {
    const t = $('toast'); t.textContent = msg; t.classList.add('show');
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 2600);
  }
  function applyPrices(p, src) {
    PT = p; source = src;
    renderMarketLine(); syncControls(); render();
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
    if (p.market === PT.market && p.ts === PT.ts) { source = 'live'; renderMarketLine(); }
    else applyPrices(p, 'live');
    return p;
  }
  $('updateBtn').addEventListener('click', openSheet);
  $('closeSheet').addEventListener('click', closeSheet);
  bg.addEventListener('click', closeSheet);
  document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape' && !sheet.hidden) closeSheet(); });
  ['hRuleset', 'hFaction', 'hRegion'].forEach((id) => $(id).addEventListener('change', syncLink));
  $('copyLink').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('ptLink').href); toast('Link copied'); }
    catch (e) { toast('Copy failed. Long-press the button above instead.'); }
  });
  $('loadLive').addEventListener('click', async () => {
    const b = $('loadLive');
    b.disabled = true; b.textContent = 'Loading…'; $('liveErr').textContent = '';
    try {
      const p = await loadLatest(houseId());
      closeSheet();
      toast('Loaded ' + marketLabel(p) + ', scanned ' + age(p.ts));
    } catch (e) {
      $('liveErr').textContent = e.name === 'AbortError' ? 'AHledger took too long to answer. Try again.'
        : e instanceof TypeError ? 'AHledger can\'t be reached from this page. Paste the table below instead.' : e.message;
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
    } catch (e) {
      $('pasteErr').textContent = e.message;
    }
  });
  $('restore').addEventListener('click', () => {
    store.del('fcp.prices'); store.del('fcp.source'); store.del('fcp.market'); applyPrices(SNAP, 'snapshot'); closeSheet(); toast('Back to the built-in prices');
  });

  // ---------- start ----------
  if (/github\.io$/.test(location.hostname)) $('siteLink').href = '../';
  $('buildNo').textContent = D.build;
  renderMarketLine();
  renderProfChips();
  syncControls();
  render();
  setTab(location.hash === '#flips' ? 'flips' : 'crafts', false);
  // Fetch the latest scan where the page may reach AHledger (GitHub Pages); elsewhere keep the copy we have.
  if (source !== 'paste' && /^https?:$/.test(location.protocol)) {
    checking = true; renderMarketLine();
    loadLatest(store.get('fcp.market') || dotted(PT.market)).catch(() => {}).finally(() => { checking = false; renderMarketLine(); });
  }
})();
