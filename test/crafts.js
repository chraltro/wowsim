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
// A plan uses what is already in the bags first: 2 Linen Bags need 6 bolts, 4 are owned, so 2 are made from 4 Linen Cloth.
const opts = { basis: 'med', trim: false, disc: 0 };
const linen = (price, qty, more) => parsePriceTable(['AHL1|forever/pvp/alliance/eu|1794052222|1', '2589:' + price + ':' + price + ':' + qty + ':' + price + ':' + price + ':' + price + ':' + price + ':90000'].concat(more || []).join('\n'));
const own = new Map([[2996, 4]]);
const po = E.context(linen(10, 5000), Object.assign({ sellTo: 'vendor', maxSkill: 300 }, opts)).plan(find('Linen Bag'), 2, own);
eq('owned bolts used', po.used.get(2996), 4); eq('cloth still to buy', po.buy.find((b) => b.id === 2589).q, 4); eq('bags emptied', own.get(2996), 0);
// Leveling. Only Linen Cloth is listed, at 10c. A Linen Bag is 3 bolts (2 cloth each) and 3 Coarse Thread: 90c, and a
// vendor pays 2s. It stays orange to 30, so Tailoring 1 to 11 is 10 bags: 9s in, 20s back.
const T = D.profs.indexOf('Tailoring');
let lp = E.levelPath(linen(10, 5000), opts, T, 1, 11, {}, false);
fo('level: one step of Linen Bags', lp.steps.map((s) => s.n + ' ' + s.r.name + ' ' + s.from + '-' + s.to).join('|'), '10 Linen Bag 1-11');
eq('level: materials', lp.mats, 900); eq('level: back', lp.back, 2000); eq('level: net', lp.net, -1100);
fo('level: bolts crafted first', lp.steps[0].pre.map((x) => x.n + ' ' + x.r.name).join(), '30 Bolt of Linen Cloth');
// With only 30 cloth listed the plan still stands, and says the 60 it needs are not there. With 1 listed nothing can be made.
lp = E.levelPath(linen(10, 30), opts, T, 1, 11, {}, false);
fo('level: short material flagged', lp.short.map((x) => x.id + ' ' + x.need + ' of ' + x.listed).join(), '2589 60 of 30');
lp = E.levelPath(linen(10, 1), opts, T, 1, 11, {}, false);
fo('level: nothing listed is a gap', JSON.stringify(lp.gaps) + ' ' + lp.steps.length + ' ' + lp.missed, '[[1,11]] 0 10');
// Keeping what later steps need. Cloth at 1s, bolts list at 3s with 80 up and 160 sold a day, so the auction house
// counts for 20 bolts. Past those a bolt and a White Linen Shirt cost the same per point, and the bolts run on to 24.
// The 12 shirts and 4 Simple Linen Pants after them use 16 of the 23 bolts, so 7 are sold and the later steps only buy
// bleach and thread.
const boltRow = '2996:300:300:80:300:300:300:300:1600';
lp = E.levelPath(linen(100, 5000, [boltRow]), opts, T, 1, 40, {}, false);
fo('level: steps', lp.steps.map((s) => s.n + ' ' + s.r.name).join('|'), '23 Bolt of Linen Cloth|12 White Linen Shirt|4 Simple Linen Pants');
eq('level: bolts kept', lp.steps[0].keep, 16); eq('level: bolts sold', lp.steps[0].ah, 7);
eq('level: seven bolts on the AH', lp.steps[0].back, 7 * expectedSale(285, 40, 2));
eq('level: shirts buy bleach and thread only', lp.steps[1].mats, 12 * 35); eq('level: pants buy thread only', lp.steps[2].mats, 40);
eq('level: trainer fee once', lp.fees, 25); eq('level: total', lp.net, 4600 + 420 + 40 + 25 - 7 * expectedSale(285, 40, 2) - 12 * 75 - 4 * 23);
// A recipe that has to be bought only joins when asked. Pattern: Red Linen Vest is listed at 5c, the vest at 20s.
const vest = ['6271:5:5:3:5:5:5:5:10', '6239:2000:1900:400:2000:2000:1900:2100:8000'];
fo('level: no bought recipes by default', String(E.levelPath(linen(100, 5000, vest), opts, T, 30, 50, {}, false).steps.some((s) => s.r.src === 2)), 'false');
const rv = E.levelPath(linen(100, 5000, vest), opts, T, 30, 50, {}, true).steps.find((s) => s.r.name === 'Red Linen Vest');
fo('level: bought recipe joins', rv ? rv.from + '-' + rv.to + ' ' + rv.n + ' ' + rv.feeKind + ' ' + rv.fee + ' ' + rv.ah : 'missing', '35-50 15 ah 5 15');
// Recipes worth buying. The vest: 3 bolts (2s each to make), thread 10c, Red Dye 50c = 6s 60c. 400 listed, 800 sold a day.
// A batch is a quarter of the 400 listed. Each sale is expected at just under 19s, so the pattern pays back in one craft.
const rb = E.recipeBuys(linen(100, 5000, vest), opts).find((x) => x.r.name === 'Red Linen Vest');
fo('recipe: cheapest way', rb.way.src + ' ' + rb.price, 'ah 5'); eq('recipe: batch', rb.n, 100); eq('recipe: payback', rb.payback, 1);
eq('recipe: expected a craft', rb.e.exp, expectedSale(1900, 160, 2) - 660); eq('recipe: after the batch', rb.net, (expectedSale(1900, 160, 2) - 660) * 100 - 5);
// Favor: 25 favor takes 3 green Apprentice crates (10 each) at 50s plus 16s of bolts. Only 12 crates are listed, so 500 has no price.
const fc = E.context(PT3, { basis: 'med', sellTo: 'best', maxSkill: 300, trim: false, disc: 0 });
eq('favor: 25 costs three crates', fc.favor(25).cost, 3 * 6600); fo('favor: more than is listed', String(fc.favor(500)), 'null');
// Post or vendor, for a Linen Bag a vendor pays 2s for. Posted just under the cheapest listing (2s 90c, so 2s 87c) with 300 sold
// a day against 90 listed, it sells every time and each unit brings its net 2s 87c less 5%, well over the vendor's 2s.
const sc = (pt, id, o) => E.context(pt, Object.assign({ basis: 'med', sellTo: 'best', maxSkill: 300, trim: false, disc: 0 }, o)).sellCheck(id);
let ck = sc(PT2, 4238);
fo('check: a fast bag is posted', ck.verdict + ' ' + ck.listAt + ' ' + ck.band + ' ' + ck.ownTurn + ' ' + ck.thin, 'post 287 fast true false');
eq('check: expected', ck.exp, expectedSale(287 * 0.95, 200, 300 / 90)); eq('check: gain over the vendor', ck.gain, ck.exp - 200);
// Listed at 1s 20c, under the 2s a vendor pays: vendor it.
const cheap = parsePriceTable(['AHL1|forever/pvp/alliance/eu|1794052222|1', '4238:150:120:10:150:150:120:150:'].join('\n'));
fo('check: under the vendor price goes to the vendor', sc(cheap, 4238).verdict, 'vendor');
// Nobody lists it here: priced at the region's other houses, with no undercut.
const none = parsePriceTable(['AHL1|forever/pvp/alliance/eu|1794052222|1', '2996:80:76:300:80:80:76:90:'].join('\n'));
if (D.ref.eu[4238] != null) { ck = sc(none, 4238); fo('check: unlisted uses the region price', ck.unlisted + ' ' + ck.listAt, 'true ' + D.ref.eu[4238]); eq('check: unlisted expected', ck.exp, expectedSale(D.ref.eu[4238] * 0.95, 200, D.turn.eu[4238] ?? 1 / 14)); }
// A listing far above the region is counted at twice the region's price when trimming is on.
const high = parsePriceTable(['AHL1|forever/pvp/alliance/eu|1794052222|1', '4238:900:900:5:900:900:900:900:'].join('\n'));
if (D.ref.eu[4238] != null) { ck = sc(high, 4238, { trim: true }); fo('check: trimmed', ck.trimmed + ' ' + ck.listAt, 'true ' + D.ref.eu[4238] * 2); }
// A region without reference prices: one lone listing is flagged as thin, and with no sales data the bag barely sells.
const cn = parsePriceTable(['AHL1|forever/pvp/alliance/cn|1794052222|1', '4238:9000:9000:1:9000:9000:9000:9000:'].join('\n'));
ck = sc(cn, 4238); fo('check: one listing nobody backs up', ck.thin + ' ' + ck.band + ' ' + ck.verdict, 'true null post');
// Soulbound items cannot be posted.
fo('check: fixture is soulbound', String(!!E.items.get(3734)[6]), 'true');
ck = sc(PT2, 3734); fo('check: soulbound goes to the vendor', ck.verdict + ' ' + ck.listAt, 'vendor null');
// Coins formatting
const f = (c) => { const k = coins(c); return (k.neg ? '-' : '') + k.parts.map(([n, u]) => n + u).join(' '); };
fo('coins 12345', f(12345), '1g 23s 45c'); fo('coins -99', f(-99), '-99c'); fo('coins 10005', f(10005), '1g 5c');
process.exit(fails ? 1 : 0);
