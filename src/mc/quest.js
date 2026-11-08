// Questing for any class: the engine gives damage per second and mana use against a normal mob of
// the chosen level; this file adds the kill time, the damage you take, walking and resting.
// Needs CLASSDATA, LEVELS, MCRequest, and DATA.drinks / DATA.food from data.js.
(function(root){
'use strict';
const RANGED = {hunter:1, mage:1, warlock:1, priest:1};
const RANGED_SPEC = {druid:{balance:1, restoration:1}, shaman:{ele:1}};
const PET_TANKS = {hunter:10, warlock:10};      // pet takes the hits from this level (Voidwalker at 10; hunters tame at 10)
const CAN_PARRY = {warrior:1, paladin:1, rogue:1, hunter:1};
const APPROACH = 4, MOB_MISS = 5, MOB_SWING = 2.0;
function row(table, L, mage){ let r = null; for(const x of table) if(x[0] <= L && (!x[4] || mage)) r = x; return r; }

// ctx: request options for MCRequest.buildRequest plus {mobDiff, travel, mageWater}
// run(req) -> MCRequest.summarize(result)
function questSim(ctx, run){
  const cd = CLASSDATA[ctx.cls], L = ctx.level, i = L - 1;
  const Lm = Math.max(1, Math.min(63, L + (ctx.mobDiff||0)));
  const mobHP = LEVELS.mobHP[Lm-1], mobDPS = LEVELS.mobDPS[Lm-1];
  // Healers quest with a damage rotation (their own talents); classdata lists it as the 'quest' role
  const sp = cd.specs[ctx.spec];
  const role = sp.roleSpec && sp.roleSpec.quest ? 'quest' : ctx.role;
  const base = Object.assign({}, ctx, {role, targetLevel: Lm, iterations: ctx.iterations || 200});
  // First pass at a guessed length, second at the kill time it implies (one pass when the length is given)
  let s = run(MCRequest.buildRequest(Object.assign({}, base, {duration: ctx.fixedDuration || 20})));
  if(ctx.fixedDuration){
    if(!s.ok) return {ok: false, why: s.why};
  }
  if(!s.ok) return {ok: false, why: s.why};
  let kill = s.dps > 0 ? mobHP / s.dps : Infinity;
  if(isFinite(kill) && !ctx.fixedDuration){
    const s2 = run(MCRequest.buildRequest(Object.assign({}, base, {duration: Math.max(4, Math.min(120, Math.round(kill)))})));
    if(s2.ok && s2.dps > 0){ s = s2; kill = mobHP / s.dps; }
  }
  if(!isFinite(kill)) return {ok: false, why: 'no damage at this level'};
  // Your stats, as the character sheet the request carried
  const g = MCRequest.gearStats(ctx.gear || {}, ITEMS_ALL);
  const sh = MCRequest.sheet(cd, ctx.race, L, g);
  const [str, agi, sta, int, spi] = sh.attributes;
  const armor = (g.armor||0) + (g.bonusArmor||0) + 2*agi;
  const mit = armor/(armor + 400 + 85*Lm);
  const dodge = (cd.baseDodge[i]||0) + agi*(cd.dodgePerAgi[i]||0) + (g.dodgeRating||0)/12;
  const parry = CAN_PARRY[ctx.cls] ? 5 : 0;
  const landed = Math.max(0, 1 - (MOB_MISS + dodge + parry)/100);
  const petTank = PET_TANKS[ctx.cls] && L >= PET_TANKS[ctx.cls];
  const ranged = RANGED[ctx.cls] || (RANGED_SPEC[ctx.cls]||{})[ctx.spec];
  const inMelee = petTank ? 0 : Math.max(0, kill - (ranged ? APPROACH : 0));
  const taken = mobDPS*(1 - mit)*landed;
  const hpLost = taken*inMelee;
  const usesMana = cd.baseMana[i] > 0;
  const manaUsed = usesMana ? Math.max(0, s.manaSpent - s.manaGained) : 0;
  // Resting: walk to the next mob, then eat and drink together for what is still missing
  const regen = usesMana ? 6.25 + spi/8 : 0;          // wowsims Forever rule, every class, outside the 5-second rule
  const travel = ctx.travel != null ? ctx.travel : 10;
  const manaNeed = Math.max(0, manaUsed - regen*Math.max(0, travel - 5));
  const dr = row(DATA.drinks, L, ctx.mageWater), fr = row(DATA.food, L, ctx.mageWater);
  const restMana = usesMana && manaNeed > 0 ? manaNeed/(dr[1]/dr[2] + regen) : 0;
  const restHP = hpLost > 0 ? hpLost/(fr[1]/fr[2]) : 0;
  const rest = Math.max(restMana, restHP);
  const spk = kill + travel + rest;
  const risky = hpLost > 0.85*sh.health ? 'you lose '+Math.round(hpLost)+' of '+sh.health+' health per kill' : (usesMana && manaUsed > sh.mana ? 'you run out of mana before it dies' : null);
  return {ok: true, mob: {level: Lm, hp: mobHP, dps: mobDPS}, dps: s.dps, ownDps: s.ownDps, petDps: s.petDps, kill, manaUsed, mana: sh.mana,
    hpLost, health: sh.health, taken: petTank ? 0 : taken, petTank: !!petTank, ranged: !!ranged, rest, restFor: restMana >= restHP ? 'mana' : 'health',
    travel, spk, perHour: 3600/spk, fightShare: kill/spk, drink: usesMana ? dr[3] : null, food: fr[3], risky};
}
const api = {questSim};
if(typeof module !== 'undefined' && module.exports) module.exports = api; else root.MCQuest = api;
})(typeof window !== 'undefined' ? window : (typeof self !== 'undefined' ? self : this));
