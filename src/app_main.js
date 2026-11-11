(function(){
'use strict';
const $ = s => document.querySelector(s);
// On GitHub Pages the two tools sit side by side; elsewhere they link to the published artifacts
// (the link to the Group Sim is in the sheet tabs now)
const fmt = (n, d) => (n === null || n === undefined || !isFinite(n)) ? '–' : Number(n).toLocaleString('en-US', {maximumFractionDigits: d||0, minimumFractionDigits: d||0});
const pct = (n, d) => fmt(n, d===undefined?1:d) + '%';
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const toast = msg => { const t = $('#toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('on'), 2200); };
const store = {get(k,d){ try{ const v = localStorage.getItem('shamansim:'+k); return v ? JSON.parse(v) : d; }catch(e){ return d; } }, set(k,v){ try{ localStorage.setItem('shamansim:'+k, JSON.stringify(v)); }catch(e){} }};
const TMETA = Object.fromEntries(TALENT_META.map(t => [t.id, t]));
const IMBUE = {rockbiter:'Rockbiter Weapon', flametongue:'Flametongue Weapon', windfury:'Windfury Weapon', none:'no imbue'};

// ---------- Level ----------
let LEVEL = Math.max(1, Math.min(60, +store.get('level', 8) || 8));
const level = () => LEVEL;
const points = () => Math.max(0, LEVEL - 9);

// ---------- Builds and their leveling routes ----------
// A route lists talents in the order points are spent, one point per level from 10 to 60.
const ROUTES = {
  pure:  [['tidalfocus',5],['mindful',3],['ihw',2],['watershield',1],['ihw',3],['anchealing',1],['manatide',1],['tidalmastery',5],['natswift',1],['healingway',3],['purification',5],['riptide',1],['thundering',5],['anchealing',2],['restotems',5],['healfocus',3],['ancknow',5]],
  melee: [['tidalfocus',5],['mindful',3],['ihw',2],['watershield',1],['ihw',3],['totemicfocus',1],['manatide',1],['ancknow',5],['mentaldex',3],['thundering',5],['eleweapons',2],['stormstrike',1],['restotems',5],['tidalmastery',4],['healingway',3],['natswift',1],['purification',5],['riptide',1]],
  mq:    [['tidalfocus',5],['mindful',3],['ihw',2],['watershield',1],['ihw',3],['totemicfocus',1],['manatide',1],['ancknow',5],['mentaldex',3],['thundering',5],['eleweapons',2],['stormstrike',1],['flurry',5],['mentalquick',2],['restotems',5],['tidalmastery',1],['healingway',3],['purification',3]],
  ele:   [['tidalfocus',5],['mindful',3],['ihw',2],['watershield',1],['anchealing',1],['healfocus',3],['manatide',1],['convection',5],['concussion',5],['elefocus',1],['restotems',5],['healingway',3],['natswift',1],['purification',5],['riptide',1],['ancknow',5],['thundering',4]]
};
const BUILDS = [
  {key:'pure',  name:'Pure healer', route:ROUTES.pure, color:'var(--pure)', hex:'#4285f4', on:true, blurb:'Most healing at 60'},
  {key:'melee', name:'Healer who can fight', route:ROUTES.melee, color:'var(--hybrid)', hex:'#ea4335', on:true, blurb:'99% of the healing, about two thirds more melee damage'},
  {key:'mq',    name:'Mental Quickness hybrid', route:ROUTES.mq, color:'var(--mq)', hex:'#fbbc04', on:false, blurb:'More melee, gives up Nature’s Swiftness and Riptide'},
  {key:'ele',   name:'Elemental dip', route:ROUTES.ele, color:'var(--ele)', hex:'#34a853', on:false, blurb:'Lightning Bolt instead of melee'}
];
const codeOf = t => ['ele','enh','res'].map(tr => TREE_ORDER[tr].map(id => t[id]||0).join('').replace(/0+$/,'')).join('-');
function splitOf(t){ const s = {ele:0,enh:0,res:0}; for(const k in t){ for(const tr in TREE_ORDER) if(TREE_ORDER[tr].indexOf(k) >= 0) s[tr] += t[k]; } return s.ele+'/'+s.enh+'/'+s.res; }
// A custom code has no order, so fill its main tree first, top row down, then the others.
function routeFromCode(t){
  const sp = {ele:0,enh:0,res:0}; for(const k in t) for(const tr in TREE_ORDER) if(TREE_ORDER[tr].indexOf(k) >= 0) sp[tr] += t[k];
  const trees = Object.keys(sp).sort((a,b) => sp[b]-sp[a]);
  const r = []; trees.forEach(tr => TREE_ORDER[tr].forEach(id => { if(t[id]) r.push([id, t[id]]); })); return r;
}
const savedOn = store.get('buildsOn', null);
const savedCustom = store.get('custom', null);
if(savedCustom){ const t = Engine.talentsFromCode(savedCustom.code, TREE_ORDER); BUILDS.push({key:'custom', name:'Custom', route:routeFromCode(t), color:'var(--custom)', hex:'#ff6d01', on:true, blurb:'From your link', custom:true}); }
BUILDS.forEach(b => { b.full = Engine.talentsAt(b.route, 51); b.split = splitOf(b.full); b.code = codeOf(b.full); if(savedOn && savedOn[b.key] !== undefined) b.on = savedOn[b.key]; });
if(!BUILDS.some(b => b.on)) BUILDS[0].on = true;
const talentsOf = b => Engine.talentsAt(b.route, points());
function activeBuilds(){ return BUILDS.filter(b => b.on); }
function saveOn(){ store.set('buildsOn', Object.fromEntries(BUILDS.map(b => [b.key, b.on]))); }
function renderBuildChips(){
  $('#buildChips').innerHTML = BUILDS.map(b => '<button class="chip" data-k="'+b.key+'" aria-pressed="'+b.on+'" title="'+esc(b.blurb)+'"><span class="dot" style="background:'+b.color+'"></span>'+esc(b.name)+' <span class="muted num">'+b.split+'</span></button>').join('');
  $('#buildChips').querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => {
    const b = BUILDS.find(x => x.key === c.dataset.k);
    if(b.on && activeBuilds().length === 1) return toast('Keep at least one build');
    b.on = !b.on; saveOn(); renderBuildChips(); renderRoutes(); refresh();
  }));
  $('#sum-builds').textContent = activeBuilds().map(b => b.name+' '+b.split).join('; ');
  const sel = $('#upBuild'); const cur = sel.value;
  sel.innerHTML = BUILDS.map(b => '<option value="'+b.key+'">'+esc(b.name)+' ('+b.split+')</option>').join('');
  if(cur && BUILDS.find(b => b.key === cur)) sel.value = cur;
}
function routeStep(route, n){ let k = 0; for(const [id, c] of route){ if(n < k + c) return {id, rank:n - k + 1}; k += c; } return null; }
function renderRoutes(){
  const p = points();
  $('#routes').innerHTML = activeBuilds().map(b => {
    const t = talentsOf(b);
    const taken = b.route.map(([id]) => id).filter((id,i,a) => a.indexOf(id) === i && t[id]).map(id => esc(TMETA[id].name)+' '+t[id]+'/'+TMETA[id].max);
    const nx = p < 51 ? routeStep(b.route, p) : null;
    const nextLine = nx ? 'Next, at '+(Math.max(10, LEVEL+1))+': '+esc(TMETA[nx.id].name)+' '+nx.rank+'/'+TMETA[nx.id].max : 'All 51 points spent';
    const head = '<div class="hd"><span class="bdot" style="background:'+b.color+'"></span>'+esc(b.name)+' <span class="muted num" style="font-weight:500">'+b.split+' at 60</span></div>';
    return '<div class="rt">'+head+(p ? '<div class="tk">'+p+' point'+(p>1?'s':'')+' now ('+splitOf(t)+'): '+taken.join(', ')+'</div>' : '<div class="tk">No talent points yet. The first comes at level 10.</div>')+'<div class="nx">'+nextLine+'</div></div>';
  }).join('');
}
$('#addCustom').addEventListener('click', () => {
  const raw = $('#customCode').value.trim();
  const m = raw.match(/[?&#]b=([0-5-]+)/) || raw.match(/^([0-5-]{3,80})$/);
  if(!m){ $('#customMsg').textContent = 'Paste a timesaver.gg calculator link or its build code.'; return; }
  const code = m[1], t = Engine.talentsFromCode(code, TREE_ORDER);
  const total = Object.values(t).reduce((a,b)=>a+b,0);
  if(total === 0 || total > 51){ $('#customMsg').textContent = 'That code has '+total+' points. A level 60 build has up to 51.'; return; }
  const ex = BUILDS.find(b => b.key === 'custom');
  const fields = {route:routeFromCode(t), full:t, split:splitOf(t), code};
  if(ex) Object.assign(ex, fields, {on:true});
  else BUILDS.push(Object.assign({key:'custom', name:'Custom', color:'var(--custom)', hex:'#ff6d01', on:true, blurb:'From your link', custom:true}, fields));
  store.set('custom', {code}); saveOn();
  const unmod = Object.keys(t).filter(k => MODELED.indexOf(k) < 0);
  $('#customMsg').textContent = 'Added ('+fields.split+'). Below 60 its points fill the main tree first, top row down.' + (unmod.length ? ' Not modelled: '+unmod.length+' talent(s) without a throughput effect here.' : '');
  renderBuildChips(); renderRoutes(); refresh();
});

// ---------- What you have at this level ----------
const SPELL_NAMES = {hw:'Healing Wave', lhw:'Lesser Healing Wave', ch:'Chain Heal', lb:'Lightning Bolt', es:'Earth Shock', fs:'Flame Shock', hst:'Healing Stream Totem', ms:'Mana Spring Totem', rb:'Rockbiter Weapon', ft:'Flametongue Weapon', wf:'Windfury Weapon'};
const EVENTS = (() => {
  const ev = [];
  for(const k in SPELL_NAMES) (RANKS[k]||[]).forEach((r,i) => { if(!r.book) ev.push({l:r.l, k, name:SPELL_NAMES[k], rank:i+1}); });
  DATA.ls.ranks.forEach((r,i) => ev.push({l:r[0], k:'ls', name:'Lightning Shield', rank:i+1}));
  return ev.sort((a,b) => a.l - b.l);
})();
function renderLevel(){
  const L = LEVEL;
  $('#level').value = L;
  $('#lvDown').disabled = L <= 1; $('#lvUp').disabled = L >= 60;
  const p = points();
  $('#lvSub').textContent = p ? p+' talent point'+(p>1?'s':'')+', '+(L < 60 ? (60-L)+' levels to go' : 'max level') : 'No talents yet, first point at 10';
  const now = {}; EVENTS.forEach(e => { if(e.l <= L) now[e.k] = e; });
  const order = ['hw','lhw','ch','lb','es','fs','ls','rb','ft','wf','hst','ms'];
  const nowPills = order.filter(k => now[k]).map(k => '<span class="pill'+(now[k].l === L ? ' new' : '')+'">'+esc(now[k].name)+' '+now[k].rank+'</span>').join('');
  const soon = {}; EVENTS.forEach(e => { if(e.l > L && e.l <= L+6) (soon[e.l] = soon[e.l] || []).push(e.name+' '+e.rank); });
  if(L < 10) (soon[10] = soon[10] || []).push('First talent point');
  const soonLv = Object.keys(soon).map(Number).sort((a,b) => a-b).slice(0, 3);
  const soonPills = soonLv.map(l => '<span class="pill"><b>'+l+'</b>'+esc(soon[l].join(', '))+'</span>').join('') || '<span class="muted">Nothing new in the next levels</span>';
  $('#lvUnlocks').innerHTML = '<div class="ul"><span class="k">Now</span><span class="v">'+nowPills+'</span></div><div class="ul"><span class="k">Soon</span><span class="v">'+soonPills+'</span></div>';
  // Buff labels for this level
  const motw = Engine.lvlVal(DATA.motwByLevel, L), ai = Engine.lvlVal(DATA.aiByLevel, L), pot = Engine.potionMana(L, DATA);
  $('#l-motw').textContent = motw ? '+'+motw+' all stats at your level' : 'Armor only below 10, no stats';
  $('#l-ai').textContent = '+'+ai+' Intellect at your level';
  const potLv = DATA.potions.filter(r => r[0] <= L).map(r => r[0]).pop();
  $('#l-potT').textContent = potLv ? DATA.potionNames[potLv]+'s in dungeons' : 'Mana potions in dungeons';
  $('#l-pot').textContent = pot ? fmt(pot)+' mana every 2 minutes' : 'None until level 5';
  $('#tabRow').style.display = L >= 60 ? '' : 'none';
  $('#qMageRow').style.display = L >= 55 ? '' : 'none';
  const ls = Engine.lvlRow(DATA.ls.ranks, L);
  $('#l-ls').textContent = ls ? 'Rank '+(DATA.ls.ranks.indexOf(ls)+1)+': '+ls[1]+' damage per charge, 3 charges' : 'Learned at level 8';
  $('#qLS').disabled = !ls;
}
function setLevel(L){
  L = Math.max(1, Math.min(60, Math.round(+L || 1)));
  if(L === LEVEL){ $('#level').value = L; return; }
  LEVEL = L; store.set('level', L);
  $('#maxLvl').value = L;
  renderLevel(); renderRoutes(); renderGear(); applyLevelDefaults(); refresh();
  $('#results').innerHTML = '';
}
$('#lvDown').addEventListener('click', () => setLevel(LEVEL - 1));
$('#lvUp').addEventListener('click', () => setLevel(LEVEL + 1));
$('#level').addEventListener('change', e => setLevel(e.target.value));

// ---------- Gear ----------
const SLOTS = [['head','Head'],['neck','Neck'],['shoulder','Shoulder'],['back','Back'],['chest','Chest'],['wrist','Wrist'],['hands','Hands'],['waist','Waist'],['legs','Legs'],['feet','Feet'],['finger1','Ring'],['finger2','Ring'],['trinket1','Trinket'],['trinket2','Trinket'],['mainhand','Main hand'],['offhand','Off hand'],['relic','Totem']];
let gear = store.get('gear', null) || (LEVEL >= 60 && PRESETS.resto_timesaver ? Object.assign({}, PRESETS.resto_timesaver.gear) : {});
const statLabel = {int:'Int',spi:'Spi',sta:'Sta',str:'Str',agi:'Agi',healing:'Heal',spellDamage:'Dmg',mp5:'Mp5',critRating:'Crit',hitRating:'Hit',ap:'AP',armor:'Armor'};
const statText = it => Object.entries(it.s||{}).filter(([k]) => statLabel[k]).map(([k,v]) => (k === 'armor' ? '' : '+')+v+' '+statLabel[k]).join(', ') + (it.w ? (it.s && Object.keys(it.s).length ? ', ' : '')+it.w.min+'-'+it.w.max+' @ '+it.w.speed : '');
function srcLevel(it){ let lv = null; (it.src||[]).forEach(s => { const m = s.lv ? String(s.lv).match(/\d+/) : null; if(m){ const v = +m[0]; if(lv === null || v < lv) lv = v; } }); return lv; }
// Shamans learn Mail at 40 in Forever, as in Classic
const MAIL_AT = 40;
const needLvl = it => Math.max(it.rl || 1, it.at === 'Mail' ? MAIL_AT : 1);
const canWear = it => needLvl(it) <= LEVEL;
// The level you can realistically get an item at: its requirement, the level of the quest or dungeon it comes from,
// and for items with neither (many have no requirement in Forever), item level minus 5.
const reachLvl = it => { const sl = srcLevel(it); return Math.max(needLvl(it), sl || ((it.rl || 0) <= 1 ? Math.max(1, (it.il || 1) - 5) : 1)); };
function wearable(g){ const out = {}; for(const k in g){ const it = ITEMS[g[k]]; if(it && canWear(it)) out[k] = g[k]; } return out; }
function presetSelect(){
  const sel = $('#preset');
  sel.innerHTML = '<option value="">Your current gear</option>' + Object.entries(PRESETS).map(([k,p]) => '<option value="'+k+'">'+esc(p.label)+'</option>').join('') + '<option value="__naked">Nothing equipped</option>';
  sel.addEventListener('change', () => {
    const v = sel.value; if(!v) return;
    gear = v === '__naked' ? {} : Object.assign({}, PRESETS[v].gear);
    $('#presetNote').textContent = v === '__naked' ? '' : PRESETS[v].title;
    sel.value = '';
    saveGear(); renderGear(); refresh();
  });
}
function saveGear(){ store.set('gear', gear); }
function renderGear(){
  $('#gearList').innerHTML = SLOTS.map(([k,label]) => {
    const it = ITEMS[gear[k]];
    const blocked = k === 'offhand' && gear.mainhand && ITEMS[gear.mainhand] && ITEMS[gear.mainhand].two && canWear(ITEMS[gear.mainhand]);
    const need = it && !canWear(it) ? '<span class="needlv">'+(it.at === 'Mail' && (it.rl||1) < MAIL_AT ? 'Mail needs level 40' : 'needs level '+it.rl)+'</span>' : '';
    return '<div class="slot"><span class="sn">'+label+'</span><div class="in">'
      + (it ? '<div class="nm q'+it.q+'">'+esc(it.n)+need+'</div><div class="st">'+esc(statText(it))+'</div>' : '<div class="nm empty">'+(blocked ? 'Two-hander equipped' : 'Empty')+'</div>')
      + '</div><div class="row" style="gap:6px;flex-wrap:nowrap">'+(blocked ? '' : '<button class="btn sm" data-pick="'+k+'">Change</button>')+(it ? '<button class="btn sm" data-clear="'+k+'" aria-label="Remove '+esc(it.n)+'">×</button>' : '')+'</div></div>';
  }).join('');
  $('#gearList').querySelectorAll('[data-pick]').forEach(b => b.addEventListener('click', () => openPicker(b.dataset.pick)));
  $('#gearList').querySelectorAll('[data-clear]').forEach(b => b.addEventListener('click', () => { delete gear[b.dataset.clear]; saveGear(); renderGear(); refresh(); }));
  const all = SLOTS.filter(([k]) => gear[k]).length, worn = Object.keys(wearable(gear)).length;
  const g = Engine.sumGear(wearable(gear), ITEMS, SETS);
  const bits = [worn+' item'+(worn===1?'':'s')+(all > worn ? ' ('+(all-worn)+' above your level)' : '')];
  ['int','sta','spi','str','agi'].forEach(k => { if(g.s[k]) bits.push(fmt(g.s[k])+' '+statLabel[k]); });
  if(g.s.healing) bits.push('+'+fmt(g.s.healing)+' healing');
  $('#sum-gear').textContent = bits.join('; ');
  $('#gearWarn').innerHTML = all > worn ? '<div class="row" style="justify-content:space-between"><span class="warnline">'+(worn ? (all-worn)+' of these items need a higher level and are left out of every number.' : 'None of this gear can be worn at level '+LEVEL+', so every number uses no gear. Clear it and add what you wear.')+'</span><button class="btn sm" id="clearHigh">Remove them</button></div>' : '';
  if($('#clearHigh')) $('#clearHigh').addEventListener('click', () => { gear = wearable(gear); saveGear(); renderGear(); refresh(); });
  $('#setNote').innerHTML = g.activeSets.length ? 'Set bonuses counted: '+g.activeSets.map(a => esc(a.set)+' ('+a.n+'): '+esc(a.text)+(a.counted ? '' : ' <span class="muted">(not modelled)</span>')).join('; ') : '';
}

// ---------- Character & options ----------
function opts(){
  const x = {};
  ['int','spi','healing','mp5','critRating','sta'].forEach(k => x[k] = +($('#x-'+k).value)||0);
  return {buffs:{motw:$('#o-motw').checked, ai:$('#o-ai').checked}, potions:$('#o-pot').checked, tablet:$('#o-tab').checked && LEVEL >= 60, extra:x};
}
function charFor(b, gearOverride){
  const o = opts(); const g = Engine.sumGear(wearable(gearOverride || gear), ITEMS, SETS);
  return Engine.character({level:LEVEL, gearStats:g.s, mh:g.mh, oh:g.oh, talents:talentsOf(b), buffs:o.buffs, extra:o.extra}, DATA);
}
const CAP_OPTS = () => ({horizon:300, mix:{HW:0.7, CH:0.3}, chainEff:0.8, healEff:0.85, hstTargets:3, hitsPerSec:0.1, potions:opts().potions, tablet:opts().tablet});
function renderSheet(){
  const bs = activeBuilds();
  const cs = bs.map(b => charFor(b));
  const rows = [
    ['Health', c => fmt(c.hp)], ['Mana', c => fmt(c.mana)], ['Intellect', c => fmt(c.int)], ['Spirit', c => fmt(c.spi)], ['Stamina', c => fmt(c.sta)],
    ['Bonus healing', c => fmt(c.healing)], ['Heal crit', c => pct(c.healCrit)], ['Spell crit', c => pct(c.spellCrit)], ['Mana per 5', c => fmt(c.mp5)],
    ['Regen while casting', c => fmt((c.mp5/5 + c.mindful*c.spiritRegen)*5)+' mp5'], ['Regen after 5 s idle', c => fmt((c.mp5/5 + c.spiritRegen)*5)+' mp5'],
    ['Attack power', c => fmt(c.ap)], ['Melee crit', c => pct(c.meleeCrit)], ['Hit', c => pct(c.hit)], ['Armor', c => fmt(c.armor)]
  ];
  $('#sheet').innerHTML = '<thead><tr><th>Level '+LEVEL+'</th>'+bs.map(b => '<th><span class="bdot" style="background:'+b.color+'"></span>'+esc(b.name)+'</th>').join('')+'</tr></thead><tbody>'
    + rows.map(r => '<tr><td>'+r[0]+'</td>'+cs.map(c => '<td>'+r[1](c)+'</td>').join('')+'</tr>').join('') + '</tbody>';
  const o = opts();
  $('#sum-opts').textContent = [o.buffs.motw && 'Mark of the Wild', o.buffs.ai && 'Arcane Intellect', o.potions && 'mana potions', o.tablet && 'rank 10 Healing Wave'].filter(Boolean).join('; ') || 'No buffs';
}
document.querySelectorAll('#f-opts input').forEach(i => i.addEventListener('change', () => refresh()));

// ---------- Questing ----------
const questOpts = () => ({mobDiff:+$('#qDiff').value, travel:+$('#qTravel').value, lightningShield:$('#qLS').checked, mageWater:$('#qMage').checked && LEVEL >= 55});
const questRate = c => { const r = Engine.solo(c, DATA, questOpts()); return r ? r.best.perHour : 0; };
const secs = v => v >= 59.5 ? fmt(v/60,1)+' min' : fmt(v, v < 10 ? 1 : 0)+' s';
function renderQuest(){
  const bs = activeBuilds(), qo = questOpts();
  const rs = bs.map(b => ({b, c:charFor(b)})).map(x => Object.assign(x, {r:Engine.solo(x.c, DATA, qo)}));
  const by = k => rs.find(x => x.b.key === k);
  const kp = rs.map(({b, r}) => {
    const s = r.best;
    return '<div class="kpi" style="--bc:'+b.color+'"><div class="lb"><span class="bdot" style="background:'+b.color+'"></span>'+esc(b.name)+'</div><div class="v">'+fmt(s.perHour)+'<small>kills per hour</small></div><div class="d">'+esc(s.name)+(s.imbue ? ', '+IMBUE[s.imbue] : '')+'. '+secs(s.kill)+' per kill, '+secs(s.rest)+' resting per kill.</div></div>';
  }).join('');
  const styles = rs[0].r.styles.map(s => s.key);
  const nameOf = k => rs[0].r.styles.find(s => s.key === k).name;
  const cell = (r, k) => { const s = r.styles.find(x => x.key === k); if(!s) return '–'; if(s.unsafe) return '<span class="muted">unsafe</span><span class="sub">'+esc(s.unsafe)+'</span>'; const isBest = s === r.best; return (isBest ? '<b>' : '')+fmt(s.perHour)+(isBest ? '</b>' : ''); };
  const cmp = '<div class="tablewrap"><table class="cmp"><thead><tr><th>Kills per hour</th>'+bs.map(b => '<th><span class="bdot" style="background:'+b.color+'"></span>'+esc(b.name)+'</th>').join('')+'</tr></thead><tbody>'
    + styles.map(k => '<tr><td>'+esc(nameOf(k))+'</td>'+rs.map(x => '<td>'+cell(x.r, k)+'</td>').join('')+'</tr>').join('') + '</tbody></table></div>';
  const rows = [
    ['Time to kill', s => secs(s.kill)], ['Damage per second in melee', s => s.meleeDPS ? fmt(s.meleeDPS,1) : '–', 'without Lightning Shield'],
    ['Mana spent', s => fmt(s.mana), 'after regen during the fight'], ['Health lost', s => fmt(s.hpLost)],
    ['Healing Waves mid-fight', s => fmt(s.heals)], ['Resting', s => secs(s.rest), 'eating and drinking together'+(rs.some(x => x.r.best.topUp > 0) ? ', plus a Healing Wave when that is faster' : '')],
    ['Share of time fighting', s => pct(s.fightShare*100, 0)]
  ];
  const det = '<div class="tablewrap"><table class="cmp"><thead><tr><th>Per kill, best way to fight</th>'+bs.map(b => '<th><span class="bdot" style="background:'+b.color+'"></span>'+esc(b.name)+'</th>').join('')+'</tr></thead><tbody>'
    + rows.map(row => '<tr><td>'+row[0]+(row[2] ? '<span class="sub">'+row[2]+'</span>' : '')+'</td>'+rs.map(x => '<td>'+row[1](x.r.best)+'</td>').join('')+'</tr>').join('') + '</tbody></table></div>';
  const r0 = rs[0].r, m = r0.mob;
  const noWeapon = !rs[0].c.mh;
  const facts = '<div class="small muted">Level '+m.level+' mob: '+fmt(m.hp)+' health, hits for '+fmt(m.dps,1)+' damage per second before armor. You take about '+fmt(m.taken,1)+' per second after '+pct(m.mitigation*100,0)+' armor reduction and misses or dodges.'+(r0.ls.rank && qo.lightningShield ? ' Lightning Shield rank '+r0.ls.rank+' adds '+fmt(r0.ls.dps,1)+' damage per second while you are hit.' : '')+' Resting uses '+esc(r0.drink[3])+' and '+esc(r0.food[3])+'.</div>';
  $('#questOut').innerHTML = (noWeapon ? '<div class="note">No weapon equipped, so melee is bare hands. Add your weapon under Gear.</div>' : '') + '<div class="kpis">'+kp+'</div><div class="grid2"><div>'+cmp+'</div><div>'+det+'</div></div>'+facts;
}
$('#qTravel').addEventListener('input', () => { $('#qTravelVal').textContent = $('#qTravel').value+' s'; renderQuest(); });
['#qDiff','#qLS','#qMage'].forEach(s => $(s).addEventListener('change', () => { renderQuest(); renderUpgrades(); }));

// ---------- Picker ----------
let pickSlot = null, pickerData = [];
function itemsForSlot(slot){ const kind = slot.replace(/[12]$/,''); return Object.entries(ITEMS).filter(([id,it]) => it.sl === kind); }
const upMode = () => $('#upMode').value;
function scoreFn(b){
  if(upMode() === 'quest') return g => questRate(charFor(b, g));
  const co = CAP_OPTS(); return g => Engine.capacity(charFor(b, g), DATA, co).total;
}
function openPicker(slot){
  pickSlot = slot;
  const label = SLOTS.find(s => s[0] === slot)[1];
  $('#pickTitle').textContent = 'Choose '+label.toLowerCase();
  $('#pickSearch').value = '';
  const b = activeBuilds()[0], f = scoreFn(b);
  $('#pickNote').textContent = 'Items you can get and wear at level '+LEVEL+', sorted by how much they add to '+(upMode() === 'quest' ? 'kills per hour while questing' : 'healing over 5 minutes')+' for '+b.name+'. Values compare to an empty slot. Search finds higher-level items too.';
  const without = Object.assign({}, gear); delete without[slot];
  const base = f(without) || 1;
  pickerData = itemsForSlot(slot).map(([id,it]) => {
    let gain = null;
    if(canWear(it)){ const g = Object.assign({}, without); g[slot] = +id; if(slot === 'mainhand' && it.two) delete g.offhand; gain = (f(g)-base)/base*100; }
    return {id:+id, it, gain};
  }).sort((a,b) => (b.gain === null ? -1e9 : b.gain) - (a.gain === null ? -1e9 : a.gain));
  renderPicker();
  $('#picker').classList.add('on');
  setTimeout(() => $('#pickSearch').focus(), 60);
}
function renderPicker(){
  const q = $('#pickSearch').value.trim().toLowerCase();
  const rows = pickerData.filter(x => q ? x.it.n.toLowerCase().indexOf(q) >= 0 : x.gain !== null && reachLvl(x.it) <= LEVEL).slice(0, 120);
  const tag = x => x.gain === null ? '<span class="needlv">needs level '+needLvl(x.it)+'</span>' : reachLvl(x.it) > LEVEL ? '<span class="needlv">from level '+reachLvl(x.it)+' content</span>' : '';
  $('#pickList').innerHTML = rows.map(x => '<div class="pick" tabindex="0" data-id="'+x.id+'"><div><div class="q'+x.it.q+'" style="font-weight:600">'+esc(x.it.n)+tag(x)+'</div><div class="st">'+esc(statText(x.it))+(x.it.rl ? ', needs level '+x.it.rl : '')+'</div><div class="st">'+esc(srcText(x.it))+'</div></div><div class="sc">'+(x.gain === null ? '' : (x.gain>=0?'+':'')+fmt(x.gain,1)+'%')+'</div></div>').join('') || '<div class="muted small" style="padding:12px">No items match.</div>';
  $('#pickList').querySelectorAll('.pick').forEach(el => {
    const choose = () => { gear[pickSlot] = +el.dataset.id; if(pickSlot === 'mainhand' && ITEMS[el.dataset.id].two) delete gear.offhand; saveGear(); closePicker(); renderGear(); refresh(); };
    el.addEventListener('click', choose); el.addEventListener('keydown', e => { if(e.key === 'Enter') choose(); });
  });
}
function closePicker(){ $('#picker').classList.remove('on'); }
$('#pickSearch').addEventListener('input', renderPicker);
$('#pickClose').addEventListener('click', closePicker);
$('#picker').addEventListener('click', e => { if(e.target.id === 'picker') closePicker(); });
document.addEventListener('keydown', e => { if(e.key === 'Escape') closePicker(); });

// ---------- Sources and effort ----------
function srcOne(s){
  if(s.t === 'quest') return 'Quest: '+(s.q||'?')+(s.z ? ' ('+s.z+')' : '')+(s.lv ? ', level '+s.lv : '')+(s.note ? ' (only the Horde version is in the data; Alliance access unconfirmed)' : '');
  if(s.t === 'dungeon' || s.t === 'npc') return (s.npc||'Drop')+(s.z ? ', '+s.z : '')+(s.t === 'dungeon' && s.lv ? ' ('+s.lv+')' : '')+(s.p ? ', '+fmt(s.p,1)+'% drop' : ', drop chance unknown');
  if(s.t === 'raid') return (s.npc||'Raid drop')+', '+(s.z||'raid')+(s.p ? ', '+fmt(s.p,1)+'%' : '');
  if(s.t === 'crafted') return 'Crafted: '+s.prof+(s.skill ? ' '+s.skill : '');
  if(s.t === 'vendor') return 'Vendor: '+(s.npc||'?')+(s.z ? ', '+s.z : '');
  if(s.t === 'rep') return 'Reputation: '+(s.f||'?')+(s.st ? ', '+s.st : '');
  if(s.t === 'pvp') return 'PvP: '+(s.npc ? s.npc : s.f ? s.f+(s.st ? ', '+s.st : '') : s.rank ? 'rank '+s.rank+' reward' : 'reward');
  if(s.t === 'world') return 'World drop'+(s.npc ? ' ('+s.npc+')' : '')+(s.z ? ', '+s.z : '');
  return '';
}
function srcText(it){ return it.src ? it.src.map(srcOne).join('; ') : 'Source not in the data'; }
const SRC_FILTERS = [['quest','Quests',true],['vendor','Vendors',true],['crafted','Crafted',true],['dungeon','Dungeon drops',true],['npc','Named mobs',true],['rep','Reputation',true],['raid','Onyxia (from Dec 9)',false],['world','World drops',false],['pvp','PvP',false],['none','Unknown source',false]];
const srcOn = Object.fromEntries(SRC_FILTERS.map(f => [f[0], f[2]]));
function effortOf(it){
  const list = it.src && it.src.length ? it.src : [{t:'none'}];
  let best = null;
  list.forEach(s => {
    const kind = s.t;
    if(!srcOn[kind]) return;
    let cost, lvl, label;
    if(kind === 'quest'){ cost = 1; lvl = 1; label = 'Quest'; }
    else if(kind === 'vendor'){ cost = 1.2; lvl = 1; label = 'Vendor'; }
    else if(kind === 'crafted'){ cost = 1.6; lvl = 2; label = 'Crafted'; }
    else if(kind === 'dungeon' || kind === 'npc'){ if(s.p){ const runs = Math.min(30, 100/s.p); cost = 1 + runs/4; lvl = runs <= 4 ? 2 : runs <= 10 ? 3 : 4; label = kind === 'npc' ? '~'+Math.ceil(runs)+' kills' : '~'+Math.ceil(runs)+' runs'; } else { cost = 3.5; lvl = 3; label = 'Drop'; } }
    else if(kind === 'rep'){ cost = 4; lvl = 3; label = 'Reputation'; }
    else if(kind === 'raid'){ cost = 8; lvl = 4; label = 'Raid'; }
    else if(kind === 'pvp'){ cost = 9; lvl = 4; label = 'PvP'; }
    else if(kind === 'world'){ cost = 12; lvl = 4; label = 'World drop'; }
    else { cost = 6; lvl = 4; label = 'Unknown'; }
    if(!best || cost < best.cost) best = {cost, lvl, label, s};
  });
  return best;
}
function renderSrcChips(){
  $('#srcChips').innerHTML = SRC_FILTERS.map(f => '<button class="chip" data-s="'+f[0]+'" aria-pressed="'+srcOn[f[0]]+'">'+f[1]+'</button>').join('');
  $('#srcChips').querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => { srcOn[c.dataset.s] = !srcOn[c.dataset.s]; renderSrcChips(); renderUpgrades(); }));
}

// ---------- Upgrades ----------
function renderUpgrades(){
  if(!$('#v-upgrades').classList.contains('on')) return;
  const b = BUILDS.find(x => x.key === $('#upBuild').value) || BUILDS[0];
  const mode = upMode();
  $('#wRow').style.display = mode === 'heal' ? '' : 'none';
  const w = mode === 'heal' ? (+$('#wDmg').value)/100 : 0;
  $('#wVal').textContent = w === 0 ? 'healing only' : Math.round((1-w)*100)+'% healing, '+Math.round(w*100)+'% damage';
  const maxLvl = Math.max(1, Math.min(60, +$('#maxLvl').value || LEVEL));
  // Looking ahead means comparing at that level: stats, talents and gear as you will have them then
  const saveL = LEVEL; LEVEL = Math.max(LEVEL, maxLvl);
  try{ upgradesAt(b, mode, w, maxLvl, saveL); } finally { LEVEL = saveL; }
}
function upgradesAt(b, mode, w, maxLvl, level0){
  const co = CAP_OPTS(), dmgO = {mobDiff:0, front:true, imbue:'rockbiter', shock:'none'};
  const cBase = charFor(b);
  let score, unit;
  if(mode === 'quest'){
    const base = questRate(cBase) || 1, sb = Engine.solo(cBase, DATA, questOpts()).best;
    $('#upBase').textContent = (LEVEL > level0 ? 'At '+LEVEL+' with this gear: ' : 'Now: ')+fmt(base)+' kills per hour ('+sb.name.toLowerCase()+')';
    score = g => { const q = (questRate(charFor(b, g)) - base)/base*100; return {v:q, a:q}; };
    unit = 'kills per hour';
  } else {
    const hBase = Engine.capacity(cBase, DATA, co).total, dBase = Engine.damage(cBase, DATA, dmgO).dps;
    $('#upBase').textContent = (LEVEL > level0 ? 'At '+LEVEL+' with this gear: ' : 'Now: ')+fmt(hBase)+' healing over 5 min, '+fmt(dBase)+' melee DPS';
    score = g => { const c = charFor(b, g); const h = (Engine.capacity(c, DATA, co).total - hBase)/hBase*100; const d = w > 0 ? (Engine.damage(c, DATA, dmgO).dps - dBase)/Math.max(1,dBase)*100 : 0; return {v:(1-w)*h + w*d, a:h, d}; };
    unit = 'healing';
  }
  const cands = [], kinds = {};
  SLOTS.forEach(([k]) => { const kind = k.replace(/[12]$/,''); (kinds[kind] = kinds[kind] || []).push(k); });
  const worn = Object.values(gear);
  Object.entries(ITEMS).forEach(([id, it]) => {
    id = +id;
    if(needLvl(it) > maxLvl || reachLvl(it) > maxLvl) return;
    const slots = kinds[it.sl]; if(!slots) return;
    if(worn.indexOf(id) >= 0) return;
    const eff = effortOf(it); if(!eff) return;
    let bestR = null;
    slots.forEach(sk => {
      if(sk === 'offhand' && gear.mainhand && ITEMS[gear.mainhand] && ITEMS[gear.mainhand].two) return;
      const g = Object.assign({}, gear); g[sk] = id;
      if(sk === 'mainhand' && it.two) delete g.offhand;
      const r = score(g); r.slot = sk;
      if(!bestR || r.v > bestR.v) bestR = r;
    });
    if(bestR && bestR.v > 0.05) cands.push({id, it, eff, r:bestR});
  });
  const row = x => {
    const sl = SLOTS.find(s => s[0] === x.r.slot)[1];
    const cur = ITEMS[gear[x.r.slot]];
    const srcL = srcLevel(x.it);
    const lv = x.it.rl > 1 ? 'req '+x.it.rl : srcL ? 'no level requirement, '+(x.eff.s.t === 'quest' ? 'quest' : 'source')+' level '+srcL : 'no level requirement, item level '+x.it.il;
    return '<div class="up"><div><div class="nm q'+x.it.q+'">'+esc(x.it.n)+'</div><div class="meta"><span class="ease e'+x.eff.lvl+'">'+esc(x.eff.label)+'</span>'+esc(srcOne(x.eff.s) || 'Source not in the data')+'</div><div class="meta">'+esc(sl)+(cur ? ', replaces '+esc(cur.n) : ', empty slot')+', '+esc(statText(x.it))+(lv ? ', '+lv : '')+(x.it.lowconf ? ', stats from Wowhead only' : '')+'</div>'+(x.it.fx ? '<div class="meta">'+esc(x.it.fx[0])+' (not modelled)</div>' : '')+'</div>'
      +'<div class="gain">+'+fmt(x.r.a,1)+'%<small>'+unit+'</small>'+(w > 0 ? '<small>'+(x.r.d>=0?'+':'')+fmt(x.r.d,1)+'% damage</small>' : '')+'</div></div>';
  };
  const best = cands.slice().sort((a,b) => b.r.v/b.eff.cost - a.r.v/a.eff.cost).slice(0, 10);
  $('#bestUps').innerHTML = best.length ? best.map(row).join('') : '<div class="muted small">No upgrades with the current filters.</div>';
  const bySlot = {};
  cands.forEach(x => (bySlot[x.r.slot] = bySlot[x.r.slot] || []).push(x));
  $('#slotUps').innerHTML = SLOTS.filter(([k]) => bySlot[k]).map(([k,label]) => '<div class="slotgroup"><h4>'+label+'</h4><div class="ups">'+bySlot[k].sort((a,b) => b.r.v - a.r.v).slice(0,4).map(row).join('')+'</div></div>').join('') || '<div class="muted small">Nothing beats your gear with these filters.</div>';
}
['#upBuild','#wDmg','#maxLvl'].forEach(s => $(s).addEventListener('input', () => renderUpgrades()));
$('#upMode').addEventListener('change', () => { store.set('upMode', upMode()); renderUpgrades(); });

// ---------- Worker ----------
let worker = null;
function getWorker(){
  if(worker) return worker;
  try{ const src = $('#worker-src').textContent; worker = new Worker(URL.createObjectURL(new Blob([src], {type:'text/javascript'}))); }catch(e){ worker = null; }
  return worker;
}
function runInWorker(msg){
  return new Promise((resolve, reject) => {
    const w = getWorker();
    if(!w){ try{ resolve(self.WorkerJob(msg)); }catch(e){ reject(e); } return; }
    const id = Math.random().toString(36).slice(2);
    const on = e => { if(e.data && e.data.id === id){ w.removeEventListener('message', on); e.data.error ? reject(new Error(e.data.error)) : resolve(e.data.result); } };
    w.addEventListener('message', on);
    w.postMessage(Object.assign({id}, msg));
  });
}

// ---------- Dungeon fight ----------
const scen = () => ({fight:+$('#len').value, tankHP:+$('#tankHP').value||6500, dpsHP:+$('#dpsHP').value||3800, bossSwing:2.0, tankAvoid:0.3, spikeChance:0.1, aoeEvery:15, aoeDmg:+$('#aoe').value, meHitsPerSec:0.05, meHitDmg:Math.max(5, Math.round(Engine.levelDefaults(DATA, LEVEL).aoe*0.12)), preCast:0.7, potions:opts().potions, tablet:opts().tablet});
[['#dtps','#dtpsVal',''],['#aoe','#aoeVal',''],['#len','#lenVal',' s']].forEach(([i,o,suf]) => $(i).addEventListener('input', () => $(o).textContent = $(i).value + suf));
function applyLevelDefaults(){
  const d = Engine.levelDefaults(DATA, LEVEL);
  const st = d.dtps < 40 ? 1 : 5, st2 = d.aoe < 100 ? 5 : 25;
  const dt = $('#dtps'); dt.step = st; dt.min = Math.max(st, Math.round(d.dtps*0.3/st)*st); dt.max = Math.round(d.dtps*3/st)*st; dt.value = d.dtps; $('#dtpsVal').textContent = d.dtps;
  const ao = $('#aoe'); ao.step = st2; ao.min = 0; ao.max = Math.round(d.aoe*3/st2)*st2; ao.value = d.aoe; $('#aoeVal').textContent = d.aoe;
  $('#tankHP').value = d.tankHP; $('#tankHP').step = LEVEL < 30 ? 10 : 100;
  $('#dpsHP').value = d.dpsHP; $('#dpsHP').step = LEVEL < 30 ? 10 : 100;
  $('#dungNote').innerHTML = LEVEL < 13 ? '<div class="note">The first dungeons, Ragefire Chasm and Hall of Thanes, are level 13 to 18. This shows how your healing would hold up at level '+LEVEL+'.</div>' : '';
}
let simRunning = false;
$('#run').addEventListener('click', async () => {
  if(simRunning) return; simRunning = true;
  $('#run').disabled = true;
  $('#runState').innerHTML = '<span class="busy"><span class="spin"></span>Simulating 40 fights per build and searching for your limit</span>';
  const bs = activeBuilds();
  const jobs = bs.map(b => ({build:b.key, c:charFor(b), s:scen(), dtps:+$('#dtps').value, mobDiff:+$('#mobLvl').value, cap:CAP_OPTS()}));
  try{
    const res = await runInWorker({type:'sim', jobs});
    renderResults(bs, res);
    $('#runState').innerHTML = '';
  }catch(e){ $('#runState').innerHTML = '<span class="small" style="color:var(--bad)">The simulation failed: '+esc(e.message)+'</span>'; }
  $('#run').disabled = false; simRunning = false;
});
function renderResults(bs, res){
  const s = scen(); const dtps = +$('#dtps').value;
  const by = k => res.find(r => r.build === k);
  const kp = bs.map(b => { const r = by(b.key); return '<div class="kpi" style="--bc:'+b.color+'"><div class="lb"><span class="bdot" style="background:'+b.color+'"></span>'+esc(b.name)+'</div><div class="v">'+fmt(r.maxDTPS)+'<small>tank DPS</small></div><div class="d">Most tank damage per second you can heal through for '+s.fight+' s at level '+LEVEL+', with nobody dying in 9 of 10 fights</div></div>'; }).join('');
  const imb = r => IMBUE[r.dmg.imbue] || '';
  const rows = [
    ['Fights where nobody dies', r => pct(r.at.survival*100,0), 'at '+dtps+' tank damage per second'],
    ['Healing per second', r => fmt(r.at.hps)],
    ['Overheal', r => pct(r.at.overheal*100,0)],
    ['Mana left at the end', r => fmt(r.at.manaEnd)],
    ['Fights where you ran out of mana', r => pct(r.at.oom*100,0)],
    ['Mana from Water Shield', r => fmt(r.at.wsMana)],
    ['Healing over 5 minutes', r => fmt(r.cap.total), 'the number dungeon upgrades are ranked by'],
    ['Melee damage per second', r => fmt(r.dmg.sustained,0)+'<span class="sub">'+esc(imb(r))+'</span>', 'best imbue'+(bs.some(b => talentsOf(b).stormstrike) ? ', Stormstrike when talented' : '')+', no shocks'],
    ['With Earth Shock on cooldown', r => fmt(r.dmg.withShock,0), 'until mana runs out'],
    ['Mana per second while fighting', r => fmt(r.dmg.manaWithShock,1)],
    ['Lightning Bolt damage per second', r => fmt(r.bolt.dps,0), 'standing and casting'],
  ];
  const cmp = '<div class="tablewrap"><table class="cmp"><thead><tr><th></th>'+bs.map(b => '<th><span class="bdot" style="background:'+b.color+'"></span>'+esc(b.name)+'</th>').join('')+'</tr></thead><tbody>'
    + rows.map(r => '<tr><td>'+r[0]+(r[2] ? '<span class="sub">'+r[2]+'</span>' : '')+'</td>'+bs.map(b => '<td>'+r[1](by(b.key))+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
  const spells = {}; bs.forEach(b => { const r = by(b.key); for(const k in r.at.bySpell) spells[k] = 1; });
  const maxEff = Math.max.apply(null, bs.map(b => Math.max.apply(null, Object.values(by(b.key).at.bySpell).map(x => x.eff).concat([1]))));
  const tot = sp => bs.reduce((s2,b) => s2 + ((by(b.key).at.bySpell[sp]||{}).eff||0), 0);
  const order = Object.keys(spells).sort((a,b2) => tot(b2) - tot(a));
  const bars = '<div class="bars">'+order.map(sp => '<div class="bar"><div>'+esc(sp)+'</div><div class="track">'+bs.map(b => { const v = (by(b.key).at.bySpell[sp]||{}).eff||0; return '<div class="seg" title="'+esc(b.name)+': '+fmt(v)+'" style="width:'+(v/maxEff*100).toFixed(1)+'%;background:'+b.hex+'"></div>'; }).join('')+'</div><div class="val">'+bs.map(b => fmt((by(b.key).at.bySpell[sp]||{}).eff||0)).join('<br>')+'</div></div>').join('')+'</div>';
  $('#results').innerHTML = '<div class="kpis">'+kp+'</div>'
    + '<div class="card"><h3>At '+dtps+' tank damage per second</h3>'+cmp+'</div>'
    + '<div class="grid2"><div class="card"><h3>Mana during the fight</h3><div class="legend" style="margin-bottom:8px">'+bs.map(b => '<span><i style="background:'+b.hex+'"></i>'+esc(b.name)+'</span>').join('')+'</div><div class="chart" id="manaChart"></div></div>'
    + '<div class="card"><h3>Healing by spell, average fight</h3><div class="legend" style="margin-bottom:10px">'+bs.map(b => '<span><i style="background:'+b.hex+'"></i>'+esc(b.name)+'</span>').join('')+'</div>'+bars+'</div></div>';
  lineChart($('#manaChart'), bs.map(b => ({name:b.name, color:b.hex, pts:by(b.key).at.manaCurve})), 'mana');
}
function lineChart(el, series, unit){
  const W = Math.max(300, Math.round(el.clientWidth || 560)), H = W < 480 ? 200 : 230, L = 46, R = 12, T = 10, B = 26;
  const n = Math.max.apply(null, series.map(s => s.pts.length));
  const maxY = Math.max.apply(null, series.map(s => Math.max.apply(null, s.pts.concat([1]))));
  const unitStep = maxY > 2000 ? 1000 : maxY > 400 ? 200 : 50;
  const yTop = Math.ceil(maxY/unitStep)*unitStep;
  const x = i => L + (W-L-R)*i/Math.max(1,n-1), y = v => T + (H-T-B)*(1 - v/yTop);
  let g = '';
  for(let k = 0; k <= 4; k++){ const v = yTop*k/4; g += '<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y(v)+'" y2="'+y(v)+'" stroke="#e2e3e3" stroke-width="1"/><text x="'+(L-8)+'" y="'+(y(v)+4)+'" text-anchor="end" fill="#5f6368" font-size="11">'+fmt(v)+'</text>'; }
  const step = (n > 150 ? 60 : 30) * (W < 420 ? 2 : 1);
  for(let s = 0; s < n; s += step) g += '<text x="'+x(s)+'" y="'+(H-6)+'" text-anchor="middle" fill="#5f6368" font-size="11">'+s+' s</text>';
  series.forEach(s => { const d = s.pts.map((v,i) => (i?'L':'M')+x(i).toFixed(1)+' '+y(v).toFixed(1)).join(' '); g += '<path d="'+d+'" fill="none" stroke="'+s.color+'" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'; });
  g += '<line class="xh" x1="0" x2="0" y1="'+T+'" y2="'+(H-B)+'" stroke="#80868b" stroke-width="1" opacity="0"/>';
  series.forEach((s,i) => g += '<circle class="pt" data-i="'+i+'" r="4" fill="'+s.color+'" stroke="#ffffff" stroke-width="2" opacity="0"/>');
  el.innerHTML = '<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Mana over time">'+g+'<rect x="'+L+'" y="'+T+'" width="'+(W-L-R)+'" height="'+(H-T-B)+'" fill="transparent" class="hit"/></svg><div class="tip"></div>';
  const svg = el.querySelector('svg'), tip = el.querySelector('.tip'), xh = el.querySelector('.xh');
  const move = ev => {
    const r = svg.getBoundingClientRect(); const px = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
    const vx = px / r.width * W; const i = Math.max(0, Math.min(n-1, Math.round((vx - L)/(W-L-R)*(n-1))));
    xh.setAttribute('x1', x(i)); xh.setAttribute('x2', x(i)); xh.setAttribute('opacity', .6);
    el.querySelectorAll('.pt').forEach(c => { const s = series[+c.dataset.i]; const v = s.pts[Math.min(i, s.pts.length-1)]; c.setAttribute('cx', x(i)); c.setAttribute('cy', y(v)); c.setAttribute('opacity', 1); });
    tip.innerHTML = '<b>'+i+' s</b><br>'+series.map(s => '<span style="color:'+s.color+'">●</span> '+esc(s.name)+': '+fmt(s.pts[Math.min(i,s.pts.length-1)])+' '+unit).join('<br>');
    tip.style.left = (x(i)/W*r.width)+'px'; tip.style.top = '20px'; tip.style.opacity = 1;
  };
  const leave = () => { tip.style.opacity = 0; xh.setAttribute('opacity', 0); el.querySelectorAll('.pt').forEach(c => c.setAttribute('opacity', 0)); };
  svg.addEventListener('mousemove', move); svg.addEventListener('touchmove', move, {passive:true}); svg.addEventListener('mouseleave', leave); svg.addEventListener('touchend', leave);
}

// ---------- Combat log ----------
const drop = $('#drop');
['dragenter','dragover'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.add('over'); }));
['dragleave','drop'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', ev => { const f = ev.dataTransfer.files[0]; if(f) readLog(f); });
$('#logFile').addEventListener('change', ev => { const f = ev.target.files[0]; if(f) readLog(f); });
function readLog(file){
  $('#logState').innerHTML = '<span class="busy"><span class="spin"></span>Reading '+esc(file.name)+' ('+fmt(file.size/1048576,1)+' MB)</span>';
  const fr = new FileReader();
  fr.onload = async () => {
    try{
      const res = await runInWorker({type:'log', text:fr.result, name:$('#logName').value.trim(), gap:+$('#logGap').value||8});
      if(res.error){ $('#logState').innerHTML = '<span class="small" style="color:var(--bad)">'+esc(res.error)+' If this is your real log, attach the file in the chat with Claude and it can be read there.</span>'; return; }
      $('#logState').innerHTML = ''; renderLog(res);
    }catch(e){ $('#logState').innerHTML = '<span class="small" style="color:var(--bad)">Could not read the log: '+esc(e.message)+'</span>'; }
  };
  fr.onerror = () => { $('#logState').innerHTML = '<span class="small" style="color:var(--bad)">The browser could not open that file.</span>'; };
  fr.readAsText(file);
}
function renderLog(r){
  const t = r.report.totals;
  const head = '<div class="kpis">'
    + '<div class="kpi" style="--bc:var(--pure)"><div class="lb">Healer</div><div class="v" style="font-size:20px;word-break:break-word">'+esc(r.report.player)+'</div><div class="d">'+fmt(r.report.linesRead)+' log lines read</div></div>'
    + '<div class="kpi" style="--bc:var(--pure)"><div class="lb">Fights</div><div class="v">'+t.fights+'<small>'+fmt(t.duration/60,1)+' min in combat</small></div></div>'
    + '<div class="kpi" style="--bc:var(--pure)"><div class="lb">Healing per second</div><div class="v">'+fmt(t.hps)+'<small>'+t.overhealPct+'% overheal</small></div></div>'
    + '<div class="kpi" style="--bc:'+(t.deaths ? 'var(--bad)' : 'var(--good)')+'"><div class="lb">Group deaths</div><div class="v">'+t.deaths+'</div></div></div>';
  const copy = '<div class="card" style="display:grid;gap:10px"><div class="row" style="justify-content:space-between"><h3 style="margin:0">Summary for Claude</h3><button class="btn primary sm" id="copySum">Copy for Claude</button></div><textarea id="sumText" readonly>'+esc(r.text)+'</textarea><div class="small muted">Paste this into the chat and ask for a critique. It holds the numbers per fight, not the raw log.</div></div>';
  const flags = r.obs.length ? '<div class="card" style="display:grid;gap:8px"><h3 style="margin:0">Things the parser noticed</h3>'+r.obs.map(o => '<div class="flag'+(o.kind==='death'?' death':'')+'"><b>'+esc(o.fight)+':</b> '+esc(o.text)+'</div>').join('')+'</div>' : '';
  const fights = '<div class="card" style="display:grid;gap:10px"><h3 style="margin:0">Fights</h3><div class="fights">'+r.report.fights.map((f,i) => '<details class="fight"><summary><div><div style="font-weight:600">'+esc(f.name)+(f.boss ? ' <span class="ease e2">Boss</span>' : '')+(f.deaths.length ? ' <span class="ease e4">'+f.deaths.length+' died</span>' : '')+'</div><div class="small muted">'+f.duration+' s, '+fmt(f.hps)+' HPS, '+f.overhealPct+'% overheal, '+f.idleSeconds+' s without casting</div></div><div class="small muted num">#'+(i+1)+'</div></summary><div class="body">'
    + '<div class="tablewrap"><table class="cmp"><thead><tr><th>Spell</th><th>Casts</th><th>Healing</th><th>Overheal</th><th>Crit</th></tr></thead><tbody>'+f.spells.map(s => '<tr><td>'+esc(s.spell)+'</td><td>'+s.casts+'</td><td>'+fmt(s.effective)+'</td><td>'+s.overhealPct+'%</td><td>'+s.critPct+'%</td></tr>').join('')+'</tbody></table></div>'
    + (f.mana.curve.length > 3 ? '<div><div class="small muted" style="margin-bottom:6px">Mana ('+fmt(f.mana.min)+' lowest of '+fmt(f.mana.max)+')</div><div class="chart" data-curve="'+i+'"></div></div>' : '<div class="small muted">No mana data in this log. Turn on Advanced Combat Logging.</div>')
    + (Object.keys(f.cooldowns).some(k => r.report.known[k]) ? '<div class="small muted">Cooldowns: '+Object.entries(f.cooldowns).filter(([k]) => r.report.known[k]).map(([k,v]) => esc(k)+' '+v.used+' of about '+v.possible).join('; ')+'</div>' : '')
    + (f.deaths.length ? f.deaths.map(d => '<div class="flag death">'+esc(d.who)+' died at '+d.at+' s. Last hits: '+esc(d.lastHits.join('; ')||'unknown')+'. Your casts in the 6 s before: '+d.myCastsLast6s+'.</div>').join('') : '')
    + '</div></details>').join('')+'</div></div>';
  $('#logOut').innerHTML = head + copy + flags + fights;
  $('#copySum').addEventListener('click', async () => {
    try{ await navigator.clipboard.writeText(r.text); toast('Copied. Paste it into the chat.'); }
    catch(e){ const ta = $('#sumText'); ta.focus(); ta.select(); toast('Selected. Copy it with your keyboard or the share menu.'); }
  });
  document.querySelectorAll('.fight').forEach(d => d.addEventListener('toggle', () => {
    const c = d.querySelector('[data-curve]'); if(!d.open || !c || c.dataset.done) return;
    const f = r.report.fights[+c.dataset.curve]; c.dataset.done = 1;
    const n = Math.ceil(f.duration); const pts = []; let j = 0, last = f.mana.curve[0][1];
    for(let s = 0; s <= n; s++){ while(j < f.mana.curve.length && f.mana.curve[j][0] <= s){ last = f.mana.curve[j][1]; j++; } pts.push(last); }
    lineChart(c, [{name:'Mana', color:'#4285f4', pts}], 'mana');
  }));
}

// ---------- Tabs ----------
function show(v){
  ['simulate','upgrades','log'].forEach(k => $('#v-'+k).classList.toggle('on', k === v));
  document.querySelectorAll('.tab').forEach(t => t.setAttribute('aria-selected', t.dataset.v === v ? 'true' : 'false'));
  $('#setup').classList.toggle('on', v !== 'log');
  try{ history.replaceState(null, '', '#'+v); }catch(e){}
  if(v === 'upgrades') renderUpgrades();
}
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => show(t.dataset.v)));

// ---------- Assumptions ----------
$('#assum').innerHTML = DATA.sources.map(([txt, st]) => '<li><span class="status s-'+st+'">'+({forever:'Forever',sim:'Sim rule',vanilla:'Vanilla',est:'Estimate'}[st])+'</span>'+esc(txt)+'</li>').join('');
$('#dataNote').textContent = DATA.version + '. Items: '+ITEMS_META.count+' items of every level from the wowsims Forever database (commit '+ITEMS_META.commit+'), with drop chances from Wowhead Forever and Warcraft DB. "Forever" means client data or Blizzard; "Sim rule" means the community simulator\'s rule; "Vanilla" means a Classic value nobody has confirmed for Forever; "Estimate" is this tool\'s own assumption.';

function refresh(){ renderSheet(); renderQuest(); renderUpgrades(); }
$('#upMode').value = store.get('upMode', LEVEL < 60 ? 'quest' : 'heal');
$('#maxLvl').value = LEVEL;
renderBuildChips(); renderLevel(); renderRoutes(); presetSelect(); renderGear(); renderSrcChips(); applyLevelDefaults(); refresh();
const h = (location.hash||'').slice(1); if(['simulate','upgrades','log'].indexOf(h) >= 0) show(h);
})();
