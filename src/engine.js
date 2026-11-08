// Shaman simulation engine for WoW Forever, levels 1-60.
// Numbers come from DATA (data.js) and, when present, DATA.LV / DATA.RK (levels.js: per-level base
// stats and every spell rank from the Forever client data). Status of each constant is listed in data.js.
(function(root){
'use strict';

// ---------- Seeded RNG ----------
function rng(seed){ let s = seed>>>0 || 1; return function(){ s ^= s<<13; s>>>=0; s ^= s>>>17; s ^= s<<5; s>>>=0; return s/4294967296; }; }

// ---------- Talents ----------
function talentsFromCode(code, TREE_ORDER){
  const parts = String(code||'').split('-');
  const t = {};
  ['ele','enh','res'].forEach((tree,i) => {
    const digits = (parts[i]||'').split('');
    TREE_ORDER[tree].forEach((id,j) => { const n = +(digits[j]||0); if(n) t[id] = n; });
  });
  return t;
}
// Talents after the first n points of a route [[id,count],...]
function talentsAt(route, points){
  const t = {}; let left = Math.max(0, points);
  for(const [id, n] of route){ if(left <= 0) break; const k = Math.min(n, left); t[id] = (t[id]||0) + k; left -= k; }
  return t;
}

// ---------- Ranks ----------
function rankVal(r, L){ return r.b + r.p*Math.max(0, Math.min(L, r.ml || 999) - r.bl); }
function lvlVal(table, L){ let v = 0; if(table) for(const row of table) if(row[0] <= L) v = row[1]; return v; }
function lvlRow(table, L, allowMage){ let r = null; if(table) for(const row of table) if(row[0] <= L && (!row[4] || allowMage)) r = row; return r; }
function pickRank(list, L, allowBook){ let best = null; if(!list) return null; for(const r of list){ if(r.l <= L && (!r.book || allowBook)) best = r; } return best; }

// ---------- Gear ----------
function sumGear(gear, ITEMS, SETS){
  const s = {str:0,agi:0,sta:0,int:0,spi:0,healing:0,spellDamage:0,natureDamage:0,mp5:0,critRating:0,hitRating:0,ap:0,armor:0};
  let mh = null, oh = null; const setCount = {};
  Object.entries(gear).forEach(([slot,id]) => {
    if(!id) return;
    const it = ITEMS[id]; if(!it) return;
    for(const k in s) if(it.s && it.s[k]) s[k] += it.s[k];
    if(slot === 'mainhand' && it.w) mh = it;
    if(slot === 'offhand') oh = it;
    if(it.set) setCount[it.set] = (setCount[it.set]||0) + 1;
  });
  const activeSets = [];
  if(SETS) for(const name in setCount){
    (SETS[name]||[]).forEach(b => { if(setCount[name] >= b.n){ for(const k in b.s) s[k] = (s[k]||0) + b.s[k]; activeSets.push({set:name, n:b.n, text:b.t, counted:b.ok}); } });
  }
  return {s, mh, oh, activeSets};
}

// ---------- Character ----------
function character(opts, D){
  const L = Math.max(1, Math.min(60, opts.level || 60));
  const g = opts.gearStats, t = opts.talents, b = opts.buffs || {}, x = opts.extra || {};
  const LV = D.LV;
  const B = LV ? {hp:LV.hp[L-1], mana:LV.mana[L-1], str:LV.str[L-1], agi:LV.agi[L-1], sta:LV.sta[L-1], int:LV.int[L-1], spi:LV.spi[L-1]} : D.base;
  const perInt = LV ? LV.cpi[L-1] : D.crit.perInt, perAgi = LV ? LV.cpa[L-1] : D.crit.perAgi;
  const apBase = LV ? LV.apt[L-1] : D.ap.base;
  const allStat = b.motw ? (b.motwStats !== undefined ? b.motwStats : D.motwByLevel ? lvlVal(D.motwByLevel, L) : D.buffs.motw.allStats) : 0;
  const aiInt = b.ai ? (b.aiInt !== undefined ? b.aiInt : D.aiByLevel ? lvlVal(D.aiByLevel, L) : D.buffs.ai.int) : 0;
  const strT = B.str + g.str + allStat + (x.str||0);
  const agiT = B.agi + g.agi + allStat + (x.agi||0);
  const staT = B.sta + g.sta + allStat + (x.sta||0);
  let intT = B.int + g.int + allStat + aiInt + (x.int||0);
  intT = intT * (1 + 0.02*(t.ancknow||0));
  const spiT = B.spi + g.spi + allStat + (x.spi||0);
  const mana = B.mana + Math.min(intT,20) + 15*Math.max(0,intT-20);
  const hp = B.hp + Math.min(staT,20) + 10*Math.max(0,staT-20);
  const hasMelee = !!(opts.mh);
  const critFromRating = (g.critRating + (x.critRating||0)) / D.ratings.crit;
  const hitFromRating = (g.hitRating + (x.hitRating||0)) / D.ratings.hit;
  const ts = hasMelee ? (t.thundering||0) : 0;
  const spellCrit = D.crit.spellBase + intT*perInt + critFromRating + ts;
  const healCrit = spellCrit + (t.tidalmastery||0);
  const meleeCrit = D.crit.meleeBase + agiT*perAgi + critFromRating + ts;
  const hit = D.race.hit + hitFromRating + (t.tidalfocus||0);
  const mq = 0.15*(t.mentalquick||0)*intT;
  const healing = g.healing + (x.healing||0) + mq;
  const spellDamage = g.spellDamage + (g.natureDamage||0) + (x.spellDamage||0) + mq;
  const ap = apBase + D.ap.perStr*strT + g.ap + (x.ap||0) + 0.5*(t.mentaldex||0)*intT;
  const mp5 = g.mp5 + (x.mp5||0);
  const spiritRegen = D.regen.spiritBase + spiT/D.regen.spiritDiv;
  const mindful = [0,0.17,0.33,0.5][t.mindful||0];
  const armor = (g.armor||0) + 2*agiT + (x.armor||0);
  return {level:L, baseMana:B.mana, armor, perAgi, str:strT, agi:agiT, sta:staT, int:intT, spi:spiT, mana, hp, spellCrit, healCrit, meleeCrit, hit, healing, spellDamage, ap, mp5, spiritRegen, mindful, hasMelee, mh:opts.mh, oh:opts.oh, t};
}

// ---------- Heal spells available at the character's level ----------
function healSpells(c, D, o){
  const t = c.t, L = c.level || 60, RK = D.RK;
  const pur = 1 + 0.02*(t.purification||0);
  const hwBonus = 1 + [0,0.08,0.17,0.25][t.healingway||0];
  const costMul = 1 - 0.01*(t.tidalfocus||0);
  const crit = Math.min(1, c.healCrit/100), cm = D.crit.healMult;
  const exp = base => base * (1 + crit*(cm-1));
  const S = {crit, critMult:cm};
  const mk = (r, name, extra) => r ? Object.assign({name, cast:r.cast, mana:r.mana*costMul, base:(rankVal(r, L) + r.c*c.healing)*pur*(extra||1), spread:r.v||0.13}) : null;
  if(RK){
    S.HW = mk(pickRank(RK.hw, L, o.tablet), 'Healing Wave', hwBonus);
    if(S.HW) S.HW.cast -= 0.1*(t.ihw||0);
    S.LHW = mk(pickRank(RK.lhw, L), 'Lesser Healing Wave');
    const ch = pickRank(RK.ch, L);
    S.CH = ch ? Object.assign(mk(ch, 'Chain Heal'), {jumps:3, falloff:0.5}) : null;
    const rt = t.riptide ? pickRank(RK.rt, L) : null;
    if(rt) S.RT = {name:'Riptide', cast:0, mana:rt.mana*costMul, tick:(rankVal(rt, L) + rt.c*c.healing)*pur, ticks:rt.ticks, every:rt.period, cd:12};
    const h = pickRank(RK.hst, L);
    if(h) S.HST = {name:'Healing Stream Totem', tick:(h.tick + h.c*c.healing)*pur*(1+0.1*(t.restotems||0)), every:h.period, mana:h.mana*(1-0.05*(t.totemicfocus||0))};
    const m = pickRank(RK.ms, L);
    if(m) S.MS = {name:'Mana Spring Totem', tick:m.tick*(1+0.05*(t.restotems||0)), every:m.period, mana:m.mana*(1-0.05*(t.totemicfocus||0))};
    const mt = t.manatide ? pickRank(RK.mtt, L) : null;
    if(mt) S.MT = {tick:mt.tick, ticks:mt.ticks, every:mt.period, total:mt.tick*mt.ticks, cd:300, mana:mt.mana};
  } else {
    const hwR = o.tablet ? D.spells.hw10 : D.spells.hw9;
    S.HW = {name:'Healing Wave', cast: hwR.cast - 0.1*(t.ihw||0), mana: hwR.mana*costMul, base:(hwR.avg + hwR.coef*c.healing)*pur*hwBonus};
    S.LHW = {name:'Lesser Healing Wave', cast: D.spells.lhw.cast, mana: D.spells.lhw.mana*costMul, base:(D.spells.lhw.avg + D.spells.lhw.coef*c.healing)*pur};
    S.CH = {name:'Chain Heal', cast: D.spells.ch.cast, mana: D.spells.ch.mana*costMul, base:(D.spells.ch.avg + D.spells.ch.coef*c.healing)*pur, jumps:3, falloff:0.5};
    if(t.riptide){ const r = D.spells.riptide; S.RT = {name:'Riptide', cast:0, mana:r.mana*costMul, tick:(r.tick + r.coefTick*c.healing)*pur, ticks:r.ticks, every:r.every, cd:r.cd}; }
    const h = D.spells.hst; S.HST = {name:'Healing Stream Totem', tick:(h.tick + h.coefTick*c.healing)*pur*(1+0.1*(t.restotems||0)), every:h.every, mana:h.mana*(1-0.05*(t.totemicfocus||0))};
    S.MS = {name:'Mana Spring Totem', tick:D.spells.manaspring.tick*(1+0.05*(t.restotems||0)), every:D.spells.manaspring.every, mana:D.spells.manaspring.mana*(1-0.05*(t.totemicfocus||0))};
    if(t.manatide) S.MT = Object.assign({}, D.spells.manatide);
  }
  for(const k of ['HW','LHW','CH']) if(S[k]){ S[k].exp = exp(S[k].base); S[k].spread = S[k].spread || D.spells.spread; }
  if(S.RT) S.RT.expTick = S.RT.tick * (D.spells.riptide.ticksCrit ? (1+crit*(cm-1)) : 1);
  return S;
}

// ---------- Deterministic healing capacity ----------
function capacity(c, D, o){
  const T = o.horizon || 300;
  const S = healSpells(c, D, o);
  const want = o.mix || {HW:0.7, CH:0.3};
  const mix = {}; let wsum = 0;
  for(const k in want) if(S[k]){ mix[k] = want[k]; wsum += want[k]; }
  if(!wsum){ mix.HW = 1; wsum = 1; }
  let cpm = 0, hpc = 0, tpc = 0;
  for(const k in mix){ const sp = S[k], w = mix[k]/wsum; const amt = k==='CH' ? sp.exp*(1+0.5+0.25)*o.chainEff : sp.exp; hpc += w*amt*o.healEff; cpm += w*sp.mana; tpc += w*Math.max(sp.cast, D.gcd); }
  const C = cpm/tpc, HPSf = hpc/tpc;
  const msRate = S.MS ? S.MS.tick/S.MS.every : 0;
  const regenCast = c.mp5/5 + c.mindful*c.spiritRegen + msRate;
  const regenIdle = c.mp5/5 + c.spiritRegen + msRate;
  const critRate = (c.healCrit/100)/tpc;
  const wsRate = c.t.watershield ? Math.min(1/D.spells.watershield.icd, critRate + (o.hitsPerSec||0)) : 0;
  const wsMana = wsRate * D.spells.watershield.pct * c.mana;
  let budget = c.mana - (S.HST ? S.HST.mana : 0) - (S.MS ? S.MS.mana : 0);
  let extraHeal = S.HST ? T/S.HST.every * S.HST.tick * o.hstTargets * o.healEff : 0;
  let busy = (S.HST ? D.totemGcd : 0) + (S.MS ? D.totemGcd : 0);
  if(S.MT) budget += Math.floor(T/S.MT.cd + 1) * S.MT.total;
  if(o.potions) budget += Math.floor(T/D.potion.cd + 1) * potionMana(c.level, D);
  if(S.RT){ const n = Math.floor(T/S.RT.cd); extraHeal += n*S.RT.expTick*S.RT.ticks*o.healEff; budget -= n*S.RT.mana; busy += n*D.gcd; }
  const avail = Math.max(0, T - busy);
  const r_c = regenCast + wsMana, r_i = regenIdle + wsMana*0.3;
  let tc;
  if(C <= r_c) tc = avail;
  else tc = Math.max(0, Math.min(avail, (budget + avail*r_i)/(C - r_c + r_i)));
  const total = tc*HPSf + extraHeal;
  const oomAt = C <= r_c ? Infinity : budget/(C - r_c);
  return {total, hps: total/T, castingShare: avail ? tc/avail : 0, oomAt, fillerHPS:HPSf, fillerHPM: hpc/cpm, manaPerSec:C, regenCast:r_c, regenIdle:r_i, spells:S};
}
// Best mana potion usable at this level (Minor 5, Lesser 14, Mana 22, Greater 31, Superior 41, Major 49; averages from Forever tooltips)
function potionMana(L, D){ const P = D.potions || [[5,160],[14,320],[22,520],[31,800],[41,1200],[49,1800]]; let m = 0; for(const [lv, v] of P) if((L||60) >= lv) m = v; return m; }

// ---------- Dungeon fight Monte Carlo ----------
function dungeonFight(c, D, o, seed, dtps){
  const R = rng(seed);
  const S = healSpells(c, D, o);
  const dt = 0.1, T = o.fight;
  const party = [
    {name:'Tank', max:o.tankHP, hp:o.tankHP, tank:true},
    {name:'DPS 1', max:o.dpsHP, hp:o.dpsHP}, {name:'DPS 2', max:o.dpsHP, hp:o.dpsHP}, {name:'DPS 3', max:o.dpsHP, hp:o.dpsHP},
    {name:'You', max:c.hp, hp:c.hp, me:true}
  ];
  const tank = party[0], me = party[4];
  let mana = c.mana, t = 0, casting = null, gcdUntil = 0, lastSpend = -10;
  const cd = {RT:0, NS:0, MT:0, POT:0};
  let ws = c.t.watershield ? 3 : 0, wsNext = 0;
  const hots = [];
  let mtLeft = 0, mtNext = 0;
  const potMana = potionMana(c.level, D);
  const out = {healing:0, overheal:0, bySpell:{}, deaths:[], manaCurve:[], oomTime:null, casts:{}, wsMana:0};
  let nextSwing = 0.5, nextAoe = o.aoeEvery > 0 && o.aoeDmg > 0 ? o.aoeEvery*0.6 : Infinity, nextHST = 2, nextMS = 2;
  let totems = !(S.HST || S.MS);
  const swing = o.bossSwing, avoid = o.tankAvoid;
  const perHit = dtps*swing/(1-avoid);
  const credit = (sp, eff, over) => { const b = out.bySpell[sp] || (out.bySpell[sp] = {eff:0, over:0}); b.eff += eff; b.over += over; out.healing += eff; out.overheal += over; };
  const heal = (u, amt, sp) => { if(u.hp <= 0) return; const room = u.max - u.hp; const eff = Math.min(room, amt); u.hp += eff; credit(sp, eff, amt-eff); };
  const procWS = () => { if(ws > 0 && t >= wsNext){ const g = D.spells.watershield.pct*c.mana; mana = Math.min(c.mana, mana + g); out.wsMana += g; ws--; wsNext = t + D.spells.watershield.icd; } };
  const roll = (sp) => { const isCrit = R() < S.crit; const v = sp.base * (1 + (R()-0.5)*sp.spread) * (isCrit ? S.critMult : 1); if(isCrit) procWS(); return v; };
  const spend = (m) => { mana -= m; lastSpend = t; };
  const deficit = u => u.hp > 0 ? u.max - u.hp : 0;
  const start = (key, target, castTime, cost) => { spend(cost); out.casts[key] = (out.casts[key]||0)+1; casting = {key, target, end: t + castTime}; gcdUntil = t + Math.max(D.gcd, castTime); };
  const incomingSoon = (u, secs) => u.tank ? dtps*secs : 0;
  for(; t < T; t += dt){
    if(t >= nextSwing){ nextSwing += swing; if(tank.hp > 0 && R() >= avoid){ let d = perHit*(0.8 + R()*0.4); if(R() < o.spikeChance) d *= 1.5; tank.hp -= d; } }
    if(t >= nextAoe){ nextAoe += o.aoeEvery; party.forEach(u => { if(u.hp > 0){ u.hp -= o.aoeDmg*(0.85+R()*0.3); if(u.me) procWS(); } }); }
    if(o.meHitsPerSec > 0 && R() < o.meHitsPerSec*dt){ me.hp -= o.meHitDmg || 60; procWS(); }
    party.forEach(u => { if(u.hp <= 0 && !u.dead){ u.dead = true; out.deaths.push({who:u.name, t:+t.toFixed(1)}); } });
    if(totems && S.HST && t >= nextHST){ nextHST += S.HST.every; party.forEach(u => heal(u, S.HST.tick, 'Healing Stream Totem')); }
    if(totems && S.MS && t >= nextMS){ nextMS += S.MS.every; mana = Math.min(c.mana, mana + S.MS.tick); }
    for(let i = hots.length-1; i >= 0; i--){ const h = hots[i]; if(t >= h.next){ h.next += h.every; h.left--; const isCrit = D.spells.riptide.ticksCrit && R() < S.crit; heal(h.target, h.tick*(isCrit?S.critMult:1), 'Riptide'); if(h.left <= 0) hots.splice(i,1); } }
    if(S.MT && mtLeft > 0 && t >= mtNext){ mtNext += S.MT.every; mtLeft--; mana = Math.min(c.mana, mana + S.MT.tick); }
    const in5 = (t - lastSpend) < 5;
    mana = Math.min(c.mana, mana + dt*(c.mp5/5 + c.spiritRegen*(in5 ? c.mindful : 1)));
    if(casting && t >= casting.end){
      const k = casting.key, u = casting.target;
      if(k === 'HW' || k === 'LHW'){ heal(u, roll(S[k]), S[k].name); }
      else if(k === 'CH'){
        const alive = party.filter(p => p.hp > 0 && p !== u).sort((a,b) => deficit(b)-deficit(a));
        let mult = 1; const first = hots.find(h => h.target === u) ? 1.25 : 1;
        heal(u, roll(S.CH)*first, S.CH.name);
        for(let j = 0; j < S.CH.jumps-1 && j < alive.length; j++){ mult *= S.CH.falloff; heal(alive[j], roll(S.CH)*mult, S.CH.name); }
      }
      casting = null;
    }
    if(mana < 0.02*c.mana && out.oomTime === null) out.oomTime = +t.toFixed(1);
    if(Math.abs(t - Math.round(t)) < dt/2) out.manaCurve.push(Math.max(0, mana));
    if(casting || t < gcdUntil) continue;
    if(!totems){ const cost = (S.HST ? S.HST.mana : 0) + (S.MS ? S.MS.mana : 0); if(mana >= cost){ spend(cost); totems = true; nextHST = t + 2; nextMS = t + 2; gcdUntil = t + ((S.HST?1:0)+(S.MS?1:0))*D.totemGcd; } continue; }
    if(c.t.watershield && ws === 0){ ws = 3; gcdUntil = t + D.gcd; out.casts.WS = (out.casts.WS||0)+1; continue; }
    if(S.MT && t >= cd.MT && mana < 0.55*c.mana){ cd.MT = t + S.MT.cd; mtLeft = S.MT.ticks; mtNext = t + S.MT.every; gcdUntil = t + D.totemGcd; spend(S.MT.mana); out.casts.MTT = (out.casts.MTT||0)+1; continue; }
    if(o.potions && potMana && t >= cd.POT && mana < c.mana - potMana*1.05){ cd.POT = t + D.potion.cd; mana += potMana; out.casts.Potion = (out.casts.Potion||0)+1; }
    const alive = party.filter(p => p.hp > 0);
    const low = alive.slice().sort((a,b) => a.hp/a.max - b.hp/b.max)[0];
    if(low && low.hp/low.max < 0.35){
      if(c.t.natswift && t >= cd.NS && mana >= S.HW.mana){ cd.NS = t + 180; spend(S.HW.mana); out.casts.NS = (out.casts.NS||0)+1; out.casts.HW = (out.casts.HW||0)+1; heal(low, roll(S.HW), S.HW.name); gcdUntil = t + D.gcd; continue; }
      if(S.LHW && mana >= S.LHW.mana){ start('LHW', low, S.LHW.cast, S.LHW.mana); continue; }
    }
    if(S.CH){ const hurt = alive.filter(p => deficit(p) >= S.CH.base*0.5).length;
      if(hurt >= 3 && mana >= S.CH.mana){ const tgt = alive.slice().sort((a,b) => deficit(b)-deficit(a))[0]; start('CH', tgt, S.CH.cast, S.CH.mana); continue; } }
    if(S.RT && t >= cd.RT && tank.hp > 0 && (deficit(tank) + incomingSoon(tank, 6)) >= S.RT.tick*S.RT.ticks*0.6 && mana >= S.RT.mana){
      cd.RT = t + S.RT.cd; spend(S.RT.mana); out.casts.RT = (out.casts.RT||0)+1;
      const ex = hots.find(h => h.target === tank); if(ex) hots.splice(hots.indexOf(ex),1);
      hots.push({target:tank, tick:S.RT.tick, left:S.RT.ticks, every:S.RT.every, next:t+S.RT.every}); gcdUntil = t + D.gcd; continue;
    }
    if(tank.hp > 0 && deficit(tank) + incomingSoon(tank, S.HW.cast)*o.preCast >= S.HW.base*0.9 && mana >= S.HW.mana){
      if(S.LHW && tank.hp/tank.max < 0.5 && mana >= S.LHW.mana && deficit(tank) < S.HW.base*0.6){ start('LHW', tank, S.LHW.cast, S.LHW.mana); continue; }
      start('HW', tank, S.HW.cast, S.HW.mana); continue;
    }
    const other = alive.filter(p => !p.tank).sort((a,b) => deficit(b)-deficit(a))[0];
    if(other && deficit(other) >= S.HW.base*0.85 && mana >= S.HW.mana){ start('HW', other, S.HW.cast, S.HW.mana); continue; }
    if(other && S.LHW && deficit(other) >= S.LHW.base*0.9 && mana >= S.LHW.mana){ start('LHW', other, S.LHW.cast, S.LHW.mana); continue; }
  }
  out.manaEnd = Math.max(0, mana);
  out.tankDied = !!tank.dead; out.anyDied = party.some(p => p.dead);
  return out;
}

function runScenario(c, D, o, n, dtps, seed0){
  const runs = []; for(let i = 0; i < n; i++) runs.push(dungeonFight(c, D, o, (seed0||1)+i*7919, dtps));
  const agg = {survival: runs.filter(r => !r.anyDied).length/n, tankSurvival: runs.filter(r => !r.tankDied).length/n,
    hps: avg(runs.map(r => r.healing))/o.fight, overheal: sum(runs.map(r=>r.overheal))/Math.max(1,sum(runs.map(r=>r.healing+r.overheal))),
    manaEnd: avg(runs.map(r => r.manaEnd)), oom: runs.filter(r => r.oomTime !== null).length/n,
    oomTime: avg(runs.filter(r=>r.oomTime!==null).map(r=>r.oomTime)), wsMana: avg(runs.map(r=>r.wsMana)), bySpell:{}, casts:{}, manaCurve:[]};
  runs.forEach(r => { for(const k in r.bySpell){ const b = agg.bySpell[k] || (agg.bySpell[k] = {eff:0,over:0}); b.eff += r.bySpell[k].eff/n; b.over += r.bySpell[k].over/n; } for(const k in r.casts) agg.casts[k] = (agg.casts[k]||0) + r.casts[k]/n; });
  const L = Math.min.apply(null, runs.map(r => r.manaCurve.length));
  for(let i = 0; i < L; i++) agg.manaCurve.push(avg(runs.map(r => r.manaCurve[i])));
  return agg;
}

function maxDTPS(c, D, o, n, need){
  let lo = 2, hi = o.dtpsMax || (D.LV ? Math.max(80, 12*D.LV.eliteDPS[(c.level||60)-1]) : 3000);
  for(let i = 0; i < 10; i++){
    const mid = (lo+hi)/2;
    const r = runScenario(c, D, o, n, mid, 1);
    if(r.survival >= need) lo = mid; else hi = mid;
  }
  return lo >= 100 ? Math.round(lo/5)*5 : Math.round(lo);
}

// ---------- Melee and spell damage (expected values) ----------
function mobTable(D, diff){ return D.mob[diff >= 3 ? 63 : 60]; }
function mobDiffOf(o){ return o.mobDiff !== undefined ? o.mobDiff : ((o.mobLevel||60) >= 63 ? 3 : 0); }
function damage(c, D, o){
  const t = c.t, L = c.level || 60, RK = D.RK, out = {parts:{}, mana:0};
  const mob = mobTable(D, mobDiffOf(o));
  const miss = Math.max(0, mob.miss - c.hit)/100;
  const dodge = mob.dodge/100, parry = (o.front ? mob.parry : 0)/100, glance = mob.glance/100;
  const crit = Math.min(1, Math.max(0, (c.meleeCrit - mob.critPen)/100));
  const spellMiss = Math.max(0, mob.spellMiss - c.hit)/100;
  const sCrit = Math.min(1, c.spellCrit/100);
  const w = c.mh && c.mh.w ? c.mh.w : {min:1, max:2, speed:2.0};
  const avgW = (w.min + w.max)/2;
  const twoH = c.mh && c.mh.two;
  const norm = twoH ? 3.3 : (c.mh && c.mh.wt === 'Dagger' ? 1.7 : 2.4);
  const ew = t.eleweapons || 0;
  // Imbue: use the one asked for if it is learned, otherwise the best one available
  let imbue = o.imbue || 'windfury';
  const avail = {windfury: RK ? pickRank(RK.wf, L) : {b:D.imbue.windfury.ap, p:0, bl:60, ml:0}, flametongue: RK ? pickRank(RK.ft, L) : {b:D.imbue.flametongue.perSpeed*100, p:0, bl:60, ml:0}, rockbiter: RK ? pickRank(RK.rb, L) : {b:D.imbue.rockbiter.ap, p:0, bl:60, ml:0}};
  if(imbue !== 'none' && !avail[imbue]) imbue = avail.windfury ? 'windfury' : avail.flametongue ? 'flametongue' : 'rockbiter';
  out.imbue = imbue;
  let ap = c.ap;
  if(imbue === 'rockbiter') ap += rankVal(avail.rockbiter, L) * (1 + [0,0.07,0.13,0.20][ew]);
  // Target armor cuts physical damage: armor / (armor + 400 + 85 x attacker level), capped at 75% (wowsims-forever)
  const diff = mobDiffOf(o);
  const tArmor = Math.max(0, (D.LV && D.LV.mobArmor ? D.LV.mobArmor[Math.max(1, Math.min(D.LV.mobArmor.length, L + diff)) - 1] : mob.armor || 0) - (o.armorDebuff || 0));
  const armorMult = 1 - Math.min(0.75, tArmor/(tArmor + 400 + 85*L));
  const land = 1 - miss - dodge - parry;
  const critW = Math.min(crit, land-glance);
  const whiteMult = (land - glance - critW) + glance*mob.glanceDmg + critW*D.crit.meleeMult;
  const yellowMult = (land - Math.min(crit,land)) + Math.min(crit,land)*D.crit.meleeMult;
  const swingDmg = apX => avgW + apX/14*w.speed;
  const fl = t.flurry || 0;
  const flurryUp = fl ? 1 - Math.pow(1-crit*land, 3) : 0;
  const haste = 1 + 0.06*fl*flurryUp;
  const swingsPerSec = haste / w.speed;
  out.parts['Melee'] = swingsPerSec * swingDmg(ap) * whiteMult * armorMult;
  let specialHitsPerSec = 0;
  if(t.stormstrike){
    out.parts['Stormstrike'] = 1.5*(avgW + ap/14*norm) * yellowMult * armorMult / 6;
    specialHitsPerSec += land/6;
    out.mana += 0.08*c.baseMana / 6;
  }
  const hitsPerSec = swingsPerSec*land + specialHitsPerSec;
  if(imbue === 'windfury'){
    const lam = hitsPerSec * D.imbue.windfury.chance;
    const rate = lam/(1 + lam*D.imbue.windfury.icd);
    const bonusAP = rankVal(avail.windfury, L) * (1 + [0,0.13,0.27,0.40][ew]);
    out.parts['Windfury'] = rate * D.imbue.windfury.attacks * swingDmg(ap + bonusAP) * yellowMult * armorMult;
  } else if(imbue === 'flametongue'){
    const per = (rankVal(avail.flametongue, L)*w.speed/100 + D.imbue.flametongue.coef*c.spellDamage) * (1 + [0,0.05,0.10,0.15][ew]);
    out.parts['Flametongue'] = swingsPerSec*land * per * (1-spellMiss) * (1 + sCrit*(D.crit.spellMult-1));
  }
  const sf = t.shamfocus ? 0.55 : 1, conv = 1 - 0.02*(t.convection||0), conc = 1 + 0.01*(t.concussion||0);
  if(o.shock === 'earth'){
    const es = RK ? pickRank(RK.es, L) : {b:D.spells.earthshock.avg, p:0, bl:60, ml:0, c:D.spells.earthshock.coef, mana:D.spells.earthshock.mana};
    if(es){ const ssBonus = t.stormstrike ? 1.2 : 1;
      out.parts['Earth Shock'] = (rankVal(es, L) + es.c*c.spellDamage)*conc*ssBonus*(1-spellMiss)*(1 + sCrit*(D.crit.spellMult-1)) / 6;
      out.mana += es.mana*sf*conv/6; }
  } else if(o.shock === 'flame'){
    const fs = RK ? pickRank(RK.fs, L, false) : null;
    if(fs){ out.parts['Flame Shock'] = ((rankVal(fs, L) + fs.c*c.spellDamage)*(1 + sCrit*(D.crit.spellMult-1)) + (fs.tick*fs.ticks + fs.tc*fs.ticks*c.spellDamage))*(1-spellMiss) / 6;
      out.mana += fs.mana*sf*conv/6; }
  }
  out.dps = Object.values(out.parts).reduce((a,b)=>a+b,0);
  out.manaPerSec = out.mana; delete out.mana;
  out.crit = crit*100; out.miss = miss*100; out.ap = ap; out.weapon = w; out.armorMult = armorMult; out.targetArmor = tArmor;
  return out;
}

function lbRank(c, D){ const L = c.level || 60; if(D.RK){ const r = pickRank(D.RK.lb, L); return r ? {avg:rankVal(r, L), cast:r.cast, mana:r.mana, coef:r.c} : null; } return D.spells.lightningbolt; }
function boltDPS(c, D, o){
  const lb = lbRank(c, D), t = c.t; if(!lb) return {dps:0, manaPerSec:0};
  const mob = mobTable(D, mobDiffOf(o));
  const spellMiss = Math.max(0, mob.spellMiss - c.hit)/100;
  const sCrit = Math.min(1, (c.spellCrit + 5*(t.callthunder||0))/100);
  const furyMult = D.crit.spellMult + 0.2*(t.elefury||0)*(D.crit.spellMult-1);
  const cast = Math.max(D.gcd, lb.cast - [0,0.17,0.33,0.5][t.alacrity||0]);
  const per = (lb.avg + lb.coef*c.spellDamage)*(1+0.01*(t.concussion||0))*(1-spellMiss)*(1 + sCrit*(furyMult-1));
  const overload = [0,0.10,0.20,0.30][t.overload||0]*0.5;
  return {dps: per*(1+overload)/cast, manaPerSec: lb.mana*(1-0.02*(t.convection||0))/cast};
}

// Lightning Bolt casting for T seconds from full mana.
function casterFight(c, D, o){
  const T = o.T || 120, t = c.t, lb = lbRank(c, D);
  if(!lb) return {damage:0, dps:0, burstDPS:0, oomAt:Infinity, manaPerSec:0};
  const mob = mobTable(D, mobDiffOf(o));
  const hitP = 1 - Math.max(0, mob.spellMiss - c.hit)/100;
  const sCrit = Math.min(1, (c.spellCrit + 5*(t.callthunder||0))/100);
  const furyMult = D.crit.spellMult + 0.2*(t.elefury||0)*(D.crit.spellMult-1);
  let cast = lb.cast - [0,0.17,0.33,0.5][t.alacrity||0];
  if(t.lmastery) cast = cast - 0.5*Math.min(1, 15/T);
  cast = Math.max(D.gcd, cast);
  const overload = [0,0.10,0.20,0.30][t.overload||0]*0.5;
  const per = (lb.avg + lb.coef*c.spellDamage)*(1+0.01*(t.concussion||0))*hitP*(1 + sCrit*(furyMult-1))*(1+overload);
  const cost = lb.mana*(1-0.02*(t.convection||0))*(t.elefocus ? 1 - 0.1/1.1 : 1);
  const C = cost/cast;
  const critPerSec = hitP*sCrit/cast;
  const ws = t.watershield ? Math.min(1/D.spells.watershield.icd, critPerSec)*D.spells.watershield.pct*c.mana : 0;
  const Rg = c.mp5/5 + c.mindful*c.spiritRegen + ws;
  const tc = C <= Rg ? T : Math.min(T, c.mana/(C - Rg));
  const frac = C <= Rg ? 1 : Math.min(1, Rg/C);
  const castTime = tc + (T - tc)*frac;
  return {damage: per/cast*castTime, dps: per/cast*castTime/T, burstDPS: per/cast, oomAt: C <= Rg ? Infinity : tc, manaPerSec: C};
}

// ---------- Questing: one normal mob at a time, then walk, eat and drink ----------
function boltStats(c, D, diff){
  const lb = lbRank(c, D), t = c.t; if(!lb) return null;
  const mob = mobTable(D, diff);
  const hitP = 1 - Math.max(0, mob.spellMiss - c.hit)/100;
  const sCrit = Math.min(1, (c.spellCrit + 5*(t.callthunder||0))/100);
  const furyMult = D.crit.spellMult + 0.2*(t.elefury||0)*(D.crit.spellMult-1);
  const overload = [0,0.10,0.20,0.30][t.overload||0]*0.5;
  return {hit:(lb.avg + lb.coef*c.spellDamage)*(1+0.01*(t.concussion||0))*hitP*(1 + sCrit*(furyMult-1))*(1+overload),
    cost: lb.mana*(1-0.02*(t.convection||0))*(t.elefocus ? 1 - 0.1/1.1 : 1), cast: Math.max(D.gcd, lb.cast - [0,0.17,0.33,0.5][t.alacrity||0])};
}
function solo(c, D, o){
  const L = c.level || 60, LV = D.LV, P = D.solo;
  if(!LV) return null;
  const diff = o.mobDiff || 0;
  const Lm = Math.max(1, Math.min(LV.mobHP.length, L + diff));
  const mobHP = LV.mobHP[Lm-1], mobRaw = LV.mobDPS[Lm-1];
  const mit = c.armor/(c.armor + 400 + 85*Lm);
  const dodge = P.dodgeBase + c.agi*c.perAgi;
  const landed = Math.max(0, 1 - P.mobMiss/100 - dodge/100);
  const taken = mobRaw*(1-mit)*landed;
  const hitRate = landed/P.mobSwing;
  const spellHit = 1 - Math.max(0, mobTable(D, diff).spellMiss - c.hit)/100;
  let ls = {dps:0, mana:0, rank:0};
  const lsr = o.lightningShield === false ? null : lvlRow(D.ls.ranks, L);
  if(lsr){ const rate = hitRate/(1 + hitRate*D.ls.icd); ls = {dps:rate*(lsr[1] + D.ls.coef*c.spellDamage)*spellHit, mana:rate*lsr[2]/D.ls.charges, rank:D.ls.ranks.indexOf(lsr)+1, per:lsr[1]}; }
  const meleeBest = shock => { let best = null; ['rockbiter','flametongue','windfury'].forEach(im => { const d = damage(c, D, {mobDiff:diff, front:true, imbue:im, shock}); if(d.imbue !== im) return; if(!best || d.dps > best.dps) best = d; }); return best || damage(c, D, {mobDiff:diff, front:true, imbue:'none', shock}); };
  const HW = healSpells(c, D, {}).HW;
  const bolt = boltStats(c, D, diff);
  const regenIdle = c.mp5/5 + c.spiritRegen, regenCast = c.mp5/5 + c.mindful*c.spiritRegen;
  const dr = lvlRow(D.drinks, L, o.mageWater), fr = lvlRow(D.food, L, o.mageWater);
  const dRate = dr[1]/dr[2] + regenIdle, fRate = fr[1]/fr[2];
  const travel = o.travel !== undefined ? o.travel : P.travel;
  const run = (key, name, openBolts, shock, boltOnly) => {
    let time = 0, mana = 0, inMelee = 0, casting = false, imbue = null, hp = mobHP, meleeDPS = 0;
    if(boltOnly){
      if(!bolt) return null;
      const dps = bolt.hit/bolt.cast;
      const pre = Math.min(hp/dps, bolt.cast + P.approach);
      hp -= dps*pre; time = pre;
      if(hp > 0){ const tm = hp/(dps + ls.dps); time += tm; inMelee = tm; mana += ls.mana*tm; }
      mana += bolt.cost/bolt.cast*time; casting = true;
    } else {
      const d = meleeBest(shock ? 'earth' : 'none'); imbue = d.imbue; meleeDPS = d.dps;
      if(openBolts){ if(!bolt) return null; const n = 1 + Math.floor(P.approach/bolt.cast); hp -= n*bolt.hit; time += n*bolt.cast; mana += n*bolt.cost; casting = true; }
      if(hp > 0){ const dps = d.dps + ls.dps; const tm = hp/dps; time += tm; inMelee = tm; mana += (d.manaPerSec + ls.mana)*tm; if(d.manaPerSec > 0) casting = true; }
    }
    let hpLost = taken*inMelee, heals = 0, unsafe = null;
    if(hpLost > 0.7*c.hp){
      const net = HW.base - taken*HW.cast;
      if(net <= 0) unsafe = 'the mob out-damages your Healing Wave';
      else { heals = Math.ceil((hpLost - 0.7*c.hp)/net); time += heals*HW.cast; mana += heals*HW.mana; hpLost += heals*(taken*HW.cast - HW.base); casting = true; }
    }
    mana -= (casting ? regenCast : regenIdle)*time;
    if(!unsafe && mana > c.mana) unsafe = 'you run out of mana before it dies';
    const travelRegen = casting ? regenCast*Math.min(5, travel) + regenIdle*Math.max(0, travel-5) : regenIdle*travel;
    const mNeed = Math.max(0, mana - travelRegen), hNeed = Math.max(0, hpLost);
    let rest = Infinity, topUp = 0;
    for(let i = 0; i <= 40; i++){
      const x = hNeed*i/40, n = x/HW.base;
      const r = Math.max((mNeed + n*HW.mana)/dRate, (hNeed - x)/fRate) + n*HW.cast;
      if(r < rest){ rest = r; topUp = x; }
    }
    const spk = time + travel + rest;
    return {key, name, imbue, kill:time, mana:Math.max(0, mana), hpLost, heals, rest, topUp, spk, perHour:unsafe ? 0 : 3600/spk, fightShare:time/spk, unsafe, meleeDPS};
  };
  const styles = [
    run('melee', 'Melee', false, false, false),
    L >= 4 ? run('shock', 'Melee and Earth Shock', false, true, false) : null,
    run('opener', 'Bolt pull, then melee'+(L >= 4 ? ' and Earth Shock' : ''), true, L >= 4, false),
    run('bolt', 'Lightning Bolt only', false, false, true)
  ].filter(Boolean);
  const best = styles.filter(s => !s.unsafe).sort((a,b) => b.perHour - a.perHour)[0] || styles[0];
  return {styles, best, mob:{level:Lm, hp:mobHP, dps:mobRaw, taken, mitigation:mit, landed}, ls, drink:dr, food:fr, regenIdle};
}

// Sensible fight defaults for a level: one elite hitting the tank, group damage scaled the same way.
function levelDefaults(D, L){
  const LV = D.LV; if(!LV) return {dtps:300, aoe:500, tankHP:6500, dpsHP:3800};
  const i = Math.max(0, Math.min(59, L-1));
  const r = LV.eliteDPS[i] / LV.eliteDPS[59];
  const hpNaked = l => LV.hp[l] + 20 + 10*Math.max(0, LV.sta[l]-20);
  const hr = hpNaked(i) / hpNaked(59);
  const round = (v, s) => Math.max(s, Math.round(v/s)*s);
  return {dtps: round(LV.eliteDPS[i], L < 20 ? 1 : 5), aoe: round(500*r, L < 20 ? 5 : 25), tankHP: round(6500*hr, 50), dpsHP: round(3800*hr, 50)};
}

function avg(a){ return a.length ? a.reduce((x,y)=>x+y,0)/a.length : 0; }
function sum(a){ return a.reduce((x,y)=>x+y,0); }

const api = {rng, talentsFromCode, talentsAt, rankVal, pickRank, lvlVal, lvlRow, solo, boltStats, sumGear, character, healSpells, capacity, potionMana, dungeonFight, runScenario, maxDTPS, damage, boltDPS, casterFight, levelDefaults};
if(typeof module !== 'undefined' && module.exports) module.exports = api; else root.Engine = api;
})(typeof window !== 'undefined' ? window : (typeof self !== 'undefined' ? self : this));
