# WoW Forever sims

Two simulators and a crafting profit tool for a group leveling together in World of Warcraft: Forever, from level 1 to 60.

**Live: https://chraltro.github.io/wowsim/**

| Tool | What it does | Page |
| --- | --- | --- |
| Forever Group Sim | Every class and spec. Kills per hour while questing, dungeon damage and healing, talents from leveling routes, upgrades ranked by effort. Class combat runs on MythicSim's Forever engine, compiled to WebAssembly and run in your browser. | [/forever/](https://chraltro.github.io/wowsim/forever/) |
| Shaman Sim | A Restoration Shaman in depth: a second-by-second healer AI for dungeons, questing with four fighting styles, upgrades by effort and a combat log parser. Its own engine, in JavaScript. | [/shaman/](https://chraltro.github.io/wowsim/shaman/) |
| Forever Craft Profits | Every recipe ranked by what it makes on your auction house after the 5% cut, with vendor materials at vendor price. Flips between vendor and auction house, including crafting to sell to a vendor. Prices load from AHledger. | [/crafts/](https://chraltro.github.io/wowsim/crafts/) |

All three run in the browser. Characters and settings are kept in the browser's local storage. Craft Profits fetches the latest price scan from AHledger when it opens.

## Forever Group Sim

- **Group.** One row per character: level, spec, kills per hour while questing, time per kill and dungeon damage or healing. Change everyone's level at once.
- **Character.** Class, race, level, spec and talent route. Talents follow the route one point a level from 10. Gear starts as typical gear for the level and can be changed slot by slot.
- **Questing.** Kill time is a normal mob's health over the engine's damage per second at your level. Then the damage you take (armor, dodge, parry, mob misses; your pet tanks for Hunter and Warlock from 10), eating and drinking with the food and water of your level, and 10 seconds of walking between pulls.
- **Dungeon.** A boss two levels above you for two minutes: damage per second, healing per second for healers, damage taken for tanks.
- **Upgrades.** Items you can get at your level, simmed against your current gear and ranked by how easy they are to get. PvP and raid-only items are left out.

The engine is [MythicSim's Forever engine](https://github.com/sage3648/mythicsim-forever-engine) (MIT), which is built on [wowsims Forever](https://github.com/wowsims/forever) (MIT). It was written for level 60. We carry nine patches that make it correct at lower levels, each one leaving level 60 results bit-identical. [`docs/multiclass.md`](docs/multiclass.md) lists every patch, the gaps that remain and the before and after numbers.

## Forever Craft Profits

- **Crafts.** Profit per craft for every recipe up to the skill you set, in any profession. Materials count at the cheaper of vendor and auction house, and materials you can make yourself, like cured hides or bolts, at the cheaper of buying and crafting. Sales count after the 5% cut, or at the vendor price when the vendor pays more.
- **Thin houses.** A sale price more than twice the median of the other houses in your region counts at twice that median, and items listed once or twice that no other house backs up are hidden. Both can be switched off.
- **Vendor flips.** Auction listings below what a vendor pays, crafts a vendor pays more for than their materials cost, and vendor goods that list above vendor price. A setting takes 10% or 20% off vendor prices for reputation.
- **Prices.** The page opens on a built-in scan, then loads the latest scan for your house from AHledger. Any ruleset, faction and region. Where AHledger cannot be reached, a price table can be pasted in.

## Shaman Sim

- **Questing.** Kills per hour for four ways to fight, with the best weapon imbue for each, Lightning Shield, eating and drinking.
- **Dungeon fight.** A Monte Carlo healer AI with a tank, three damage dealers and you. It finds the most tank damage per second you can heal through.
- **Upgrades.** The easiest real upgrades for your level, ranked by what they add to questing speed or healing over the effort to get them.
- **Combat log.** Parses a WoW combat log file in the browser and writes a summary you can paste to Claude for a critique.

## Layout

| Path | What it is |
| --- | --- |
| `src/mc/` | Group Sim: `app.html` and `app.js` (page), `request.js` (engine requests and character sheets), `quest.js` (questing model), `gear.js` (typical gear), `worker.js` (runs the engine off the main thread). `classdata.js` and `items.js` are generated. |
| `src/` | Shaman Sim: `app.html`, `app_main.js`, `engine.js`, `data.js`, `logparse.js`, `worker.js`. `levels.js`, `items.js` and `ranks.json` are generated. The Group Sim reuses `data.js`, `levels.js` and the page CSS. |
| `src/crafts/` | Craft Profits: `app.html` (page), `core.js` (pricing, no DOM), `app.js` (interface). |
| `data/crafts.json` | Craft Profits data: recipes, items, vendor prices and availability, reference prices and a built-in scan. Generated by `pipeline/crafts/`. |
| `src/site/index.html` | The landing page. |
| `engine-wasm/` | A small Rust crate that wraps the engine for the browser (`ws_alloc`, `ws_sim`, `ws_out_ptr`, `ws_out_len`), our engine patches, and the built `engine.wasm.gz`. |
| `vendor/mythicsim-forever-engine` | The engine, a git submodule pinned at `b3c5eb6`. |
| `data/` | Inputs to the generated files: items, class stats per level, talents, leveling routes, Shaman data. |
| `tools/` | Build and deploy scripts. |
| `test/` | Node checks and Playwright browser checks. |
| `opt/` | Shaman talent optimizer: local search over legal 51-point builds, plus Pareto frontiers. |
| `pipeline/` | The one-off crawlers that produced `data/`. They do not run as they are; see `pipeline/README.md`. |
| `docs/multiclass.md` | Group Sim design notes, engine patches and known gaps. |
| `dist/` | The built site: `index.html`, `shaman/index.html`, `forever/index.html`, `forever/engine.gz.wasm` and `crafts/index.html`. |

## Build

```sh
git clone --recurse-submodules https://github.com/chraltro/wowsim
cd wowsim
./tools/build_site.sh       # src/ -> dist/ (Python only)
cd dist && python3 -m http.server 8765    # open http://localhost:8765/
```

The Group Sim fetches its engine, so open it over HTTP, not from the file system. The Shaman Sim is one self-contained file.

The engine is committed already built, in `engine-wasm/engine.wasm.gz`. To rebuild it you need [rustup](https://rustup.rs); the toolchain and the wasm target are pinned in `engine-wasm/rust-toolchain.toml`:

```sh
./tools/build_engine.sh     # applies engine-wasm/patches/ to the submodule, builds, gzips
```

When the data changes:

```sh
python3 tools/build_mc_data.py    # data/classes, data/talents, data/routes + engine presets -> src/mc/classdata.js
python3 tools/build_items_all.py  # data/items_all.json -> src/mc/items.js
python3 tools/build_ranks.py      # data/shaman_ranks.json -> src/ranks.json
python3 tools/build_levels.py     # data/shaman_levels.json + src/ranks.json -> src/levels.js
python3 tools/build_items.py      # data/items_forever_all.json + presets -> src/items.js
./pipeline/crafts/fetch_inputs.sh # recipes, price scans, client tables and vendor lists -> data/crafts.json (about 30 minutes)
```

## Deploy

```sh
./tools/build_site.sh && ./tools/deploy_pages.sh
```

`deploy_pages.sh` force-pushes `dist/` as a single commit to the `gh-pages` branch, which GitHub Pages serves.

## Checks

```sh
node test/mc_levels.js all 10,20,40,60   # every spec through the engine: no refusals, damage rises with level
node test/mc_quest.js all 10,20,40,60    # questing kills per hour for every spec
node test/lv.js                          # Shaman engine at levels 8 to 60
node test/routes.js                      # every Shaman leveling route is legal
node test/crafts.js                      # Craft Profits pricing against hand-checked recipes
python3 test/mc_ui.py                    # Group Sim in a browser (needs Playwright and Chrome, and the local server above)
python3 test/ui.py                       # Shaman Sim in a browser
```

The engine checks use a local cargo build if there is one, otherwise the committed `engine.wasm.gz`.

## Data

Each Shaman Sim assumption in `src/data.js` is labelled, and the page shows the labels under "How the sim works": **Forever** (Forever client data or a Blizzard statement), **Sim rule** (taken from wowsims Forever), **Vanilla** (a Classic value nobody has confirmed for Forever) or **Estimate** (our own assumption).

Sources:

- Class combat for the Group Sim: MythicSim's Forever engine, pinned at `b3c5eb6`, with our patches.
- Spell records, the item database and level 60 rules: [wowsims/forever](https://github.com/wowsims/forever), commit `125e534`, client build 1.60.1.70862.
- Per-level player and mob stats: the Forever client tables PlayerExpectedStat and ExpectedStat via wago.tools, with gaps filled from cmangos and vmangos.
- Talents and leveling routes: the public talent calculators and leveling guides named on each route in the page.
- Drop chances: Wowhead Forever and Warcraft DB. Quest rewards: QuestieDB-Forever.
- Craft Profits: recipes and auction prices from [AHledger](https://ahledger.com/) (free API, credited on the page); item names, vendor prices, recipe items and skill-up levels from the Forever client tables via wago.tools; which vendors sell an item, and learn skill for trainer recipes, from [MetaBot](https://metabot.gg/en/wow-forever) (Classic vendor lists). See `pipeline/crafts/README.md`.

## Licence

This repo includes code from MythicSim's Forever engine and wowsims Forever, both under the MIT licence; see [`NOTICE.md`](NOTICE.md). Not affiliated with Blizzard Entertainment. World of Warcraft is a trademark of Blizzard Entertainment.
