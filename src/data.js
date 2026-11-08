// Shaman data for WoW Forever, levels 1-60 (per-level tables live in levels.js). Status: forever = client data or Blizzard text;
// sim = rule used by the wowsims Forever simulator; vanilla = Classic fallback, not confirmed for Forever.
const DATA = {
  version: 'Spell data: wowsims/forever commit 125e534 (client build 1.60.1.70862), checked Nov 8, 2026',
  base: {hp:1280, mana:1520, str:87, agi:51, sta:98, int:89, spi:99},
  ap: {base:100, perStr:2},
  ratings: {hit:10, crit:14},
  race: {hit:1},
  crit: {spellBase:2.3, meleeBase:1.7, perInt:0.0169, perAgi:0.0508, healMult:1.5, spellMult:1.5, meleeMult:2.0},
  regen: {spiritBase:6.25, spiritDiv:8},
  gcd: 1.5, totemGcd: 1.0,
  potion: {mana:1800, cd:120},
  buffs: {motw:{allStats:16}, ai:{int:31}},
  // Leveling tables. Buffs assume the caster is your level (you level together).
  motwByLevel: [[1,0],[10,3],[20,5],[30,8],[40,11],[50,14],[60,16]],
  aiByLevel: [[1,2],[14,7],[28,15],[42,22],[56,31]],
  potions: [[5,160],[14,320],[22,520],[31,800],[41,1200],[49,1800]],
  potionNames: {5:'Minor Mana Potion',14:'Lesser Mana Potion',22:'Mana Potion',31:'Greater Mana Potion',41:'Superior Mana Potion',49:'Major Mana Potion'},
  // [level, amount, seconds, name, conjured by a mage only]
  drinks: [[1,151,18,'Refreshing Spring Water'],[5,437,21,'Ice Cold Milk'],[15,835,24,'Melon Juice'],[25,1345,27,'Sweet Nectar'],[35,1915,30,'Moonberry Juice'],[45,2821,30,'Morning Glory Dew'],[55,4038,30,'Conjured Crystal Water',1]],
  food: [[1,59,18,'Tough Jerky'],[5,234,21,'Haunch of Meat'],[15,531,24,'Mutton Chop'],[25,841,27,'Wild Hog Shank'],[35,1338,30,'Cured Ham Steak'],[45,2065,30,'Roasted Quail'],[55,3058,30,'Conjured Cinnamon Roll',1]],
  ls: {ranks:[[8,13,45],[16,24,80],[24,40,125],[32,64,180],[40,96,240],[48,134,305],[56,178,370]], coef:0.267, charges:3, icd:3.5},
  solo: {approach:4, mobSwing:2.0, mobMiss:5, dodgeBase:1.7, travel:10, restAt:0.15},
  spells: {
    spread: 0.13,
    hw9:  {avg:1366, cast:3.0, mana:560, coef:0.857},
    hw10: {avg:1615, cast:3.0, mana:620, coef:0.857},
    lhw:  {avg:820, cast:1.5, mana:380, coef:0.429},
    ch:   {avg:506.5, cast:2.5, mana:405, coef:0.714, targets:3, falloff:0.5},
    riptide: {tick:161, ticks:5, every:3, coefTick:0.10, mana:230, cd:12, ticksCrit:true},
    hst: {tick:11, every:2, coefTick:0.022, mana:80},
    manaspring: {tick:10, every:2, mana:100},
    manatide: {tick:290, ticks:4, every:3, total:1160, cd:300, mana:60},
    watershield: {pct:0.02, icd:3.5},
    lightningbolt: {avg:361.4, cast:2.5, mana:220, coef:0.714},
    earthshock: {avg:531, coef:0.386, mana:450, cd:6},
    flameshock: {direct:292, coefDirect:0.214, dot:320, ticks:4, coefTick:0.10, mana:410, cd:6},
    stormstrike: {cd:6, manaPctBase:0.08}
  },
  imbue: {
    windfury: {chance:0.20, icd:1.5, attacks:2, ap:333},
    flametongue: {perSpeed:28.10, coef:0.10},
    rockbiter: {ap:653}
  },
  mob: {
    60: {miss:5, dodge:5, parry:5, glance:10, glanceDmg:0.95, critPen:0, spellMiss:4, armor:3566},
    63: {miss:8, dodge:6.5, parry:14, glance:40, glanceDmg:0.65, critPen:4.8, spellMiss:17, armor:3731}
  },
  // What each number rests on, shown in the Assumptions panel.
  sources: [
    ['Healing Wave rank 9: 1,275-1,457, 3.0 s, 560 mana, 0.857 coefficient','forever'],
    ['Healing Wave rank 10 (Tablet of Healing Wave X, a raid book): 1,508-1,722, 620 mana','forever'],
    ['Lesser Healing Wave rank 6: 775-865, 1.5 s, 380 mana, 0.429','forever'],
    ['Chain Heal rank 3: 473-540, 2.5 s, 405 mana, 0.714, 3 targets, each jump 50%','forever'],
    ['Riptide rank 3: 161 every 3 s for 15 s, 230 mana, 12 s cooldown, 0.10 per tick','forever'],
    ['Riptide ticks can crit','sim'],
    ['Healing Stream Totem rank 5: 11 every 2 s to the party; Mana Spring rank 4: 10 mana every 2 s','forever'],
    ['Mana Tide Totem rank 4: 290 mana every 3 s, 4 ticks, 5 min cooldown','forever'],
    ['Water Shield: 3 globes, 2% of max mana each, at most one every 3.5 s, on hits taken or any spell crit','forever'],
    ['Base stats, Dwarf Shaman 60: 1,520 mana, 87 Str, 51 Agi, 98 Sta, 89 Int, 99 Spi','forever'],
    ['10 hit rating = 1%, 14 crit rating = 1%, both count for melee and spells','forever'],
    ['Spell crit: 2.3% base + 1% per 59.2 Int; melee crit 1.7% base + 1% per 19.7 Agi','sim'],
    ['Mana: 15 per Int; health: 10 per Sta','vanilla'],
    ['Spirit regen 6.25 + Spirit/8 per second, stopped for 5 s after spending mana (Mindfulness keeps up to 50%)','sim'],
    ['Crits: heals and spells 1.5x, melee 2x','vanilla'],
    ['Attack power 100 + 2 per Str; weapon damage + AP/14 per second of weapon speed','vanilla'],
    ['Stormstrike: 150% normalized weapon damage, 6 s cooldown, 8% of base mana; next Earth Shock +20%','forever'],
    ['Windfury Weapon: 20% per hit, 1.5 s internal cooldown, 2 extra attacks at +333 AP','forever'],
    ['Melee vs level 60: 5% miss, 5% dodge, 5% parry from the front, 10% glancing at 95%','vanilla'],
    ['Melee vs level 63: 8% miss, 6.5% dodge, 14% parry, 40% glancing at 65%, crit -4.8%','vanilla'],
    ['Mark of the Wild at your level: +3 all stats at 10, +5 at 20, +8 at 30, +11 at 40, +14 at 50, +16 at 60 (rank 1 is armor only)','forever'],
    ['Arcane Intellect at your level: +2 Int from 1, +7 at 14, +15 at 28, +22 at 42, +31 at 56','forever'],
    ['Mana potions by level: Minor 160 (5), Lesser 320 (14), Mana Potion 520 (22), Greater 800 (31), Superior 1,200 (41), Major 1,800 (49), all 2 min cooldown','forever'],
    ['Base stats, spell ranks, mob health and mob damage for every level 1 to 60 from the Forever client tables','forever'],
    ['Lightning Shield: 3 charges, at most one every 3.5 s, 13 damage at 8 up to 178 at 56, 0.267 coefficient','forever'],
    ['Drink and food by level: 151 mana at 1 up to 2,821 at 45 (4,038 with Conjured Crystal Water at 55)','forever'],
    ['Shamans wear Leather until they learn Mail at 40 (Forever guides); the item lists follow that','forever'],
    ['Target armor: a normal mob of each level from the Forever client table (3,566 at 60, 3,731 at 63); your melee, Stormstrike, Windfury and Rockbiter hits lose armor / (armor + 400 + 85 x your level), at most 75%. No Sunder Armor or Faerie Fire','forever'],
    ['Armor reduces physical damage by armor / (armor + 400 + 85 x mob level); Shamans cannot parry; Agility gives 2 armor','vanilla'],
    ['Questing: the mob swings every 2 s and misses 5%; you dodge 1.7% plus Agility at the same rate as crit','est'],
    ['Questing: a Lightning Bolt pull gets about 4 s before the mob reaches you; 10 s walking between pulls by default; you eat and drink at the same time','est']
  ]
};

const TREE_ORDER = {
  ele:['convection','concussion','eledev','reverb','alacrity','callflame','elefocus','elewarding','trialfire','eyestorm','earthbound','reach','callthunder','overload','elefury','lmastery'],
  enh:['earthsgrasp','thundering','ancknow','guardian','mentaldex','implshield','eleweapons','shamfocus','anticipation','toughness','flurry','stormstrike','impghostwolf','spiritweapons','mentalquick','impstorm','maelstrom','farseer'],
  res:['ihw','tidalfocus','mindful','natgrace','totemicfocus','impreinc','anchealing','healfocus','watershield','tidalmastery','restotems','manatide','healingway','natswift','purification','riptide']
};
const MODELED = ['ihw','tidalfocus','mindful','watershield','tidalmastery','restotems','manatide','healingway','natswift','purification','riptide','totemicfocus','thundering','ancknow','mentaldex','eleweapons','shamfocus','flurry','stormstrike','mentalquick','convection','concussion','alacrity','callthunder','overload','elefury'];

if(typeof module !== 'undefined' && module.exports) module.exports = {DATA, TREE_ORDER, MODELED};
