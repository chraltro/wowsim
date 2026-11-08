(function(){
'use strict';
const $ = s => document.querySelector(s);
const fmt = (n, d) => (n === null || n === undefined || !isFinite(n)) ? '–' : Number(n).toLocaleString('en-US', {maximumFractionDigits: d||0, minimumFractionDigits: d||0});
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const toast = msg => { const t = $('#toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('on'), 2200); };
const store = {get(k,d){ try{ const v = localStorage.getItem('foreversim:'+k); return v ? JSON.parse(v) : d; }catch(e){ return d; } }, set(k,v){ try{ localStorage.setItem('foreversim:'+k, JSON.stringify(v)); }catch(e){} }};
const CLASS_LABEL = {warrior:'Warrior', paladin:'Paladin', hunter:'Hunter', rogue:'Rogue', priest:'Priest', shaman:'Shaman', mage:'Mage', warlock:'Warlock', druid:'Druid'};
const secs = v => !isFinite(v) ? '–' : v >= 59.5 ? fmt(v/60,1)+' min' : fmt(v, v < 10 ? 1 : 0)+' s';
const SLOT_LABEL = {head:'Head',neck:'Neck',shoulder:'Shoulder',back:'Back',chest:'Chest',wrist:'Wrist',hands:'Hands',waist:'Waist',legs:'Legs',feet:'Feet',finger1:'Ring',finger2:'Ring',trinket1:'Trinket',trinket2:'Trinket',mainhand:'Main hand',offhand:'Off hand',ranged:'Ranged'};
const statLabel = {int:'Int',spi:'Spi',sta:'Sta',str:'Str',agi:'Agi',healing:'Heal',spellDamage:'Spell dmg',mp5:'Mp5',critRating:'Crit',hitRating:'Hit',ap:'AP',rangedAp:'RAP',armor:'Armor',defenseRating:'Def',dodgeRating:'Dodge',blockValue:'Block value'};
const statText = it => Object.entries(it.s||{}).filter(([k]) => statLabel[k]).map(([k,v]) => (k === 'armor' ? v : '+'+v)+' '+statLabel[k]).join(', ') + (it.w ? (it.s && Object.keys(it.s).length ? ', ' : '')+it.w.min+'-'+it.w.max+' @ '+it.w.speed : '');
const inEngine = id => ITEMS_ALL[id] && !ITEMS_ALL[id].ne;
const SHAMAN_SIM = /github\.io$/.test(location.hostname) ? '../shaman/' : 'https://claude.ai/artifact/HmiNY3CyCiiMqAeMS6kPRU';

// ---------- Characters ----------
const DEFAULT_SPEC = {warrior:'arms', paladin:'protection', hunter:'beast_mastery', rogue:'combat', priest:'shadow', shaman:'res', mage:'frost', warlock:'affliction', druid:'feral_combat'};
const DEFAULT_RACE = {warrior:'human', paladin:'human', hunter:'dwarf', rogue:'human', priest:'human', shaman:'dwarf', mage:'human', warlock:'human', druid:'night_elf'};
const uid = () => Math.random().toString(36).slice(2, 9);
function newChar(name, cls, level){ return {id: uid(), name, cls, race: DEFAULT_RACE[cls], spec: DEFAULT_SPEC[cls], route: 0, level, gear: null, autoGear: true}; }
let chars = store.get('chars', null);
if(!chars || !chars.length){
  const L = 8;
  chars = [newChar('Christian', 'shaman', L), newChar('Niels', 'warrior', L), newChar('Nicklas', 'druid', L), newChar('Mikkel', 'warlock', L),
           newChar('Cornelius', 'mage', L), newChar('Cornelius (alt)', 'hunter', L), newChar('Christian (alt)', 'paladin', L)];
}
let current = store.get('current', chars[0].id);
const save = () => { store.set('chars', chars); store.set('current', current); };
const cur = () => chars.find(c => c.id === current) || chars[0];
const results = {};   // id -> {quest, dungeon, key}

function specOf(c){ const cd = CLASSDATA[c.cls]; return cd.specs[c.spec] ? c.spec : Object.keys(cd.specs)[0]; }
function routeOf(c){ const sp = CLASSDATA[c.cls].specs[specOf(c)]; return sp.routes[Math.min(c.route||0, sp.routes.length-1)]; }
function gearOf(c){
  if(c.autoGear || !c.gear) return MCGear.typicalGear(ITEMS_ALL, c.cls, specOf(c), c.level, {inEngine});
  const out = {}; for(const k in c.gear){ const it = ITEMS_ALL[c.gear[k]]; if(it && inEngine(c.gear[k])) out[k] = c.gear[k]; } return out;
}
function ctxOf(c){ const r = routeOf(c); return {cls: c.cls, race: c.race, spec: specOf(c), level: c.level, route: r ? r.route : undefined, gear: gearOf(c), iterations: 150}; }
const keyOf = c => JSON.stringify(ctxOf(c));

// ---------- Engine ----------
let worker = null, engineReady = null, jobs = {}, jobN = 0;
function setEngineState(html){ $('#engineState').innerHTML = html; }
function startEngine(){
  if(engineReady) return engineReady;
  engineReady = (async () => {
    setEngineState('<div class="loader"><span class="spin"></span>Loading MythicSim\'s engine (5.6 MB)<span class="prog"><i id="eprog"></i></span></div>');
    const res = await fetch('engine.gz.wasm');   // the gzipped module; named .wasm so the host serves it
    if(!res.ok) throw new Error('could not load the engine ('+res.status+')');
    const total = +res.headers.get('content-length') || 5593068;
    let got = 0; const reader = res.body.getReader(); const parts = [];
    for(;;){ const {done, value} = await reader.read(); if(done) break; parts.push(value); got += value.length; const p = $('#eprog'); if(p) p.style.width = Math.min(100, got/total*100)+'%'; }
    const blob = new Blob(parts);
    const head = new Uint8Array(await blob.slice(0, 4).arrayBuffer());
    // Gzipped unless the host already decoded it (then it starts with the wasm magic "\0asm")
    const bytes = head[0] === 0x1f && head[1] === 0x8b ? await new Response(blob.stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer() : await blob.arrayBuffer();
    const module = await WebAssembly.compile(bytes);
    worker = new Worker(URL.createObjectURL(new Blob([$('#worker-src').textContent], {type: 'text/javascript'})));
    worker.onmessage = e => { const j = jobs[e.data.id]; if(!j) return; if(e.data.progress != null){ j.onProgress && j.onProgress(e.data.progress); return; } delete jobs[e.data.id]; e.data.error ? j.reject(new Error(e.data.error)) : j.resolve(e.data.result); };
    await call({type: 'init', module});
    setEngineState('');
    return true;
  })().catch(err => { setEngineState('<span class="warnline">The engine did not load: '+esc(err.message)+'</span>'); throw err; });
  return engineReady;
}
// The worker gets only the item records a job needs
function itemsFor(ids){ const o = {}; ids.forEach(id => { if(ITEMS_ALL[id]) o[id] = ITEMS_ALL[id]; }); return o; }
function call(msg, onProgress){ return new Promise((resolve, reject) => { const id = ++jobN; jobs[id] = {resolve, reject, onProgress}; worker.postMessage(Object.assign({id}, msg)); }); }
// Queue character runs one at a time, newest request per character wins
let queue = [], running = false;
function simChar(c){
  const key = keyOf(c);
  if(results[c.id] && results[c.id].key === key) return;
  results[c.id] = {key, pending: true};
  queue = queue.filter(x => x.id !== c.id); queue.push({id: c.id, key});
  pump();
}
async function pump(){
  if(running) return; running = true;
  try { await startEngine(); } catch(e){ running = false; return; }
  while(queue.length){
    const job = queue.shift(); const c = chars.find(x => x.id === job.id); if(!c) continue;
    const ctx = ctxOf(c); if(JSON.stringify(ctx) !== job.key) continue;
    try { const r = await call({type: 'char', ctx, items: itemsFor(Object.values(ctx.gear))}); results[c.id] = Object.assign({key: job.key}, r); }
    catch(err){ results[c.id] = {key: job.key, error: err.message}; }
    renderGroup(); if(c.id === current) renderResults();
  }
  running = false;
}

// ---------- Group view ----------
function renderGroup(){
  const L = groupLevel();
  $('#gLevel').value = L;
  const rows = chars.map(c => ({c, r: results[c.id]}));
  const maxKph = Math.max(1, ...rows.map(x => x.r && x.r.quest && x.r.quest.ok ? x.r.quest.perHour : 0));
  const cell = (x, f) => !x.r || x.r.pending ? '<span class="skel">000</span>' : x.r.error ? '<span class="warnline">error</span>' : f(x.r);
  $('#grpTable').innerHTML = '<thead><tr><th>Character</th><th class="hide-s">Talents</th><th>Level</th><th>Kills per hour</th><th class="hide-s">Per kill</th><th>Dungeon</th></tr></thead><tbody>'
    + rows.map(x => {
      const c = x.c, sp = CLASSDATA[c.cls].specs[specOf(c)];
      return '<tr class="cls-'+c.cls+'" data-id="'+c.id+'"><td class="nmc"><span class="cdot"></span> <b>'+esc(c.name)+'</b><span class="sub">'+esc(CLASSDATA[c.cls].races[c.race].label)+' '+CLASS_LABEL[c.cls]+'</span></td>'
        + '<td class="hide-s">'+esc(sp.label)+'</td><td>'+c.level+'</td>'
        + '<td>'+cell(x, r => r.quest && r.quest.ok ? fmt(r.quest.perHour)+'<div class="bar1" style="width:'+(r.quest.perHour/maxKph*100).toFixed(1)+'%"></div>' : '<span class="muted small">'+esc((r.quest && r.quest.why) || '–')+'</span>')+'</td>'
        + '<td class="hide-s">'+cell(x, r => r.quest && r.quest.ok ? secs(r.quest.kill)+' fighting<span class="sub">'+secs(r.quest.rest)+' resting</span>' : '–')+'</td>'
        + '<td>'+cell(x, r => r.dungeon && r.dungeon.ok ? (r.dungeon.role === 'healer' ? fmt(r.dungeon.hps)+'<span class="sub">healing per second</span>' : fmt(r.dungeon.dps)+'<span class="sub">damage per second'+(r.dungeon.role === 'tank' ? ', tank' : '')+'</span>') : '<span class="muted small">'+esc((r.dungeon && r.dungeon.why) || '–').slice(0, 80)+'</span>')+'</td></tr>';
    }).join('') + '</tbody>';
  $('#grpTable').querySelectorAll('tbody tr').forEach(tr => tr.addEventListener('click', () => { current = tr.dataset.id; save(); show('char'); renderChar(); }));
  $('#grpNote').textContent = 'Typical gear for each level unless you set a character\'s gear. Dungeon is a boss two levels above you for 2 minutes.';
}
function groupLevel(){ const ls = chars.map(c => c.level); return ls.sort((a,b) => a-b)[Math.floor(ls.length/2)] || 1; }
function setGroupLevel(L){ L = Math.max(1, Math.min(60, Math.round(+L || 1))); chars.forEach(c => c.level = L); save(); chars.forEach(simChar); renderGroup(); if($('#v-char').classList.contains('on')) renderChar(); }
$('#gDown').addEventListener('click', () => setGroupLevel(groupLevel() - 1));
$('#gUp').addEventListener('click', () => setGroupLevel(groupLevel() + 1));
$('#gLevel').addEventListener('change', e => setGroupLevel(e.target.value));

// ---------- Character view ----------
function renderPeople(){
  $('#people').innerHTML = chars.map(c => '<button class="person cls-'+c.cls+'" aria-pressed="'+(c.id === current)+'" data-id="'+c.id+'"><span class="nm"><span class="cdot"></span>'+esc(c.name)+'</span><span class="sb">'+c.level+' '+CLASS_LABEL[c.cls]+' · '+esc(CLASSDATA[c.cls].specs[specOf(c)].label)+'</span></button>').join('')
    + '<button class="person add" id="addChar">+ Add character</button>';
  $('#people').querySelectorAll('.person[data-id]').forEach(b => b.addEventListener('click', () => { current = b.dataset.id; save(); renderChar(); }));
  $('#addChar').addEventListener('click', () => { const c = newChar('New character', 'warrior', groupLevel()); chars.push(c); current = c.id; save(); renderChar(); simChar(c); renderGroup(); });
}
function renderChar(){
  const c = cur(); renderPeople();
  const cd = CLASSDATA[c.cls];
  $('#cName').value = c.name;
  $('#cClass').innerHTML = Object.keys(CLASSDATA).map(k => '<option value="'+k+'"'+(k === c.cls ? ' selected' : '')+'>'+CLASS_LABEL[k]+'</option>').join('');
  $('#cRace').innerHTML = Object.keys(cd.races).map(k => '<option value="'+k+'"'+(k === c.race ? ' selected' : '')+'>'+esc(cd.races[k].label)+'</option>').join('');
  $('#cSpec').innerHTML = Object.keys(cd.specs).map(k => '<option value="'+k+'"'+(k === specOf(c) ? ' selected' : '')+'>'+esc(cd.specs[k].label)+'</option>').join('');
  const sp = cd.specs[specOf(c)];
  $('#cRoute').innerHTML = sp.routes.map((r, i) => '<option value="'+i+'"'+(i === (c.route||0) ? ' selected' : '')+'>'+esc((r.site||'').replace(/ \(.*\)$/,'')+': '+(r.name||sp.label))+(r.problem ? ' (breaks the tree rules)' : '')+'</option>').join('');
  $('#cLevel').value = c.level; $('#cDown').disabled = c.level <= 1; $('#cUp').disabled = c.level >= 60;
  // Talent progress
  const r = routeOf(c), pts = Math.max(0, c.level - 9);
  if(!r) $('#cTalents').textContent = 'No leveling route published for this spec.';
  else {
    const t = MCRequest.talentsAt(r.route, pts), names = {}; cd.trees.forEach(tr => tr.talents.forEach(x => names[x[0]] = [x[1], x[2]]));
    const taken = r.route.map(x => x[0]).filter((id, i, a) => a.indexOf(id) === i && t[id]).map(id => '<b>'+esc(names[id][0])+'</b> '+t[id]+'/'+names[id][1]);
    let k = 0, next = null; for(const [id, n] of r.route){ if(pts < k + n){ next = [id, pts - k + 1]; break; } k += n; }
    $('#cTalents').innerHTML = (pts ? pts+' talent point'+(pts > 1 ? 's' : '')+': '+taken.join(', ') : 'No talent points before level 10.')
      + (next ? '<div class="nx">Next, at '+Math.max(10, c.level+1)+': '+esc(names[next[0]][0])+' '+next[1]+'/'+names[next[0]][1]+'</div>' : '')
      + '<div class="small" style="margin-top:4px">Route from <a href="'+esc(r.url)+'" target="_blank" rel="noopener">'+esc(r.site)+'</a>'+(r.updated ? ', '+esc(r.updated) : '')+'</div>';
  }
  $('#cRemove').innerHTML = chars.length > 1 ? '<button class="btn sm" id="delChar">Remove '+esc(c.name)+'</button>' : '';
  if($('#delChar')) $('#delChar').addEventListener('click', () => { chars = chars.filter(x => x.id !== c.id); current = chars[0].id; save(); renderChar(); renderGroup(); });
  renderGear(); renderResults(); $('#upList').innerHTML = ''; $('#upState').innerHTML = '';
  simChar(c);
}
function change(f){ const c = cur(); f(c); save(); renderChar(); renderGroup(); }
$('#cName').addEventListener('change', e => change(c => c.name = e.target.value.trim() || 'Unnamed'));
$('#cClass').addEventListener('change', e => change(c => { c.cls = e.target.value; c.race = DEFAULT_RACE[c.cls]; c.spec = DEFAULT_SPEC[c.cls]; c.route = 0; c.autoGear = true; c.gear = null; }));
$('#cRace').addEventListener('change', e => change(c => c.race = e.target.value));
$('#cSpec').addEventListener('change', e => change(c => { c.spec = e.target.value; c.route = 0; }));
$('#cRoute').addEventListener('change', e => change(c => c.route = +e.target.value));
const setLevel = L => change(c => c.level = Math.max(1, Math.min(60, Math.round(+L || 1))));
$('#cDown').addEventListener('click', () => setLevel(cur().level - 1));
$('#cUp').addEventListener('click', () => setLevel(cur().level + 1));
$('#cLevel').addEventListener('change', e => setLevel(e.target.value));

// ---------- Gear ----------
function renderGear(){
  const c = cur(), g = gearOf(c);
  $('#gearList').innerHTML = MCGear.SLOTS.map(k => {
    const it = ITEMS_ALL[g[k]];
    const blocked = k === 'offhand' && g.mainhand && ITEMS_ALL[g.mainhand] && ITEMS_ALL[g.mainhand].two;
    return '<div class="slot"><span class="sn">'+SLOT_LABEL[k]+'</span><div class="in">'
      + (it ? '<div class="nm q'+it.q+'">'+esc(it.n)+'</div><div class="st">'+esc(statText(it))+'</div>' : '<div class="nm empty">'+(blocked ? 'Two-hander equipped' : 'Empty')+'</div>')
      + '</div><div class="row" style="gap:6px;flex-wrap:nowrap">'+(blocked ? '' : '<button class="btn sm" data-pick="'+k+'">Change</button>')+(it ? '<button class="btn sm" data-clear="'+k+'" aria-label="Remove '+esc(it.n)+'">×</button>' : '')+'</div></div>';
  }).join('');
  $('#gearList').querySelectorAll('[data-pick]').forEach(b => b.addEventListener('click', () => openPicker(b.dataset.pick)));
  $('#gearList').querySelectorAll('[data-clear]').forEach(b => b.addEventListener('click', () => change(c => { c.gear = Object.assign({}, gearOf(c)); delete c.gear[b.dataset.clear]; c.autoGear = false; })));
  const n = Object.keys(g).length;
  $('#sum-gear').textContent = (c.autoGear ? 'Typical gear for level '+c.level : 'Your gear')+' · '+n+' item'+(n === 1 ? '' : 's');
  $('#gearNote').textContent = c.autoGear ? 'Easy-to-get items for this level, picked by rough stat value. Change any slot to use your own.' : '';
}
$('#autoGear').addEventListener('click', () => change(c => { c.autoGear = true; c.gear = null; }));
$('#clearGear').addEventListener('click', () => change(c => { c.autoGear = false; c.gear = {}; }));
let pickSlot = null, pickRows = [];
function openPicker(slot){
  const c = cur(); pickSlot = slot;
  $('#pickTitle').textContent = 'Choose '+SLOT_LABEL[slot].toLowerCase();
  $('#pickSearch').value = '';
  const w = MCGear.STYLE[(MCGear.STYLE_OF[c.cls]||{})[specOf(c)] || 'melee'];
  pickRows = Object.keys(ITEMS_ALL).filter(id => { const f = MCGear.wearFrom(ITEMS_ALL[id], c.cls, slot); return f !== null; }).map(id => {
    const it = ITEMS_ALL[id]; const from = MCGear.wearFrom(it, c.cls, slot); const reach = MCGear.reachLevel(it);
    let v = 0; for(const k in it.s) v += (w[k]||0)*it.s[k]; if(it.w) v += (it.w.min+it.w.max)/2/it.w.speed*(w.str ? 3 : w.agi ? 2.5 : 0.3);
    return {id: +id, it, ok: from <= c.level && reach <= c.level && inEngine(id), from, reach, v};
  }).sort((a, b) => (b.ok - a.ok) || (b.v - a.v));
  $('#pickNote').textContent = 'Items a level '+c.level+' '+CLASS_LABEL[c.cls]+' can wear and get, best rough stat value first. Search finds higher-level items too.';
  renderPicker(); $('#picker').classList.add('on'); setTimeout(() => $('#pickSearch').focus(), 60);
}
function renderPicker(){
  const q = $('#pickSearch').value.trim().toLowerCase();
  const rows = pickRows.filter(x => q ? x.it.n.toLowerCase().indexOf(q) >= 0 : x.ok).slice(0, 120);
  $('#pickList').innerHTML = rows.map(x => '<div class="pick" tabindex="0" data-id="'+x.id+'"><div><div class="q'+x.it.q+'" style="font-weight:600">'+esc(x.it.n)+(!inEngine(x.id) ? '<span class="needlv">not in the engine\'s data</span>' : x.from > cur().level ? '<span class="needlv">needs level '+x.from+'</span>' : x.reach > cur().level ? '<span class="needlv">level '+x.reach+' content</span>' : '')+'</div><div class="st">'+esc(statText(x.it))+(x.it.rl ? ' · req '+x.it.rl : '')+'</div><div class="st">'+esc(srcText(x.it))+'</div></div><div class="sc"></div></div>').join('') || '<div class="muted small" style="padding:12px">No items match.</div>';
  $('#pickList').querySelectorAll('.pick').forEach(el => {
    const choose = () => { const id = +el.dataset.id; change(c => { c.gear = Object.assign({}, gearOf(c)); c.gear[pickSlot] = id; if(pickSlot === 'mainhand' && ITEMS_ALL[id].two) delete c.gear.offhand; c.autoGear = false; }); closePicker(); };
    el.addEventListener('click', choose); el.addEventListener('keydown', e => { if(e.key === 'Enter') choose(); });
  });
}
function closePicker(){ $('#picker').classList.remove('on'); }
$('#pickSearch').addEventListener('input', renderPicker);
$('#pickClose').addEventListener('click', closePicker);
$('#picker').addEventListener('click', e => { if(e.target.id === 'picker') closePicker(); });
document.addEventListener('keydown', e => { if(e.key === 'Escape') closePicker(); });

// ---------- Results ----------
function renderResults(){
  const c = cur(), r = results[c.id];
  const pending = !r || r.pending;
  const kpi = (label, v, unit, d) => '<div class="kpi cls-'+c.cls+'" style="--bc:var(--cc)"><div class="lb">'+label+'</div><div class="v">'+(pending ? '<span class="skel">000</span>' : v)+'<small>'+unit+'</small></div><div class="d">'+(pending ? '' : d)+'</div></div>';
  if(r && r.error){ $('#charKpis').innerHTML = '<div class="note">The engine could not run this character: '+esc(r.error)+'</div>'; $('#charDetails').innerHTML = ''; return; }
  const q = r && r.quest, d = r && r.dungeon;
  const qv = q && q.ok ? fmt(q.perHour) : '–', qd = q && q.ok ? secs(q.kill)+' per kill, '+secs(q.rest)+' resting'+(q.risky ? '. <span class="warnline">Risky: '+esc(q.risky)+'</span>' : '') : esc(q ? q.why : '');
  const dv = d && d.ok ? fmt(d.role === 'healer' ? d.hps : d.dps) : '–';
  const du = d && d.role === 'healer' ? 'healing per second' : 'damage per second';
  const dd = d && d.ok ? 'Boss two levels above you, 2 minutes'+(d.petDps ? ', pet '+fmt(d.petDps)+' of it' : '')+(d.role === 'tank' ? '. Tanking is simmed as damage for now' : '') : esc(d ? d.why : '');
  $('#charKpis').innerHTML = kpi('Questing', qv, 'kills per hour', qd) + kpi('Dungeon', dv, du, dd)
    + (c.cls === 'shaman' && specOf(c) === 'res' ? '<div class="note" style="grid-column:1/-1">Whether you keep the tank alive, mana over a pull and Resto talents compared: <a href="'+SHAMAN_SIM+'" target="_blank" rel="noopener">Shaman Sim</a>.</div>' : '');
  if(pending || !q || !q.ok){ $('#charDetails').innerHTML = ''; return; }
  const rows = [
    ['Mob', 'Level '+q.mob.level+', '+fmt(q.mob.hp)+' health, '+fmt(q.mob.dps,1)+' damage per second'],
    ['Your damage per second', fmt(q.dps,1)+(q.petDps ? ' (pet '+fmt(q.petDps,1)+')' : '')],
    ['Time to kill', secs(q.kill)],
    ['Damage you take', q.petTank ? 'Your pet takes the hits' : fmt(q.taken,1)+' per second, '+fmt(q.hpLost)+' of '+fmt(q.health)+' health per kill'],
    ['Mana per kill', q.mana ? fmt(q.manaUsed)+' of '+fmt(q.mana) : 'No mana'],
    ['Resting per kill', secs(q.rest)+(q.rest > 0.05 ? ', waiting on '+q.restFor : '')],
    ['Walking between pulls', secs(q.travel)],
    ['Share of time fighting', fmt(q.fightShare*100)+'%'],
    ['Food and water', esc(q.food)+(q.drink ? ' and '+esc(q.drink) : '')]
  ];
  $('#charDetails').innerHTML = '<div class="card"><h3>Questing, per kill</h3><table class="sheet"><tbody>'+rows.map(x => '<tr><td>'+x[0]+'</td><td>'+x[1]+'</td></tr>').join('')+'</tbody></table></div>'
    + '<div class="card"><h3>Character sheet</h3>'+sheetTable(c)+'</div>';
}
function sheetTable(c){
  const g = MCRequest.gearStats(gearOf(c), ITEMS_ALL), sh = MCRequest.sheet(CLASSDATA[c.cls], c.race, c.level, g);
  const rows = [['Health', fmt(sh.health)], ['Mana', sh.mana ? fmt(sh.mana) : 'None'], ['Strength', fmt(sh.attributes[0])], ['Agility', fmt(sh.attributes[1])], ['Stamina', fmt(sh.attributes[2])], ['Intellect', fmt(sh.attributes[3])], ['Spirit', fmt(sh.attributes[4])], ['Melee crit', fmt(sh.meleeCrit,2)+'%'], ['Spell crit', sh.spellCrit[0] ? fmt(sh.spellCrit[0],2)+'%' : '–'], ['Armor', fmt((g.armor||0)+(g.bonusArmor||0)+2*sh.attributes[1])]];
  return '<table class="sheet"><tbody>'+rows.map(x => '<tr><td>'+x[0]+'</td><td>'+x[1]+'</td></tr>').join('')+'</tbody></table>';
}

// ---------- Sources and effort ----------
function srcOne(s){
  if(s.t === 'quest') return 'Quest: '+(s.q||'?')+(s.z ? ' ('+s.z+')' : '')+(s.lv ? ', level '+s.lv : '');
  if(s.t === 'dungeon' || s.t === 'npc') return (s.npc||'Drop')+(s.z ? ', '+s.z : '')+(s.t === 'dungeon' && s.lv ? ' ('+s.lv+')' : '')+(s.p ? ', '+fmt(s.p,1)+'% drop' : ', drop chance unknown');
  if(s.t === 'raid') return (s.npc||'Raid drop')+', '+(s.z||'raid')+(s.p ? ', '+fmt(s.p,1)+'%' : '');
  if(s.t === 'crafted') return 'Crafted: '+s.prof+(s.skill ? ' '+s.skill : '');
  if(s.t === 'vendor') return 'Vendor: '+(s.npc||'?')+(s.z ? ', '+s.z : '');
  if(s.t === 'rep') return 'Reputation: '+(s.f||'?')+(s.st ? ', '+s.st : '');
  if(s.t === 'pvp') return 'PvP reward';
  if(s.t === 'world') return 'World drop'+(s.npc ? ' ('+s.npc+')' : '')+(s.z ? ', '+s.z : '');
  return '';
}
function srcText(it){ return it.src ? it.src.slice(0, 2).map(srcOne).join(' · ') : 'Source not in the data'; }
function effortOf(it){
  let best = null;
  (it.src && it.src.length ? it.src : [{t:'none'}]).forEach(s => {
    let cost, lvl, label;
    if(s.t === 'quest'){ cost = 1; lvl = 1; label = 'Quest'; }
    else if(s.t === 'vendor'){ cost = 1.2; lvl = 1; label = 'Vendor'; }
    else if(s.t === 'crafted'){ cost = 1.6; lvl = 2; label = 'Crafted'; }
    else if(s.t === 'dungeon' || s.t === 'npc'){ if(s.p){ const runs = Math.min(30, 100/s.p); cost = 1 + runs/4; lvl = runs <= 4 ? 2 : runs <= 10 ? 3 : 4; label = '~'+Math.ceil(runs)+(s.t === 'npc' ? ' kills' : ' runs'); } else { cost = 3.5; lvl = 3; label = 'Drop'; } }
    else if(s.t === 'rep'){ cost = 4; lvl = 3; label = 'Reputation'; }
    else if(s.t === 'raid'){ cost = 8; lvl = 4; label = 'Raid'; }
    else if(s.t === 'pvp'){ cost = 9; lvl = 4; label = 'PvP'; }
    else if(s.t === 'world'){ cost = 12; lvl = 4; label = 'World drop'; }
    else { cost = 6; lvl = 4; label = 'Unknown'; }
    if(!best || cost < best.cost) best = {cost, lvl, label, s};
  });
  return best;
}

// ---------- Upgrades ----------
$('#runUps').addEventListener('click', async () => {
  const c = cur(), ctx = ctxOf(c), obj = $('#upObj').value;
  const r = results[c.id];
  if(!r || r.pending){ toast('Wait for this character\'s numbers first'); return; }
  const w = MCGear.STYLE[(MCGear.STYLE_OF[c.cls]||{})[specOf(c)] || 'melee'];
  const score = it => { let v = 0; for(const k in it.s) v += (w[k]||0)*it.s[k]; if(it.w) v += (it.w.min+it.w.max)/2/it.w.speed*(w.str ? 3 : w.agi ? 2.5 : 0.3)*(it.two ? 1.4 : 1); return v; };
  const cands = [], seen = new Set();   // each item once, in the first slot it fits; PvP and raid-only items left out
  for(const slot of MCGear.SLOTS){
    if(slot === 'offhand' && ctx.gear.mainhand && ITEMS_ALL[ctx.gear.mainhand] && ITEMS_ALL[ctx.gear.mainhand].two) continue;
    const curIt = ITEMS_ALL[ctx.gear[slot]]; const curV = curIt ? score(curIt) : -1;
    const worn = new Set(Object.values(ctx.gear).map(String));
    const hard = it => it.src && it.src.length && it.src.every(x => x.t === 'pvp' || x.t === 'raid');
    const pool = Object.keys(ITEMS_ALL).filter(id => !worn.has(id) && inEngine(id) && !seen.has(id) && !hard(ITEMS_ALL[id])).map(id => ({id, it: ITEMS_ALL[id]}))
      .filter(x => { const f = MCGear.wearFrom(x.it, c.cls, slot); return f !== null && f <= c.level && MCGear.reachLevel(x.it) <= c.level; })
      .map(x => Object.assign(x, {v: score(x.it)})).filter(x => x.v > curV).sort((a, b) => b.v - a.v).slice(0, slot === 'mainhand' || slot === 'ranged' ? 6 : 3);
    pool.forEach(x => { cands.push({id: +x.id, slot, two: !!x.it.two}); seen.add(x.id); });
  }
  if(!cands.length){ $('#upState').innerHTML = '<span class="small muted">No candidates with a better rough stat value at this level.</span>'; return; }
  $('#runUps').disabled = true;
  $('#upState').innerHTML = '<div class="loader"><span class="spin"></span>Simming '+cands.length+' items<span class="prog"><i id="uprog"></i></span></div>';
  try {
    await startEngine();
    const kill = r.quest && r.quest.ok ? r.quest.kill : 20;
    const res = await call({type: 'ups', ctx, objective: obj, candidates: cands, killTime: kill, items: itemsFor(Object.values(ctx.gear).concat(cands.map(x => x.id)))}, p => { const el = $('#uprog'); if(el) el.style.width = (p*100)+'%'; });
    if(res.base == null){ $('#upState').innerHTML = '<span class="warnline">'+esc(res.why || 'No baseline')+'</span>'; return; }
    const rows = res.items.filter(x => x.v != null && x.v > res.base*1.002).map(x => { const it = ITEMS_ALL[x.id]; const gain = (x.v - res.base)/res.base*100; const eff = effortOf(it); return {x, it, gain, eff, rank: gain/eff.cost}; }).sort((a, b) => b.rank - a.rank);
    const unit = obj === 'quest' ? 'kills per hour' : 'dungeon';
    // Gains compare like with like (each item and the baseline simmed the same way); "now" is the character's own number
    const now = obj === 'quest' ? (r.quest && r.quest.ok ? fmt(r.quest.perHour)+' kills per hour' : '') : (r.dungeon && r.dungeon.ok ? fmt(r.dungeon.role === 'healer' ? r.dungeon.hps : r.dungeon.dps)+' per second in the dungeon' : '');
    $('#upState').innerHTML = '<span class="small muted">Now: '+now+'. '+rows.length+' of '+res.items.length+' items simmed are upgrades.</span>';
    $('#upList').innerHTML = rows.slice(0, 15).map(({x, it, gain, eff}) => {
      const was = ITEMS_ALL[ctx.gear[x.slot]];
      return '<div class="up"><div><div class="nm q'+it.q+'">'+esc(it.n)+'</div><div class="meta"><span class="ease e'+eff.lvl+'">'+esc(eff.label)+'</span>'+esc(srcOne(eff.s) || 'Source not in the data')+'</div><div class="meta">'+SLOT_LABEL[x.slot]+(was ? ', replaces '+esc(was.n) : ', empty slot')+' · '+esc(statText(it))+(it.rl ? ' · req '+it.rl : '')+'</div></div><div class="gain">+'+fmt(gain,1)+'%<small>'+unit+'</small></div></div>';
    }).join('') || '<div class="small muted">Nothing beats the current gear.</div>';
  } catch(err){ $('#upState').innerHTML = '<span class="warnline">'+esc(err.message)+'</span>'; }
  finally { $('#runUps').disabled = false; }
});

// ---------- Tabs and start ----------
function show(v){
  ['group','char'].forEach(k => $('#v-'+k).classList.toggle('on', k === v));
  document.querySelectorAll('.tab').forEach(t => t.setAttribute('aria-selected', t.dataset.v === v ? 'true' : 'false'));
  try{ history.replaceState(null, '', '#'+v); }catch(e){}
  if(v === 'char') renderChar();
}
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => show(t.dataset.v)));
$('#dataNote').textContent = 'Data: '+ITEMS_ALL_META.count+' items, talent trees and spell ranks from the Forever client (build 1.60.1.70862) via wowsims Forever and wago.tools; leveling routes from Maxroll, Method, Warcraft Tavern and wowtbc.gg; engine: '+MC_META.engine+'.';
renderGroup();
chars.forEach(simChar);
if((location.hash||'').slice(1) === 'char') show('char');
})();
