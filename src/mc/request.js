// Builds MythicSim engine requests for any class, spec, race and level.
// Needs CLASSDATA, PRESETS_APL, SPEC_TEMPLATES (classdata.js), ITEMS_ALL (items.js) and LEVELS (levels.js, mob tables).
(function(root){
'use strict';
const SLOT_ORDER = ['head','neck','shoulder','back','chest','wrist','hands','waist','legs','feet','finger1','finger2','trinket1','trinket2','mainhand','offhand','ranged'];
const ATTR = ['str','agi','sta','int','spi'];

function talentsAt(route, points){
  const t = {}; let left = Math.max(0, Math.min(51, points));
  for(const [id, n] of route){ if(left <= 0) break; const k = Math.min(n, left); t[id] = (t[id]||0) + k; left -= k; }
  return t;
}
function talentCode(cd, talents){
  return Object.keys(cd.codeOrder).map(tr => cd.codeOrder[tr].map(id => talents[id]||0).join('').replace(/0+$/,'')).join('-');
}
function gearStats(gear, items){
  const s = {};
  for(const slot in gear){ const it = items[gear[slot]]; if(!it) continue; for(const k in it.s) s[k] = (s[k]||0) + it.s[k]; }
  return s;
}
// What the in-game character sheet would show: the engine solves base health, mana and crit slopes from it.
function sheet(cd, race, level, g){
  const i = level - 1, B = cd.races[race].base[i];
  const attrs = ATTR.map((k, j) => B[j] + (g[k]||0));
  const [str, agi, sta, int] = attrs;
  const health = cd.baseHP[i] + Math.min(sta, 20) + cd.hpPerSta[i]*Math.max(0, sta - 20);
  const mana = cd.baseMana[i] > 0 ? cd.baseMana[i] + Math.min(int, 20) + cd.manaPerInt[i]*Math.max(0, int - 20) : 0;
  const critR = (g.critRating||0)/14;
  const meleeCrit = cd.baseMeleeCrit[i] + agi*cd.critPerAgi[i] + critR;
  const spellCrit = cd.baseMana[i] > 0 ? cd.baseSpellCrit[i] + int*cd.critPerInt[i] + critR : 0;
  const r2 = v => Math.round(v*100)/100;
  return {level, base: B.slice(), attributes: attrs, health: Math.round(health), mana: Math.round(mana), meleeCrit: r2(meleeCrit), spellCrit: [0,0,0,0,0,0].map(() => r2(spellCrit))};
}
function ammoFor(level, rangedItem){
  const gun = rangedItem && /Gun/.test(rangedItem.wt||'');
  if(level >= 52) return gun ? 'ThoriumShells' : 'ThoriumHeadedArrow';
  if(level >= 40) return gun ? 'AccurateSlugs' : 'JaggedArrow';
  if(level >= 25) return gun ? 'SolidShot' : 'RazorArrow';
  return 'AmmoNone';
}
// Class options that depend on level (pets, armors, imbues and poisons come at set levels).
function optionsFor(cls, engineSpec, level, gear, items, want){
  const t = JSON.parse(JSON.stringify(SPEC_TEMPLATES[engineSpec]));
  const block = t.options; const o = block.options || (block.options = {}); const co = o.classOptions || (o.classOptions = {});
  const cons = {};
  if(cls === 'hunter'){
    co.ammo = ammoFor(level, items[gear.ranged]); co.petType = level >= 10 ? (want.petType || 'Cat') : 'PetNone';
    co.petUptime = 1; co.quiverBonus = 'QuiverNone'; co.petAttackSpeed = co.petAttackSpeed || 'Two';
  }
  if(cls === 'warlock'){
    co.summon = want.summon || (level >= 20 ? 'Succubus' : level >= 10 ? 'Voidwalker' : 'Imp');
    co.armor = level >= 20 ? 'DemonArmor' : 'NoArmor';
    co.curseOptions = 'Agony';
  }
  if(cls === 'mage') co.defaultMageArmor = 'MageArmorFrostArmor';
  if(cls === 'priest' && engineSpec === 'dpsPriest'){ co.armor = level >= 12 ? 'InnerFire' : 'NoArmor'; co.useShadowfiend = level >= 40; }
  // The healer follows the same Shadowfiend rule as the DPS priest. The engine gave every healer the Shadowfiend
  // (classes/priest/prepare.rs "the healer always has the Shadowfiend"); engine patch 0007 lets the option turn it off below 60.
  // The level 40 is this builder's own rule, not a verified Forever learn level: client 401977 has spell level 1
  // and no trainer level, and wowsims-forever (125e534) has no Shadowfiend at all.
  if(cls === 'priest' && engineSpec === 'healerPriest'){ co.armor = level >= 12 ? 'InnerFire' : 'NoArmor'; co.useShadowfiend = level >= 40; }
  if(engineSpec === 'enhancementShaman'){
    co.imbueMh = want.imbue || (level >= 30 ? 'WindfuryWeapon' : level >= 10 ? 'FlametongueWeapon' : 'RockbiterWeapon');
    delete o.imbueOh; delete o.syncType;
  }
  return {t, options: block, consumables: cons};
}
function target(level, opts){
  const Lm = Math.max(1, Math.min(63, level));
  const stats = new Array(41).fill(0);
  stats[30] = LEVELS.mobArmor[Lm-1];
  stats[32] = opts.boss ? Math.round(LEVELS.eliteHP[Math.min(59, Lm-1)]*20) : LEVELS.mobHP[Lm-1];
  stats[17] = 0;
  const t = {id: 31146, name: 'Level '+Lm, level: Lm, mobType: opts.mobType || 'MobTypeUnknown', stats, minBaseDamage: 0, swingSpeed: 2, damageSpread: 0.3333, canCrush: false, parryHaste: !!opts.boss};
  if(opts.tank){
    // A tank's target swings at it. The engine rolls a swing as minBaseDamage * (1 + damageSpread * roll) with no attack power
    // (stats[17] = 0), so the average swing is minBaseDamage * (1 + spread/2). The average is the client's creature auto attack
    // dps for the target's level times the 2.0 s swing (ExpectedStat CreatureAutoAttackDps, LEVELS.mobDPS), or the elite
    // estimate for a dungeon mob (LEVELS.eliteDPS: the client row times the cmangos elite median ratio, an estimate).
    // canCrush as the engine's tank fixtures set it; its attack table (prepare/attack.rs) crushes only from 3 levels up (15%).
    const dps = (opts.elite || opts.boss ? LEVELS.eliteDPS : LEVELS.mobDPS)[Lm-1];
    t.minBaseDamage = Math.round(dps * t.swingSpeed / (1 + t.damageSpread/2) * 100) / 100;
    t.canCrush = true;
  }
  return t;
}
// The engine specs that tank: the engine prepares a tank only when the raid names it in raid.tanks (proto.UnitReference)
// and the target swings at it (tests/classes/warrior/prepare.rs, a_tanking_warrior_is_prepared_with_the_target_swing).
const TANK_SPECS = new Set(['protectionWarrior', 'protectionPaladin', 'feralBearDruid']);
// Builders and fillers a preset leaves out before its own is learned. Each entry: the preset, what makes its own
// filler known (a talent in the route, or a level), and the spells appended to the end of the priority list
// (the engine casts a named spell at the highest rank the character knows).
//  - Arcane (mage/dps/arcane) fills with Arcane Blast, rank 1 at level 20 (engine data/spells.jsonl 400574); below 20
//    it cast nothing. Arcane Missiles (5143, level 8) then Frostbolt (116, level 4) then Fireball (133, level 1).
//  - Assassination (rogue/dps/forever_mutilate) builds only with Mutilate, a 31 point talent; before it, Backstab (53,
//    level 4, main hand dagger, from behind as the template stands) then Sinister Strike (1752, level 1).
//  - Subtlety (rogue/dps/forever_hemorrhage) builds with Hemorrhage, a talent; before it the same Backstab, Sinister Strike.
//  - Frost (mage/dps/frost) fills with Frostbolt, rank 1 at level 4; below it Fireball (133, level 1).
//  - Shadow (priest/dps/shadow) fills with Mind Flay, a talent (15407, level 20); before it Smite (585, level 1).
const LOW_FILLERS = {
  'mage/dps/arcane': {knownFrom: {level: 20}, spells: [5143, 116, 133]},
  'mage/dps/frost': {knownFrom: {level: 4}, spells: [133]},
  'priest/dps/shadow': {knownFrom: {talent: 'mind_flay'}, spells: [585]},
  'rogue/dps/forever_mutilate': {knownFrom: {talent: 'mutilate'}, spells: [53, 1752]},
  'rogue/dps/forever_hemorrhage': {knownFrom: {talent: 'hemorrhage'}, spells: [53, 1752]}
};
function addLowFillers(rotation, preset, level, talents){
  const f = LOW_FILLERS[preset]; if(!f) return;
  const known = f.knownFrom.level ? level >= f.knownFrom.level : (talents[f.knownFrom.talent]||0) > 0;
  if(known || !rotation.priorityList) return;
  for(const id of f.spells) rotation.priorityList.push({action: {castSpell: {spellId: {spellId: id}}}});
}
// o: {cls, race, spec, level, talents (object) or route, gear {slot: id}, targetLevel, boss, elite (a tank's target swings as an elite), duration, iterations, seed, role, petType, summon, imbue}
function buildRequest(o){
  const cd = CLASSDATA[o.cls], sp = cd.specs[o.spec];
  const roleSpec = o.role && sp.roleSpec && sp.roleSpec[o.role];
  const engineSpec = roleSpec ? roleSpec.engineSpec : sp.engineSpec;
  const preset = roleSpec ? roleSpec.preset : sp.preset;
  const talents = o.talents || talentsAt(o.route || sp.routes[0].route, o.level - 9);
  const gear = {}; for(const k in (o.gear||{})) if(ITEMS_ALL[o.gear[k]] && !o.skipItems?.has?.(o.gear[k])) gear[k] = o.gear[k];
  const g = gearStats(gear, ITEMS_ALL);
  const {t, options} = optionsFor(o.cls, engineSpec, o.level, gear, ITEMS_ALL, o);
  const player = {
    name: o.cls, class: cd.engineClass, race: cd.races[o.race].engine, level: o.level,
    talentsString: talentCode(cd, talents),
    equipment: {items: SLOT_ORDER.map(k => gear[k] ? {id: +gear[k]} : {})},
    characterSheet: sheet(cd, o.race, o.level, g),
    rotation: JSON.parse(JSON.stringify(PRESETS_APL[preset])),
    consumables: {}, buffs: {},
    distanceFromTarget: t.distanceFromTarget, reactionTimeMs: t.reactionTimeMs || 100
  };
  if(t.inFrontOfTarget) player.inFrontOfTarget = true;
  if(t.channelClipDelayMs) player.channelClipDelayMs = t.channelClipDelayMs;
  player[engineSpec] = options;
  addLowFillers(player.rotation, preset, o.level, talents);
  const tl = o.targetLevel || o.level;
  const tank = TANK_SPECS.has(engineSpec);
  const raid = {buffs: {}, debuffs: {}, parties: [{buffs: {}, players: [player]}]};
  if(tank) raid.tanks = [{index: 0, type: 'Player'}];
  return {
    encounter: {duration: o.duration || 60, durationVariation: 0, executeProportion20: 0.2, executeProportion25: 0.25, executeProportion35: 0.35, executeProportion45: 0.45, executeProportion90: 0.9, noHitSuppression: true,
      targets: [target(tl, {boss: o.boss, elite: o.elite, tank})]},
    raid,
    simOptions: {iterations: o.iterations || 200, randomSeed: String(o.seed || 42)}
  };
}
// Headline numbers from an engine report
function summarize(res){
  if(!res || !res.ok) return {ok: false, why: res ? (res.stage+': '+res.reason) : 'no result'};
  const p = res.report.result.raidMetrics.parties[0].players[0];
  const petDps = (p.pets||[]).reduce((a, x) => a + (x.dps && x.dps.avg || 0), 0);
  let manaSpent = 0, manaGained = 0;
  (p.resources||[]).forEach(r => { if(r.type === 'ResourceTypeMana'){ const v = r.actualGain != null ? r.actualGain : (r.gain||0); if(v < 0) manaSpent -= v; else manaGained += v; } });
  const its = res.report.result.iterationsDone || 1;
  const dps = p.dps && p.dps.avg || 0;
  // A player's dps already counts its pets' damage
  return {ok: true, dps, ownDps: dps - petDps, petDps, total: dps, hps: p.hps && p.hps.avg || 0, dtps: p.dtps && p.dtps.avg || 0,
    oom: p.secondsOomAvg || 0, manaSpent: manaSpent/its, manaGained: manaGained/its, duration: res.report.result.avgIterationDuration};
}
const api = {SLOT_ORDER, TANK_SPECS, LOW_FILLERS, talentsAt, talentCode, gearStats, sheet, buildRequest, summarize, ammoFor};
if(typeof module !== 'undefined' && module.exports) module.exports = api; else root.MCRequest = api;
})(typeof window !== 'undefined' ? window : (typeof self !== 'undefined' ? self : this));
