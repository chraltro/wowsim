# Shaman Sim for WoW Forever

A single-page simulator for a Dwarf Restoration Shaman in WoW Forever, from level 1 to 60. It has four parts:

- **Questing.** Kills per hour while leveling, for four ways to fight. It picks your best weapon imbue for each and includes Lightning Shield, eating and drinking.
- **Dungeon fight.** A Monte Carlo healer AI with a tank, three damage dealers and you. It finds the most tank damage per second you can heal through.
- **Upgrades.** Finds the easiest real upgrades for your level. Each item is ranked by what it adds to questing speed or healing, divided by the effort to get it.
- **Combat log.** Parses a WoW combat log file in the browser and writes a summary you can paste to Claude for a critique.

Every spell uses the rank you have at your level, with its level scaling. Talents come from each build's leveling route, one point per level from 10.

Live version: https://claude.ai/artifact/HmiNY3CyCiiMqAeMS6kPRU

## Layout

| Path | What it is |
| --- | --- |
| `src/app.html` | Page template: markup and CSS. Has placeholders for the scripts below. |
| `src/app_main.js` | The page's UI: level, builds and routes, gear picker, questing, dungeon runs, upgrades, log view. |
| `src/engine.js` | Simulation engine: character sheet, heal spells, 5-minute healing capacity, dungeon fight, melee and Lightning Bolt damage, questing model. Runs in both node and the browser. |
| `src/data.js` | Level 60 constants, leveling tables and the list of assumptions with their status. |
| `src/levels.js` | Generated. Base stats, crit scaling, mob health, damage and armor per level, plus every spell rank. |
| `src/items.js` | Generated. 6,214 Shaman-usable items with sources, drop chances, set bonuses and gear presets. |
| `src/ranks.json` | Generated. Compact spell ranks, read by `tools/build_levels.py`. |
| `src/logparse.js` | Combat log parser. |
| `src/worker.js` | Web Worker entry point, used for dungeon runs and log parsing. |
| `tools/` | Build scripts (see below). |
| `data/` | Inputs to the generated files. |
| `opt/` | Talent optimizer: local search over legal 51-point builds, plus Pareto frontiers. |
| `test/` | Node checks and Playwright browser checks. |
| `pipeline/` | One-off crawlers that produced `data/`. See `pipeline/README.md`. |
| `dist/index.html` | The built page. One self-contained file. |

## Build

```sh
python3 tools/build_ranks.py    # data/shaman_ranks.json  -> src/ranks.json
python3 tools/build_levels.py   # data/shaman_levels.json + src/ranks.json -> src/levels.js
python3 tools/build_items.py    # data/items_forever_all.json + presets -> src/items.js
python3 tools/build.py          # src/* -> dist/index.html
```

You only need the first three when the data changes. `tools/build.py` inlines everything into one HTML file, including a copy of the engine for the Web Worker.

## Checks

```sh
node test/lv.js        # engine at levels 8 to 60: spells, dungeon limits, questing per style
node test/routes.js    # every leveling route is legal and ends on its 51-point code
node test/imbue.js     # imbue comparison at 60 with the gear presets
node test/gen.js       # regenerate the synthetic combat log in test/sample.txt
python3 test/ui.py     # browser run at several levels (needs playwright and Chrome)
```

## Optimizer

```sh
cd opt
node optimize.js resto_timesaver          # best builds for healing, and for healing plus melee
node frontier.js                          # healing vs melee damage Pareto frontier
node frontier2.js                         # healing vs Lightning Bolt frontier
node validate.js resto_timesaver '{"pure":"-055-5530003315513151"}'   # Monte Carlo check
```

Build codes use the timesaver.gg format `ele-enh-res`, with one digit per talent in row and column order.

## Data and status labels

Each assumption in `src/data.js` has one of four labels, and the page shows them under "How the sim works":

- **Forever**: Forever client data or a Blizzard statement.
- **Sim rule**: a rule taken from the wowsims Forever simulator.
- **Vanilla**: a Classic value that nobody has confirmed for Forever.
- **Estimate**: this tool's own assumption.

Where the data comes from:

- Spell records, the item database and level 60 rules: [wowsims/forever](https://github.com/wowsims/forever), MIT licence, commit 125e534, client build 1.60.1.70862.
- Per-level player and mob stats: the Forever client tables PlayerExpectedStat and ExpectedStat, via wago.tools. Gaps are filled from cmangos and vmangos. `data/shaman_levels.json` records the source of every value.
- Drop chances: Wowhead Forever and Warcraft DB (wowtbc.gg).
- Quest rewards: QuestieDB-Forever.
- Tooltip checks for spells, potions, drinks and food: Wowhead Forever.

## Not modelled

- Healing threat and cast pushback.
- Item procs and on-use trinkets.
- Searing Totem.
- Pulling more than one mob while questing.
- Health regeneration outside eating.
- Armor debuffs (Sunder Armor, Faerie Fire). Melee is always against a normal mob's full armor.
