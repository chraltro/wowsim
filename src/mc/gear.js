// Gear helpers for every class: who can wear what, and a typical set of gear for a level.
(function(root){
'use strict';
const SLOTS = ['head','neck','shoulder','back','chest','wrist','hands','waist','legs','feet','finger1','finger2','trinket1','trinket2','mainhand','offhand','ranged'];
// Rough stat values per spec style, only used to fill a typical set of gear for a level
const STYLE = {
  melee:  {str:2, agi:1.5, sta:0.5, ap:1, critRating:1.5, hitRating:1.5, armor:0.01},
  agile:  {agi:2, str:1, sta:0.5, ap:1, rangedAp:1, critRating:1.5, hitRating:1.5, armor:0.01},
  caster: {int:1, spi:0.6, sta:0.4, spellDamage:1.2, shadowDamage:0.8, fireDamage:0.8, frostDamage:0.8, critRating:1, hitRating:1, mp5:1.5},
  healer: {int:1, spi:0.8, sta:0.4, healing:1, mp5:2, critRating:0.8},
  tank:   {sta:1.5, armor:0.05, bonusArmor:0.1, defenseRating:1.5, dodgeRating:1.5, str:1, agi:1, blockValue:0.3}
};
const STYLE_OF = {
  warrior: {arms:'melee', fury:'melee', protection:'tank'}, paladin: {holy:'healer', protection:'tank', retribution:'melee'},
  hunter: {beast_mastery:'agile', marksmanship:'agile', survival:'agile'}, rogue: {assassination:'agile', combat:'agile', subtlety:'agile'},
  priest: {discipline:'healer', holy:'healer', shadow:'caster'}, shaman: {ele:'caster', enh:'melee', res:'healer'},
  mage: {arcane:'caster', fire:'caster', frost:'caster'}, warlock: {affliction:'caster', demonology:'caster', destruction:'caster'},
  druid: {balance:'caster', feral_combat:'agile', restoration:'healer'}
};
// Weapon types a spec's engine rotation needs, by hand. From the engine (MythicSim Forever, b3c5eb6):
// Mutilate needs a dagger in both hands (classes/rogue/prepare/export_specs.rs: "daggers": has_dagger(Main) && has_dagger(Off);
// talents/assassination.rs: "Every rank, and both hand strikes, require a Dagger in the beta client"); Backstab and Ambush need
// a main hand dagger (export.rs and export_specs.rs "main_hand_dagger"), and Hemorrhage takes its larger weapon share with one
// (talents/subtlety.rs, effect 4). Assassination's preset (rogue/dps/forever_mutilate) builds with Mutilate, Subtlety's
// (rogue/dps/forever_hemorrhage) opens with Ambush and builds with Hemorrhage; Combat's Sinister Strike takes any weapon.
// A hand with no wearable weapon of the type falls back to the best of any type.
const WEAPON_PREF = {
  rogue: {assassination: {mainhand: 'Dagger', offhand: 'Dagger'}, subtlety: {mainhand: 'Dagger'}}
};
function srcLevel(it){ let lv = null; (it.src||[]).forEach(s => { const m = s.lv ? String(s.lv).match(/\d+/) : null; if(m){ const v = +m[0]; if(lv === null || v < lv) lv = v; } }); return lv; }
// Level from which this class can wear the item in this slot, or null if never
function wearFrom(it, cls, slot){
  const u = it.ub && it.ub[cls]; if(!u) return null;
  const slots = Array.isArray(u[1]) ? u[1] : it.es;
  const want = slot.replace(/[12]$/, m => m);
  const ok = slots.some(s => s === want || s.replace(/[12]$/,'') === want.replace(/[12]$/,''));
  if(!ok) return null;
  let from = Math.max(u[0] || 0, it.rl || 1);
  if(slot === 'offhand' && it.w && !(it.wt||'').match(/Shield|Off-hand/)){ const oh = typeof u[1] === 'number' ? u[1] : (u[2] || null); if(oh) from = Math.max(from, oh); }
  return from;
}
// Level at which you can realistically get it (quest or dungeon level, else item level - 5 when it has no requirement)
function reachLevel(it){ const sl = srcLevel(it); return Math.max(it.rl || 1, sl || ((it.rl||0) <= 1 ? Math.max(1, (it.il||1) - 5) : 1)); }
function easySource(it){ return (it.src||[]).some(s => s.t === 'quest' || s.t === 'vendor' || s.t === 'crafted' || (s.t === 'dungeon' && (!s.p || s.p >= 5)) || (s.t === 'npc' && s.p >= 10)); }
function score(it, w){ let v = 0; for(const k in it.s) v += (w[k]||0)*it.s[k]; if(it.w) v += ((it.w.min+it.w.max)/2/it.w.speed)*(w.str ? 3 : w.agi ? 2.5 : 0.3)*(it.two ? 1.4 : 1); return v; }
// A typical set for the level: easy-to-get items you can wear, best by rough stat value
function typicalGear(items, cls, spec, level, opts){
  opts = opts || {};
  const w = STYLE[(STYLE_OF[cls]||{})[spec] || 'melee'];
  const pref = (WEAPON_PREF[cls]||{})[spec] || {};
  const gear = {}, used = new Set();
  const pick = (slot, type) => {
    if(type === undefined && pref[slot]) return pick(slot, pref[slot]) || pick(slot, null);
    let best = null, bv = -1;
    for(const id in items){
      const it = items[id];
      if(type && it.wt !== type) continue;
      if(used.has(id) && it.u) continue;
      const from = wearFrom(it, cls, slot); if(from === null || from > level) continue;
      if(reachLevel(it) > level) continue;
      if(opts.easyOnly !== false && !easySource(it)) continue;
      if(opts.inEngine && !opts.inEngine(id)) continue;
      const v = score(it, w) + (it.il||0)*0.01;
      if(v > bv){ bv = v; best = id; }
    }
    return best;
  };
  for(const slot of SLOTS){
    if(slot === 'offhand' && gear.mainhand && items[gear.mainhand].two) continue;
    const id = pick(slot); if(id){ gear[slot] = +id; used.add(id); }
  }
  // Compare a two-hander with one hand plus off hand by the same rough value
  if(gear.mainhand && items[gear.mainhand].two){
    const two = score(items[gear.mainhand], w);
    const saved = gear.mainhand; delete gear.mainhand;
    const oneIds = Object.keys(items).filter(id => !items[id].two);
    const sub = {}; for(const id of oneIds) sub[id] = items[id];
    const mh = (function(){ let best = null, bv = -1; for(const id in sub){ const it = sub[id]; const f = wearFrom(it, cls, 'mainhand'); if(f === null || f > level || reachLevel(it) > level || (opts.easyOnly !== false && !easySource(it)) || (opts.inEngine && !opts.inEngine(id))) continue; const v = score(it, w); if(v > bv){ bv = v; best = id; } } return best; })();
    const oh = mh ? pick('offhand') : null;
    const one = (mh ? score(items[mh], w) : 0) + (oh ? score(items[oh], w) : 0);
    if(mh && one > two){ gear.mainhand = +mh; if(oh) gear.offhand = +oh; } else gear.mainhand = saved;
  }
  return gear;
}
const api = {SLOTS, STYLE, STYLE_OF, WEAPON_PREF, wearFrom, reachLevel, srcLevel, typicalGear};
if(typeof module !== 'undefined' && module.exports) module.exports = api; else root.MCGear = api;
})(typeof window !== 'undefined' ? window : (typeof self !== 'undefined' ? self : this));
