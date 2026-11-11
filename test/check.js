// The check command against test/sample_export.txt (written by test/addon_run.py from the real addon code) and a fixed
// price table, so the numbers do not move with new scans. Quest checks run only when local/cache/quests.json exists.
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..');
const Parse = require('../src/check/parse.js');
const Advise = require('../src/check/advise.js');
const { DATA } = require('../src/data.js');
const { LEVELS, RANKS } = require('../src/levels.js'); DATA.LV = LEVELS; DATA.RK = RANKS;
const { ITEMS, SETS } = require('../src/items.js');
const core = require('../src/crafts/core.js');
const D = require('../data/crafts.json');
let fails = 0;
const ok = (name, cond, got) => { if (!cond) fails++; console.log((cond ? 'ok   ' : 'FAIL ') + name + (cond && got === undefined ? '' : ': ' + got)); };

const ch = Parse.parseExport(fs.readFileSync(path.join(ROOT, 'test/sample_export.txt'), 'utf8'));
ok('character line', ch.name === 'Thrainor' && ch.level === 14 && ch.cls === 'shaman' && ch.race === 'Dwarf', [ch.name, ch.level, ch.race, ch.cls].join(' '));
ok('gold', ch.gold === 31250, ch.gold);
ok('zone', ch.zone === 'Loch Modan' && ch.subzone === 'Thelsamar', ch.zone + ' / ' + ch.subzone);
ok('worn gear', Object.keys(ch.gear).length === 5 && ch.gear.mainhand.id === 3103, Object.keys(ch.gear).join(','));
ok('tooltip stats', JSON.stringify(Parse.tooltipStats(ch.gear.mainhand.lines)) === '{"s":{"str":1,"spi":1},"w":{"min":18,"max":27,"speed":2.7},"two":true,"wt":"Mace","at":null}', JSON.stringify(Parse.tooltipStats(ch.gear.mainhand.lines)));
ok('bags and bank', ch.bags.length === 8 && ch.bank.length === 2 && ch.bags.find((b) => b.id === 2318).count === 14, ch.bags.length + '/' + ch.bank.length);
ok('quest log', ch.quests.length === 3 && ch.quests[0].choices.length === 3 && ch.quests[1].complete, ch.quests.map((q) => q.id).join(','));
ok('completed quests', ch.completed.size === 40 && ch.completed.has(96243), ch.completed.size);
ok('talents', ch.talents['Tidal Focus'].rank === 5 && ch.talentPoints.Restoration === 5);
ok('skills', ch.skills.Leatherworking.rank === 62 && ch.skills.Skinning.max === 75);
ok('known recipes', ch.recipes.Leatherworking.names.size === 10 && ch.recipes.Leatherworking.names.get('Embossed Leather Cloak') === 'orange');
ok('auction scan', ch.ah.prices.size === 21 && ch.ah.prices.get(1959).min === 1300 && ch.ah.prices.get(2318).qty === 40 && !ch.ah.gearOnly, ch.ah.prices.size);

let quests = null;
try { quests = JSON.parse(fs.readFileSync(path.join(ROOT, 'local/cache/quests.json'), 'utf8')); } catch (e) { console.log('skip quest checks: no local/cache/quests.json (python tools/fetch_quests.py)'); }
const advisor = Advise.makeAdvisor({ Engine: require('../src/engine.js'), DATA, ITEMS, SETS, TALENT_META: require('../opt/talents_meta.json'), Parse,
  MCGear: require('../src/mc/gear.js'), crafts: { core, D }, quests, prices: core.parsePriceTable(D.snap) });
const R = advisor.report(ch, {});
const U = R.upgrades;
ok('the bag upgrade is found first', U.own.length === 2 && U.own[0].name === 'Cold Iron Pick' && U.own[0].questGain > 3, U.own.map((u) => u.name).join(', '));
ok('gloves in the bags too', U.own[1].name === 'Fine Leather Gloves' && U.own[1].healGain > 1);
ok('auction buys are compared with the gear after that', !U.ah.some((u) => u.name === 'Cold Iron Pick' || u.name === 'Fine Leather Gloves') && U.ah.every((u) => u.value >= 0.5));
ok('best auction buy', U.ah[0].name === 'Green Woolen Vest' && U.ah[0].price === 700 && U.ah[0].afford, U.ah[0] && U.ah[0].name);
ok('the staff replaces the pick, not the hammer', U.ah.find((u) => u.name === 'Riverside Staff').replaces === 'Cold Iron Pick');
ok('the full scan decides what is listed', !U.ah.some((u) => u.from !== 'scan'));
ok('Mail is not offered at 14', !JSON.stringify(U).includes('Ironheart Chain') || U.rewards[0].cantWear.includes('Ironheart Chain'), U.rewards[0].cantWear.join(','));
ok('crafts use what is in the bags', U.craft.some((u) => /Light Leather/.test(u.held)));
const lw = R.professions.find((p) => p.name === 'Leatherworking');
ok('Leatherworking: recipes to learn', lw.learnNow.some((r) => r.name === 'Embossed Leather Boots') && !lw.learnNow.some((r) => r.name === 'Embossed Leather Cloak'), lw.learnNow.map((r) => r.name).join(', '));
ok('Leatherworking: a path to the cap', lw.path && lw.path.from === 62 && lw.path.to === 75 && lw.path.steps.length > 0, lw.path && lw.path.steps.map((s) => s.crafts + ' x ' + s.name).join(', '));
ok('Skinning: near its cap', R.professions.find((p) => p.name === 'Skinning').cap === 75);
ok('bags: keep the leather', R.bags.find((b) => b.name === 'Light Leather').verdict === 'keep');
if (quests) {
  const Q = R.quests;
  const names = Q.open.map((q) => q.name);
  ok('open quests found', Q.total > 20, Q.total);
  ok('here comes first', Q.byZone[0].here && Q.byZone[0].zone === 'Loch Modan', Q.byZone[0].zone);
  ok('done and active quests are left out', !names.includes('Rat Catching') && !names.includes('Filthy Paws') && !names.includes('Thelsamar Blood Sausages'));
  ok('a chain step waits for the quest in the log', Q.soon.some((q) => q.name === "In Defense of the King's Lands"));
  ok('quests above your level wait', !names.includes('A Dark Threat Looms') && !names.includes("WANTED: Chok'sul"));
  ok('the level 13-18 dungeon is listed', Q.byZone.some((g) => g.dungeon && /Hall of Thanes/.test(g.zone)));
  ok('reward quests', U.quest.length > 0 && U.quest.every((u) => names.includes(u.quest)));
}
const text = Advise.render(R);
ok('the report renders', /## Gear/.test(text) && /## Professions/.test(text) && !/undefined|NaN/.test(text), text.length + ' characters');
// An export from an older addon: no finished-quest list, no scan. It still works and says what is missing.
const old = fs.readFileSync(path.join(ROOT, 'test/sample_export.txt'), 'utf8').replace(/## Completed quests[\s\S]*?(?=## Talents)/, '').replace(/## Auction house scan[\s\S]*$/, '').replace(/## Known recipes[\s\S]*?(?=## Reputation)/, '');
const R2 = advisor.report(Parse.parseExport(old), {});
ok('older exports still work', R2.upgrades.own.length === 2 && R2.upgrades.ah.every((u) => u.from === 'ahledger'));
ok('and say what is missing', !quests || R2.notes.some((n) => /finished quests/.test(n)));
console.log(fails ? fails + ' FAILED' : 'all passed');
process.exit(fails ? 1 : 0);
