// Craft Profits pricing checks against a fixed price table, so the numbers do not move with new scans.
const { parsePriceTable, makeEngine, coins, skillChance, speedBand, sellChance, expectedSale } = require('../src/crafts/core.js');
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
const fo = (name, got, want) => { const ok = got === want; if (!ok) fails++; console.log((ok ? 'ok   ' : 'FAIL ') + name + ': ' + got + (ok ? '' : ' want ' + want)); };
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
// Shopping plan for 3 pairs: the cured hides expand into Light Hide and Salt, crafted first.
const pl = ctx.plan(find('Light Leather Pants'), 3);
const got = (name, src) => { const b = pl.buy.find((x) => E.items.get(x.id)[0] === name && x.src === src); return b ? b.q : 0; };
eq('plan Light Leather', got('Light Leather', 'ah'), 30); eq('plan Light Hide', got('Light Hide', 'ah'), 3);
eq('plan Salt', got('Salt', 'vendor'), 3); eq('plan Fine Thread', got('Fine Thread', 'vendor'), 3);
eq('plan steps', pl.steps.length === 1 && pl.steps[0].r.name === 'Cured Light Hide' ? pl.steps[0].n : -1, 3);
eq('plan cost', pl.cost, 1650); eq('plan stock', pl.stock, 40); // 40 Light Hide listed, one per pair
// Skill-up chance: Light Leather Pants turn yellow and grey at the client's levels.
const llp = find('Light Leather Pants');
eq('chance while orange', skillChance(llp, llp.yellow - 1), 1); eq('chance at grey', skillChance(llp, llp.grey), 0);
// Expected sale: a miss chance of one half per listing, net 10s, vendor 2s.
// Sells within three tries 7 times in 8; 0.875 expired listings on average at a 1s 20c deposit each: 875 + 25 - 105.
const half = Math.log(2) / 2;
eq('expected sale', expectedSale(1000, 200, half), 795);
eq('sell chance', sellChance(half) * 100, 50);
fo('speed bands', [1.2, 0.5, 0.1, 0.01, null].map(speedBand).join(' '), 'fast steady slow barely ');
// A house that reports sales: 90 Linen Bags listed, 300 sold a day. The scan's own speed is used, and the bag sells fast.
const PT2 = parsePriceTable(['AHL1|forever/pvp/alliance/eu|1794052222|2', '2996:80:76:300:80:80:76:90:9000', '4238:300:290:90:300:300:290:320:3000'].join('\n'));
const c2 = E.context(PT2, { basis: 'med', sellTo: 'best', maxSkill: 300, trim: false, disc: 0 });
const bag = c2.evalRecipe(find('Linen Bag'));
const bagVendor = E.items.get(bag.r.res)[2];
fo('own speed', bag.band + ' ' + bag.ownTurn + ' ' + bag.via, 'fast true ah');
eq('expected Linen Bag', bag.exp, expectedSale(285, bagVendor, 300 / 90) - 270);
// The same bag selling slowly is better sold to a vendor: each expired listing loses 60% of its 2s vendor price.
const PT2b = parsePriceTable(['AHL1|forever/pvp/alliance/eu|1794052222|2', '2996:80:76:300:80:80:76:90:9000', '4238:300:290:90:300:300:290:320:300'].join('\n'));
fo('slow bag goes to the vendor', E.context(PT2b, { basis: 'med', sellTo: 'best', maxSkill: 300, trim: false, disc: 0 }).evalRecipe(find('Linen Bag')).via, 'vendor');
// Crates: Apprentice Fabrics takes 20 Bolts of Linen (16s here) or 2 Cured Light Hides (not listed). Green Apprentice crates give 10 favor.
const PT3 = parsePriceTable(['AHL1|forever/rppvp/alliance/eu|1794052222|2', '2996:80:76:300:80:80:76:90:', '248702:5000:4800:12:5000:5000:4800:5200:'].join('\n'));
const every = Object.fromEntries(D.profs.map((_, i) => [i, 300]));
const cr = E.context(PT3, { basis: 'med', sellTo: 'best', maxSkill: 300, trim: false, disc: 0, mine: every }).crates().find((c) => c.id === 248702);
eq('crate fill', cr.best.buy, 1600); eq('crate favor', cr.favor, 10); eq('cost per favor', cr.perFavor, 660);
// Spending plan: never over budget, never more materials than are listed.
const mineT = { [D.profs.indexOf('Tailoring')]: 75 };
const sp = E.spend(PT2, { basis: 'med', trim: false, disc: 0 }, mineT, 2000, false);
fo('plan within budget', String(sp.spent <= 2000 && sp.lines.length > 0), 'true');
const lb = sp.lines.find((l) => l.kind === 'craft' && l.e.r.name === 'Linen Bag');
fo('plan crafts Linen Bags', String(!!lb && lb.n >= 1 && lb.n * 3 <= 300 && lb.n <= Math.floor(90 * 0.25)), 'true');
// Coins formatting
const f = (c) => { const k = coins(c); return (k.neg ? '-' : '') + k.parts.map(([n, u]) => n + u).join(' '); };
fo('coins 12345', f(12345), '1g 23s 45c'); fo('coins -99', f(-99), '-99c'); fo('coins 10005', f(10005), '1g 5c');
process.exit(fails ? 1 : 0);
