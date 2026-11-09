// Craft Profits pricing checks against a fixed price table, so the numbers do not move with new scans.
const { parsePriceTable, makeEngine, coins } = require('../src/crafts/core.js');
const D = require('../data/crafts.json');
const E = makeEngine(D);
// Hand-written table in AHledger's format: id:median:min:qty:med7:med30:low30:high30:sold10
const PT = parsePriceTable([
  'AHL1|forever/rppvp/alliance/eu|1794052222|4',
  '2996:80:76:300:80:80:76:90:',    // Bolt of Linen Cloth
  '2318:30:30:2000:30:30:30:40:',   // Light Leather
  '783:115:115:40:115:115:100:130:', // Light Hide
  '4238:300:290:90:300:300:290:320:', // Linen Bag
].join('\n'));
let fails = 0;
const eq = (name, got, want) => { const ok = Math.abs(got - want) < 0.51; if (!ok) fails++; console.log((ok ? 'ok   ' : 'FAIL ') + name + ': ' + got + (ok ? '' : ' want ' + want)); };
const find = (n) => E.recipes.find((r) => r.name === n);
// Linen Bag: 3 Bolts of Linen (AH 80c) + 3 Coarse Thread (vendor 10c) = 2s 70c; sells 3s less 5% = 2s 85c.
let ctx = E.context(PT, { basis: 'med', sellTo: 'ah', maxSkill: 300, trim: false, disc: 0 });
let e = ctx.evalRecipe(find('Linen Bag'));
eq('Linen Bag cost', e.c.cost, 270); eq('Linen Bag profit', e.profit, 15);
// Light Leather Pants to a vendor: 10 Light Leather 30c + Cured Light Hide (Light Hide 1s 15c + Salt 50c) + Fine Thread 1s = 5s 65c; vendor pays 5s 99c.
ctx = E.context(PT, { basis: 'med', sellTo: 'vendor', maxSkill: 300, trim: false, disc: 0 });
e = ctx.evalRecipe(find('Light Leather Pants'));
eq('Light Leather Pants cost', e.c.cost, 565); eq('Light Leather Pants vendor', e.vend, 599);
// With the 10% Honored discount Salt is 45c and Fine Thread 90c, as in the forum post: 5s 50c.
ctx = E.context(PT, { basis: 'med', sellTo: 'vendor', maxSkill: 300, trim: false, disc: 0.1 });
e = ctx.evalRecipe(find('Light Leather Pants'));
eq('Light Leather Pants cost at Honored', e.c.cost, 550); eq('Light Leather Pants profit at Honored', e.profit, 49);
// Coins formatting
const f = (c) => { const k = coins(c); return (k.neg ? '-' : '') + k.parts.map(([n, u]) => n + u).join(' '); };
const fo = (name, got, want) => { const ok = got === want; if (!ok) fails++; console.log((ok ? 'ok   ' : 'FAIL ') + name + ': ' + got + (ok ? '' : ' want ' + want)); };
fo('coins 12345', f(12345), '1g 23s 45c'); fo('coins -99', f(-99), '-99c'); fo('coins 10005', f(10005), '1g 5c');
process.exit(fails ? 1 : 0);
