// Talent optimizer: iterated local search over legal 51-point builds, scored with the sim engine.
const E = require('../src/engine.js');
const {DATA, TREE_ORDER} = require('../src/data.js');
const {ITEMS, SETS, PRESETS} = require('../src/items.js');
const META = require('./talents_meta.json');
const T = Object.fromEntries(META.map(t => [t.id, t]));
const IDS = META.map(t => t.id);

const presetKey = process.argv[2] || 'resto_timesaver';
const g = E.sumGear(PRESETS[presetKey].gear, ITEMS, SETS);
const CAP = {horizon:300, mix:{HW:0.7, CH:0.3}, chainEff:0.8, healEff:0.85, hstTargets:3, hitsPerSec:0.1, potions:true, tablet:false};
const char = t => E.character({gearStats:g.s, mh:g.mh, oh:g.oh, talents:t, buffs:{motw:true, ai:true}}, DATA);
const H = t => E.capacity(char(t), DATA, CAP).total;
const Dm = t => E.damage(char(t), DATA, {mobLevel:60, front:true, imbue:'windfury', shock:'none'}).dps;

function legal(t){
  let total = 0; const rowPts = {ele:[0,0,0,0,0,0,0,0], enh:[0,0,0,0,0,0,0,0], res:[0,0,0,0,0,0,0,0]};
  for(const id in t){ const n = t[id]; if(!n) continue; const m = T[id]; if(n > m.max || n < 0) return false; total += n; rowPts[m.tree][m.r] += n; }
  if(total > 51) return false;
  for(const id in t){ const n = t[id]; if(!n) continue; const m = T[id];
    let below = 0; for(let r = 1; r < m.r; r++) below += rowPts[m.tree][r];
    if(below < 5*(m.r-1)) return false;
    if(m.req && (t[m.req]||0) < T[m.req].max) return false;
  }
  return total === 51;
}
const code = t => ['ele','enh','res'].map(tr => TREE_ORDER[tr].map(id => t[id]||0).join('').replace(/0+$/,'')).join('-').replace(/-+$/,'');
const split = t => { const s = {ele:0,enh:0,res:0}; for(const id in t) s[T[id].tree] += t[id]; return s.ele+'/'+s.enh+'/'+s.res; };
let seed = 12345; const rnd = () => { seed ^= seed<<13; seed>>>=0; seed ^= seed>>>17; seed ^= seed<<5; seed>>>=0; return seed/4294967296; };

function randomLegal(){
  // Fill points one at a time, in row order, picking random legal talents.
  for(let tries = 0; tries < 200; tries++){
    const t = {}; let ok = true;
    for(let p = 0; p < 51; p++){
      const opts = IDS.filter(id => { const c = Object.assign({}, t); c[id] = (c[id]||0)+1; return partialLegal(c); });
      if(!opts.length){ ok = false; break; }
      const id = opts[Math.floor(rnd()*opts.length)]; t[id] = (t[id]||0)+1;
    }
    if(ok && legal(t)) return t;
  }
  return null;
}
function partialLegal(t){
  let total = 0; const rowPts = {ele:[0,0,0,0,0,0,0,0], enh:[0,0,0,0,0,0,0,0], res:[0,0,0,0,0,0,0,0]};
  for(const id in t){ const n = t[id]; const m = T[id]; if(n > m.max) return false; total += n; rowPts[m.tree][m.r] += n; }
  if(total > 51) return false;
  for(const id in t){ const n = t[id]; if(!n) continue; const m = T[id]; let below = 0; for(let r = 1; r < m.r; r++) below += rowPts[m.tree][r]; if(below < 5*(m.r-1)) return false; if(m.req && (t[m.req]||0) < T[m.req].max) return false; }
  return true;
}

function localSearch(start, score){
  let t = Object.assign({}, start), best = score(t), improved = true;
  while(improved){
    improved = false;
    // move k points from a to b (k = 1..3)
    outer: for(const k of [1,2,3,5]){
      for(const a of IDS){ if((t[a]||0) < k) continue;
        for(const b of IDS){ if(a === b) continue;
          const c = Object.assign({}, t); c[a] -= k; if(!c[a]) delete c[a]; c[b] = (c[b]||0)+k;
          if(!legal(c)) continue;
          const s = score(c);
          if(s > best + 1e-9){ t = c; best = s; improved = true; break outer; }
        }
      }
    }
    if(!improved){ // try swaps of two pairs to escape gating plateaus
      for(let i = 0; i < 400 && !improved; i++){
        const c = Object.assign({}, t);
        for(let j = 0; j < 3; j++){ const a = IDS[Math.floor(rnd()*IDS.length)], b = IDS[Math.floor(rnd()*IDS.length)]; if((c[a]||0) > 0){ c[a]--; if(!c[a]) delete c[a]; c[b] = (c[b]||0)+1; } }
        if(legal(c)){ const s = score(c); if(s > best + 1e-9){ t = c; best = s; improved = true; } }
      }
    }
  }
  return {t, s:best};
}
function ils(score, starts, restarts){
  let best = null;
  const pool = starts.slice();
  for(let i = 0; i < restarts; i++){ const r = randomLegal(); if(r) pool.push(r); }
  for(const s0 of pool){ const r = localSearch(s0, score); if(!best || r.s > best.s) best = r; }
  return best;
}

const KNOWN = {
  pure:E.talentsFromCode('-055-5530003315513151', TREE_ORDER),
  hybrid:E.talentsFromCode('-055030310021-5530000115513101', TREE_ORDER),
  leprestorePvE:E.talentsFromCode('-035-5535003315513151', TREE_ORDER),
  rankedboost:E.talentsFromCode('-05-5530533315513151', TREE_ORDER),
  kryhavoc:E.talentsFromCode('-0052303130012122-05300233105031', TREE_ORDER),
  mq2229:E.talentsFromCode('-055030310021-553000011551310', TREE_ORDER)
};
for(const k in KNOWN) if(!legal(KNOWN[k])) console.error('illegal known build', k, split(KNOWN[k]), Object.values(KNOWN[k]).reduce((a,b)=>a+b,0));

const out = {preset:presetKey, known:{}, healOpt:null, frontier:[]};
for(const k in KNOWN) if(legal(KNOWN[k])) out.known[k] = {split:split(KNOWN[k]), code:code(KNOWN[k]), H:H(KNOWN[k]), D:Dm(KNOWN[k])};
const healBest = ils(H, Object.values(KNOWN).filter(legal), 25);
out.healOpt = {split:split(healBest.t), code:code(healBest.t), H:healBest.s, D:Dm(healBest.t), t:healBest.t};
for(const tau of [0.98, 0.96, 0.94, 0.92, 0.90, 0.88, 0.85]){
  const target = tau*healBest.s;
  const sc = t => { const h = H(t); return Dm(t) - 50*Math.max(0, target - h)/1000; };
  const r = ils(sc, Object.values(KNOWN).filter(legal).concat([healBest.t]), 15);
  out.frontier.push({tau, split:split(r.t), code:code(r.t), H:H(r.t), D:Dm(r.t), t:r.t});
}
console.log(JSON.stringify(out, null, 1));
