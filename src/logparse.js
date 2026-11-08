// Combat log parser and healer analysis for WoW Forever (modern CLEU text format).
// Works with and without Advanced Combat Logging. Field positions are found
// structurally, not by fixed offsets, so it tolerates client-version differences.
(function(root){
'use strict';

function splitCSV(s){
  const out = []; let i = 0, n = s.length;
  while(i <= n){
    if(s[i] === '"'){
      let j = i+1, buf = '';
      while(j < n){
        if(s[j] === '"'){ if(s[j+1] === '"'){ buf += '"'; j += 2; continue; } break; }
        buf += s[j++];
      }
      out.push(buf); i = j+2; // skip quote and comma
    } else if(s[i] === '['){ // nested lists (rare in classic) - keep raw until matching ]
      let depth = 0, j = i;
      for(; j < n; j++){ if(s[j]==='[') depth++; else if(s[j]===']'){ depth--; if(depth===0){ j++; break; } } }
      out.push(s.slice(i, j)); i = j+1;
    } else {
      let j = s.indexOf(',', i); if(j < 0) j = n;
      out.push(s.slice(i, j)); i = j+1;
    }
    if(i > n) break;
  }
  return out;
}

// "11/8/2026 20:15:03.123-1  EVENT,..." or "11/8 20:15:03.123  EVENT,..."
const TS = /^(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\s+(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d{1,4}))?(?:[-+]\d+)?\s\s(.*)$/;
function parseTime(m){
  const ms = m[7] ? Number((m[7]+'000').slice(0,3)) : 0;
  // Seconds since start of month (enough for a session; handles midnight via day field)
  return ((Number(m[2])*24 + Number(m[4]))*60 + Number(m[5]))*60 + Number(m[6]) + ms/1000;
}
const isGUID = s => /^(Player|Creature|Pet|Vehicle|GameObject|Item|0000000000000000)/.test(s);
const isFloat = s => /^-?\d+\.\d+$/.test(s);
const isInt = s => /^-?\d+$/.test(s);

// Locate the suffix start after an optional advanced-parameter block beginning at index b.
function suffixStart(f, b){
  if(!isGUID(f[b] || '')) return {s:b, adv:null};
  // advanced block: infoGUID, ownerGUID, curHP, maxHP, AP, SP, armor, [absorb], powerType, curPower, maxPower, powerCost, posX, posY, uiMapID, facing, level
  for(let p = b+8; p < f.length-3; p++){
    if(isFloat(f[p]) && isFloat(f[p+1]) && isInt(f[p+2]) && isFloat(f[p+3])){
      const adv = {
        unit: f[b], curHP:+f[b+2], maxHP:+f[b+3],
        powerType: String(f[p-4]).split(/[:|]/)[0],
        curPower: +String(f[p-3]).split(/[:|]/)[0],
        maxPower: +String(f[p-2]).split(/[:|]/)[0]
      };
      return {s:p+5, adv};
    }
  }
  return {s:b, adv:null};
}

function parseLine(line){
  const m = TS.exec(line); if(!m) return null;
  const t = parseTime(m);
  const f = splitCSV(m[8]);
  const ev = f[0];
  const e = {t, ev};
  if(ev === 'ENCOUNTER_START' || ev === 'ENCOUNTER_END'){
    e.encId = f[1]; e.encName = f[2]; e.success = ev==='ENCOUNTER_END' ? f[5]==='1' : null; return e;
  }
  if(ev === 'ZONE_CHANGE'){ e.zone = f[2]; return e; }
  if(ev === 'COMBATANT_INFO' || ev === 'COMBAT_LOG_VERSION' || ev === 'MAP_CHANGE') return e;
  if(f.length < 9) return e;
  e.src = f[1]; e.srcName = f[2]; e.srcFlags = parseInt(f[3]); e.dst = f[5]; e.dstName = f[6]; e.dstFlags = parseInt(f[7]);
  let b = 9;
  if(ev.startsWith('SPELL_') || ev.startsWith('RANGE_') || ev.startsWith('DAMAGE_')){
    e.spellId = f[9]; e.spell = f[10]; b = 12;
  } else if(ev.startsWith('ENVIRONMENTAL_')){
    e.spell = f[9]; b = 10;
  } else if(ev.startsWith('SWING_')){
    e.spell = 'Melee';
  }
  const ss = suffixStart(f, b);
  e.adv = ss.adv;
  const sfx = f.slice(ss.s);
  if(/_HEAL$/.test(ev)){
    e.amount = +sfx[0];
    const k = sfx.length;
    e.overheal = +sfx[k-3]; e.absorbed = +sfx[k-2]; e.crit = sfx[k-1] === '1';
    if(!(e.overheal >= 0)) e.overheal = 0;
  } else if(/_DAMAGE$/.test(ev) || ev === 'DAMAGE_SHIELD' || ev === 'DAMAGE_SPLIT'){
    e.amount = +sfx[0];
    const base = sfx.length >= 10 ? 1 : 0;
    e.overkill = +sfx[1+base];
    e.crit = sfx[6+base] === '1';
    e.glancing = sfx[7+base] === '1';
  } else if(/_MISSED$/.test(ev)){
    e.missType = sfx[0];
  } else if(/_ENERGIZE$/.test(ev)){
    e.amount = +sfx[0]; e.over = +sfx[1] || 0; e.powerType = sfx[2];
  } else if(/AURA_(APPLIED|REMOVED|REFRESH|APPLIED_DOSE|REMOVED_DOSE)$/.test(ev)){
    e.auraType = f[12];
  }
  return e;
}

const SHAMAN_HEALS = ['Healing Wave','Lesser Healing Wave','Chain Heal','Riptide','Healing Stream'];
const COOLDOWNS = {"Riptide":12, "Nature's Swiftness":180, "Mana Tide Totem":300};

function analyze(text, opts){
  opts = opts || {};
  const lines = text.split(/\r?\n/);
  const evs = [];
  let bad = 0;
  for(const ln of lines){ if(!ln) continue; const e = parseLine(ln); if(e) evs.push(e); else bad++; }
  evs.sort((a,b) => a.t - b.t);
  if(!evs.length) return {error:'No combat log lines found. The file should be WoWCombatLog.txt from your Logs folder.'};

  // Players and the likely shaman healer
  const players = {};
  const isPlayer = g => typeof g === 'string' && g.startsWith('Player-');
  for(const e of evs){
    if(isPlayer(e.src)){
      const p = players[e.src] || (players[e.src] = {guid:e.src, name:e.srcName, heal:0, shamanHeals:0, dmg:0});
      if(/_HEAL$/.test(e.ev)){ p.heal += (e.amount||0)-(e.overheal||0); if(SHAMAN_HEALS.indexOf(e.spell)>=0) p.shamanHeals++; }
      if(/_DAMAGE$/.test(e.ev)) p.dmg += e.amount||0;
    }
  }
  const plist = Object.values(players).sort((a,b) => b.heal-a.heal);
  let me = null;
  if(opts.name) me = plist.find(p => p.name && p.name.toLowerCase().startsWith(opts.name.toLowerCase()));
  if(!me) me = plist.slice().sort((a,b) => b.shamanHeals-a.shamanHeals)[0];
  if(!me) return {error:'No players found in the log.', players:plist};

  // Segment into fights: encounter markers if present, else activity gaps.
  const fights = [];
  const groupGUIDs = new Set();
  for(const e of evs){ if(isPlayer(e.src)) groupGUIDs.add(e.src); if(isPlayer(e.dst)) groupGUIDs.add(e.dst); }
  let cur = null, lastHostile = -1e9;
  const GAP = opts.gap || 8;
  const hostileEvent = e => (/_DAMAGE$|_MISSED$/.test(e.ev)) && ((groupGUIDs.has(e.src) && !groupGUIDs.has(e.dst) && !isPlayer(e.dst)) || (groupGUIDs.has(e.dst) && !isPlayer(e.src)));
  let enc = null;
  for(const e of evs){
    if(e.ev === 'ENCOUNTER_START'){ enc = {name:e.encName, start:e.t}; }
    if(e.ev === 'ENCOUNTER_END'){ if(cur) cur.boss = cur.boss || (enc && enc.name); if(cur) cur.kill = e.success; enc = null; }
    const h = hostileEvent(e);
    if(h){
      if(!cur || e.t - lastHostile > GAP){
        if(cur) fights.push(cur);
        cur = {start:e.t, end:e.t, events:[], boss: enc ? enc.name : null};
      }
      lastHostile = e.t; cur.end = e.t;
    }
    if(cur && e.t <= lastHostile + 0.01 + GAP) cur.events.push(e);
  }
  if(cur) fights.push(cur);
  const real = fights.filter(f => f.end - f.start >= (opts.minFight || 10));

  const known = {};
  for(const e of evs) if(e.src === me.guid && e.ev === 'SPELL_CAST_SUCCESS') known[e.spell] = 1;
  const out = {known, player:me.name, players:plist.map(p => ({name:p.name, heal:Math.round(p.heal)})), linesRead:evs.length, badLines:bad, fights:[]};
  for(const f of real) out.fights.push(fightReport(f, me.guid, groupGUIDs));
  out.totals = totalsOf(out.fights);
  return out;
}

function fightReport(f, my, group){
  const dur = Math.max(1, f.end - f.start);
  const spells = {}; let eff = 0, over = 0;
  const targets = {};
  const casts = {}; const castTimes = [];
  const mana = []; const gains = {};
  let maxMana = 0, dmgTaken = 0, hitsTaken = 0;
  const deaths = []; const recent = {}; // per dest: last damage events
  const enemies = {};
  let myDamage = 0; const dmgSpells = {};
  for(const e of f.events){
    if(e.adv && e.src === my && e.adv.unit === my && e.adv.powerType === '0'){ mana.push([e.t - f.start, e.adv.curPower]); maxMana = Math.max(maxMana, e.adv.maxPower); }
    if(e.src === my && /_HEAL$/.test(e.ev)){
      const s = spells[e.spell] || (spells[e.spell] = {hits:0, crits:0, eff:0, over:0, casts:0});
      const ef = Math.max(0, (e.amount||0) - (e.overheal||0));
      s.hits++; if(e.crit) s.crits++; s.eff += ef; s.over += e.overheal||0; eff += ef; over += e.overheal||0;
      targets[e.dstName] = (targets[e.dstName]||0) + ef;
    }
    if(e.src === my && e.ev === 'SPELL_CAST_SUCCESS'){
      casts[e.spell] = (casts[e.spell]||0)+1; castTimes.push(e.t);
      if(spells[e.spell]) spells[e.spell].casts++;
    }
    if(e.src === my && /_DAMAGE$/.test(e.ev)){ myDamage += e.amount||0; dmgSpells[e.spell] = (dmgSpells[e.spell]||0) + (e.amount||0); }
    if(e.dst === my && /_ENERGIZE$/.test(e.ev) && (e.powerType === '0' || e.powerType === undefined)){
      gains[e.spell] = (gains[e.spell]||0) + Math.max(0,(e.amount||0) - (e.over||0));
    }
    if(e.dst === my && /_DAMAGE$/.test(e.ev)){ dmgTaken += e.amount||0; hitsTaken++; }
    if(group.has(e.dst) && /_DAMAGE$/.test(e.ev)){
      const r = recent[e.dstName] || (recent[e.dstName] = []);
      r.push({t:e.t, by:e.srcName, what:e.spell, amt:e.amount}); if(r.length > 6) r.shift();
    }
    if(!group.has(e.dst) && group.has(e.src) && /_DAMAGE$/.test(e.ev) && e.dstName) enemies[e.dstName] = 1;
    if(e.ev === 'UNIT_DIED' && group.has(e.dst)){
      const r = (recent[e.dstName]||[]).filter(x => e.t - x.t <= 6);
      const myCastsBefore = castTimes.filter(t => e.t - t <= 6 && t <= e.t).length;
      deaths.push({who:e.dstName, at:+(e.t - f.start).toFixed(1), lastHits:r.slice(-3).map(x => x.by+' '+x.what+' '+x.amt), myCastsLast6s:myCastsBefore});
    }
  }
  for(const k in spells){ if(!spells[k].casts) spells[k].casts = casts[k] || 0; }
  // Idle time: gaps > 2.5s between my casts while the group was taking damage
  let idle = 0; castTimes.sort((a,b)=>a-b);
  const pts = [f.start].concat(castTimes, [f.end]);
  for(let i = 1; i < pts.length; i++){ const g = pts[i]-pts[i-1]; if(g > 2.5) idle += g - 2.5; }
  const cdUse = {};
  for(const k in COOLDOWNS){ cdUse[k] = {used:casts[k]||0, possible: Math.floor(dur/COOLDOWNS[k])+1}; }
  const manaStart = mana.length ? mana[0][1] : null, manaEnd = mana.length ? mana[mana.length-1][1] : null;
  const manaMin = mana.length ? Math.min.apply(null, mana.map(x=>x[1])) : null;
  return {
    name: f.boss || ('Pull vs ' + Object.keys(enemies).slice(0,3).join(', ')),
    boss: !!f.boss, kill: f.kill, duration: +dur.toFixed(1),
    healing: Math.round(eff), overheal: Math.round(over), hps: Math.round(eff/dur),
    overhealPct: eff+over ? Math.round(over/(eff+over)*100) : 0,
    spells: Object.entries(spells).map(([n,s]) => ({spell:n, casts:s.casts, hits:s.hits, critPct: s.hits ? Math.round(s.crits/s.hits*100) : 0, effective:Math.round(s.eff), overhealPct: s.eff+s.over ? Math.round(s.over/(s.eff+s.over)*100) : 0})).sort((a,b)=>b.effective-a.effective),
    casts, targets: Object.entries(targets).sort((a,b)=>b[1]-a[1]).map(([n,v]) => ({name:n, healed:Math.round(v)})),
    mana: {start:manaStart, end:manaEnd, min:manaMin, max:maxMana || null, curve:mana.map(x => [+x[0].toFixed(1), x[1]]), gains:Object.fromEntries(Object.entries(gains).map(([k,v])=>[k,Math.round(v)]))},
    cooldowns: cdUse, idleSeconds: +idle.toFixed(1), damageTaken: Math.round(dmgTaken), hitsTaken,
    myDamage: Math.round(myDamage), damageBySpell: Object.fromEntries(Object.entries(dmgSpells).map(([k,v])=>[k,Math.round(v)])),
    deaths
  };
}

function totalsOf(fs){
  const t = {fights:fs.length, duration:0, healing:0, overheal:0, deaths:0};
  fs.forEach(f => { t.duration += f.duration; t.healing += f.healing; t.overheal += f.overheal; t.deaths += f.deaths.length; });
  t.hps = t.duration ? Math.round(t.healing/t.duration) : 0;
  t.overhealPct = t.healing+t.overheal ? Math.round(t.overheal/(t.healing+t.overheal)*100) : 0;
  return t;
}

// Rule-based observations. Each says what was seen and why it matters; no guesses.
function observations(r){
  const obs = [];
  r.fights.forEach(f => {
    const tag = f.name + ' (' + Math.round(f.duration) + 's)';
    const rp = f.cooldowns['Riptide'];
    if(f.duration >= 40 && rp && r.known['Riptide'] && rp.used < rp.possible*0.5)
      obs.push({fight:tag, kind:'cooldown', text:'Riptide cast '+rp.used+' times, room for about '+rp.possible+'. It is cheap and makes your next Chain Heal on that target 25% stronger.'});
    const mt = f.cooldowns['Mana Tide Totem'];
    if(mt && r.known['Mana Tide Totem'] && mt.used === 0 && f.mana.min !== null && f.mana.max && f.mana.min < f.mana.max*0.35)
      obs.push({fight:tag, kind:'mana', text:'Mana dropped to '+Math.round(f.mana.min/f.mana.max*100)+'% without a Mana Tide Totem.'});
    if(f.overhealPct >= 45)
      obs.push({fight:tag, kind:'efficiency', text:'Overheal was '+f.overhealPct+'%. Look at the spell table for which heal landed on full health most.'});
    if(f.idleSeconds >= f.duration*0.3 && f.duration >= 30)
      obs.push({fight:tag, kind:'activity', text:'About '+Math.round(f.idleSeconds)+'s without a cast. If mana allowed, that time can go to damage or downranked heals.'});
    if(r.known['Water Shield'] && f.mana.gains['Water Shield'] === undefined && f.duration >= 30 && f.hitsTaken > 0)
      obs.push({fight:tag, kind:'mana', text:'No mana from Water Shield recorded while you took '+f.hitsTaken+' hits. Check it was up.'});
    f.deaths.forEach(d => obs.push({fight:tag, kind:'death', text:d.who+' died at '+d.at+'s. Last hits: '+(d.lastHits.join('; ')||'unknown')+'. Your casts in the 6s before: '+d.myCastsLast6s+'.'}));
  });
  return obs;
}

// Compact text for pasting into a chat.
function summaryText(r, obs){
  const L = [];
  L.push('WoW Forever combat log summary (healer: '+r.player+')');
  L.push('Fights: '+r.totals.fights+', total '+Math.round(r.totals.duration)+'s, effective healing '+r.totals.healing+' ('+r.totals.hps+' HPS), overheal '+r.totals.overhealPct+'%, group deaths '+r.totals.deaths);
  r.fights.forEach((f,i) => {
    L.push('');
    L.push('#'+(i+1)+' '+f.name+(f.boss ? (f.kill===false?' [wipe]':' [boss]') : '')+' | '+f.duration+'s | '+f.hps+' HPS | overheal '+f.overhealPct+'% | idle '+f.idleSeconds+'s | damage taken '+f.damageTaken+' ('+f.hitsTaken+' hits)');
    L.push('  Spells: '+f.spells.map(s => s.spell+' '+s.casts+'c/'+s.effective+' eff/'+s.overhealPct+'%oh/'+s.critPct+'%crit').join('; '));
    const cds = Object.entries(f.cooldowns).filter(([k]) => r.known[k]);
    if(cds.length) L.push('  Cooldowns (used/possible): '+cds.map(([k,v]) => k+' '+v.used+'/'+v.possible).join(', '));
    if(f.mana.max) L.push('  Mana: start '+f.mana.start+', min '+f.mana.min+', end '+f.mana.end+' of '+f.mana.max+'. Gains: '+(Object.entries(f.mana.gains).map(([k,v])=>k+' '+v).join(', ')||'none logged'));
    else L.push('  Mana: not in log (turn on Advanced Combat Logging)');
    L.push('  Healed: '+f.targets.slice(0,5).map(t => t.name+' '+t.healed).join(', '));
    const oc = Object.entries(f.casts).filter(([k]) => !f.spells.find(s=>s.spell===k)).map(([k,v])=>k+' '+v);
    if(oc.length) L.push('  Other casts: '+oc.join(', '));
    if(f.myDamage) L.push('  My damage: '+f.myDamage+' ('+Object.entries(f.damageBySpell).map(([k,v])=>k+' '+v).join(', ')+')');
    f.deaths.forEach(d => L.push('  Death: '+d.who+' at '+d.at+'s; last hits '+d.lastHits.join(' | ')+'; my casts in prior 6s: '+d.myCastsLast6s));
  });
  if(obs && obs.length){ L.push(''); L.push('Automatic flags:'); obs.forEach(o => L.push('- '+o.fight+': '+o.text)); }
  return L.join('\n');
}

const api = {splitCSV, parseLine, analyze, observations, summaryText};
if(typeof module !== 'undefined' && module.exports) module.exports = api; else root.LogParse = api;
})(typeof window !== 'undefined' ? window : this);
